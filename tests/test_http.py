"""HTTP contract checks on an ephemeral loopback server, no external traffic."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
import server
from engine import BookingStore

class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        server.store=BookingStore(Path(cls.tmp.name)/'sandbox.sqlite3')
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join()
        cls.tmp.cleanup()

    def request(self,path,body=None,origin=None,raw=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=3)
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        conn.request('POST' if body is not None or raw is not None else 'GET',path,body=raw if raw is not None else json.dumps(body) if body is not None else None,headers=headers)
        response=conn.getresponse()
        result=(response.status,response.read())
        conn.close()
        return result

    def test_health_and_static_allowlist(self):
        self.assertEqual(self.request('/api/health')[0],200)
        self.assertEqual(self.request('/')[0],200)
        self.assertEqual(self.request('/../engine.py')[0],404)

    def test_bad_json_and_shapes(self):
        for raw in [b'[]',b'42',b'null',b'{broken',b'\xff']:
            self.assertEqual(self.request('/api/evaluate',raw=raw)[0],400)
        for body in [{'known_only':'yes'},{'listings':[]},{'months':False}]:
            self.assertEqual(self.request('/api/evaluate',body)[0],400)

    def test_foreign_origin_and_booking_validation(self):
        self.assertEqual(self.request('/api/book',{},origin='https://foreign.example')[0],403)
        self.assertEqual(self.request('/api/book',{'listing':'not-real','consent':True,'key':'request-01'})[0],400)
        self.assertEqual(self.request('/api/book',{'listing':'cedar-studio','consent':'true','key':'request-01'})[0],400)
        self.assertEqual(self.request('/api/reconcile',{'key':[]})[0],400)

    def test_evaluate_and_sandbox_round_trip(self):
        code,raw=self.request('/api/evaluate',{'kind':'whole','known_only':True})
        self.assertEqual(code,200)
        data=json.loads(raw)
        self.assertEqual([x['id'] for x in data['results']],['mesa-one'])
        payload={'listing':'sage-room','consent':True,'key':'http-request-01'}
        first=self.request('/api/book',payload)
        self.assertEqual(first[0],200)
        self.assertEqual(first,self.request('/api/book',payload))
        self.assertEqual(json.loads(first[1])['status'],'pending')

    def test_model_disabled_by_default(self):
        self.assertEqual(self.request('/api/preferences',{'text':'cheap home'})[0],503)
