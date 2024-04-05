"""Run with python server.py; binds only to loopback."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import argparse
import json
from engine import BookingStore, costs, validate_listing, money
from model_adapter import OllamaAdapter, validate_preferences
from workspace import Workspace
from decision import evaluate
from exports import comparison_export

ROOT = Path(__file__).resolve().parent
LISTINGS = [validate_listing(x) for x in json.loads((ROOT / 'data.json').read_text(encoding='utf-8'))]
store = None
model = None
workspace = None

def local_workspace():
    if workspace is not None:return workspace
    if store is None:raise ValueError('Workspace storage is unavailable')
    return Workspace(store.path)

class Handler(BaseHTTPRequestHandler):
    def respond(self, status, value, kind='application/json'):
        raw = json.dumps(value).encode() if kind == 'application/json' else value
        self.send_response(status)
        self.send_header('Content-Type', kind + '; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/health':
            return self.respond(200, {'status':'ok','sandbox':True,'model_enabled':model is not None})
        if path == '/api/listings':
            return self.respond(200, {'listings': LISTINGS, 'sample': True})
        if path == '/api/collections':
            return self.respond(200, {'collections':local_workspace().collections(True)})
        if path == '/api/searches':
            return self.respond(200, {'searches':local_workspace().searches()})
        if path == '/api/bookings':
            return self.respond(200, {'bookings':store.history()})
        assets = {'/': ('index.html','text/html'), '/app.js': ('app.js','text/javascript'), '/style.css': ('style.css','text/css')}
        if path in assets:
            name, kind = assets[path]
            return self.respond(200, (ROOT / name).read_bytes(), kind)
        self.respond(404, {'error': 'Route not found'})

    def do_POST(self):
        # Same-origin checks prevent browser cross-site actions against localhost.
        if self.headers.get('Origin') not in (None, 'http://' + self.headers.get('Host', '')):
            return self.respond(403, {'error': 'Same-origin requests only'})
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.respond(415, {'error': 'Use application/json'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 100000:
                raise ValueError('JSON body must be 1–100000 bytes')
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('Request body must be an object')
            path = urlsplit(self.path).path
            if path == '/api/searches/save':
                return self.respond(200,local_workspace().save_search(body.get('name'),body.get('preferences')))
            if path == '/api/searches/delete':
                return self.respond(200,local_workspace().delete_search(body.get('id')))
            if path == '/api/bookings/status':
                return self.respond(200,store.status(body.get('key')))
            if path == '/api/bookings/events':
                return self.respond(200,{'events':store.events(body.get('key'))})
            if path == '/api/bookings/cancel':
                return self.respond(200,store.cancel(body.get('key'),body.get('consent')))
            if path == '/api/collections/create':
                return self.respond(200,local_workspace().create_collection(body.get('name'),body.get('listings'),body.get('provenance')))
            if path == '/api/collections/load':
                return self.respond(200,local_workspace().collection(body.get('id'),body.get('version')))
            if path == '/api/collections/revise':
                return self.respond(200,local_workspace().revise_collection(body.get('id'),body.get('listings'),body.get('provenance'),body.get('expected_version')))
            if path == '/api/collections/versions':
                return self.respond(200,{'versions':local_workspace().versions(body.get('id'))})
            if path == '/api/collections/archive':
                return self.respond(200,local_workspace().archive_collection(body.get('id'),body.get('archived',True)))
            if path == '/api/preferences':
                if model is None:
                    return self.respond(503, {'error':'Local model disabled. Start with --ollama-model MODEL and run Ollama locally to opt in.'})
                try:
                    return self.respond(200, model.propose_preferences(body.get('text')))
                except OSError:
                    return self.respond(502, {'error':'Local model unavailable or timed out. Deterministic filtering remains available.'})
            if path == '/api/evaluate':
                preferences={k:body[k] for k in ('budget','kind','months','optional','known_only') if k in body}
                return self.respond(200,evaluate(body.get('listings',LISTINGS),preferences))
            if path == '/api/book':
                if body.get('listing') not in {x['id'] for x in LISTINGS}:
                    raise ValueError('Only bundled sample listings support sandbox booking')
                return self.respond(200, store.book(body.get('key'), body['listing'], body.get('consent')))
            if path == '/api/reconcile':
                return self.respond(200, store.reconcile(body.get('key')))
            return self.respond(404, {'error': 'Route not found'})
        except (ValueError, TypeError, KeyError, UnicodeDecodeError) as exc:
            self.respond(400, {'error': str(exc)})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8761)
    parser.add_argument('--db', default=str(ROOT / 'sandbox.sqlite3'))
    parser.add_argument('--ollama-model', help='Optional locally installed Ollama model; disabled by default')
    args = parser.parse_args()
    store = BookingStore(args.db)
    workspace = Workspace(args.db)
    model = OllamaAdapter(args.ollama_model) if args.ollama_model else None
    print(f'Rentwise sample dashboard: http://127.0.0.1:{args.port} (Ctrl+C to stop)', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
