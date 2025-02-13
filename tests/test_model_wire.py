from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import unittest
from model_adapter import OllamaAdapter

class FakeOllama(BaseHTTPRequestHandler):
    mode='valid'
    payload=None
    def log_message(self,*args):pass
    def do_POST(self):
        type(self).payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.mode=='redirect':
            self.send_response(302);self.send_header('Location','http://example.invalid/');self.end_headers();return
        raw={'valid':json.dumps({'message':{'content':'{"budget":"1800","kind":"whole"}'}}).encode(),'oversize':b'x'*65537,'invalid':b'not json'}[self.mode]
        self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)

class ModelWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),FakeOllama)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def adapter(self):return OllamaAdapter('fake-model',endpoint=f'http://127.0.0.1:{self.server.server_port}/api/chat')

    def test_actual_wire_envelope_is_structured_and_nonstreaming(self):
        FakeOllama.mode='valid'
        result=self.adapter().propose_preferences('Entire place under 1800')
        self.assertEqual(result,{'budget':'1800.00','kind':'whole'})
        self.assertEqual(FakeOllama.payload['format'],'json')
        self.assertIs(FakeOllama.payload['stream'],False)
        self.assertEqual(FakeOllama.payload['model'],'fake-model')
        self.assertEqual(FakeOllama.payload['messages'][1]['role'],'user')

    def test_redirect_oversize_and_nonjson_fail_without_remote_requests(self):
        for mode in ['redirect','oversize','invalid']:
            FakeOllama.mode=mode
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.adapter().propose_preferences('test')

    def test_remote_and_credentialed_endpoints_are_rejected(self):
        for endpoint in ['https://example.com/api/chat','http://localhost:11434/api/chat','http://user@127.0.0.1:11434/api/chat','http://127.0.0.1:11434/api/chat?target=remote']:
            with self.subTest(endpoint=endpoint),self.assertRaises(ValueError):OllamaAdapter('fake-model',endpoint=endpoint)
