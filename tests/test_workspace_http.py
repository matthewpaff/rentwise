import http.client
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
import server
from engine import BookingStore
from workspace import Workspace

class WorkspaceHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.path=Path(cls.tmp.name)/'db.sqlite3'
        cls.old_store,cls.old_workspace=server.store,server.workspace
        server.store=BookingStore(cls.path);server.workspace=Workspace(cls.path)
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.thread.join()
        server.store,server.workspace=cls.old_store,cls.old_workspace;cls.tmp.cleanup()
    def call(self,path,body=None,headers=None,raw=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=3)
        conn.request('POST' if body is not None or raw is not None else 'GET',path,body=raw if raw is not None else json.dumps(body) if body is not None else None,headers={'Content-Type':'application/json',**(headers or {})})
        response=conn.getresponse();result=response.status,json.loads(response.read());conn.close();return result

    def test_host_rebinding_is_rejected_on_read_and_write(self):
        for path,body in [('/api/health',None),('/api/evaluate',{})]:
            self.assertEqual(self.call(path,body,{'Host':f'evil.example:{self.http.server_port}'})[0],403)
        self.assertEqual(self.call('/api/health',headers={'Host':f'localhost:{self.http.server_port}'})[0],200)

    def test_ambiguous_and_unauthorized_fields_fail(self):
        for raw in [b'{"months":12,"months":1}',b'{"budget":NaN}']:
            self.assertEqual(self.call('/api/evaluate',raw=raw)[0],400)
        self.assertEqual(self.call('/api/evaluate',{'consent':True})[0],400)
        for invalid in [False,0,'',[]]:
            self.assertEqual(self.call('/api/export',{'preferences':invalid})[0],400)

    def test_collection_import_revision_and_original_retrieval(self):
        status,created=self.call('/api/collections/create',{'name':'HTTP import','listings':server.LISTINGS,'provenance':'Synthetic API test'})
        self.assertEqual(status,200)
        payload={'id':created['id'],'listings':server.LISTINGS,'provenance':'Revision test','expected_version':1}
        self.assertEqual(self.call('/api/collections/revise',payload)[1]['version'],2)
        self.assertEqual(self.call('/api/collections/revise',payload)[0],400)
        self.assertEqual(self.call('/api/collections/load',{'id':created['id'],'version':1})[1]['provenance'],'Synthetic API test')

    def test_export_rejects_unknown_selection(self):
        self.assertEqual(self.call('/api/export',{'ids':['missing']})[0],400)
        status,export=self.call('/api/export',{'ids':['mesa-one'],'format':'csv'})
        self.assertEqual(status,200)
        self.assertIn('source_excerpt',export['content'])

    def test_booking_cancel_preserves_status_and_audit(self):
        body={'key':'v2-http-booking','listing':'cedar-studio','consent':True}
        self.assertEqual(self.call('/api/book',body)[0],200)
        self.assertEqual(self.call('/api/bookings/cancel',{'key':body['key'],'consent':True})[1]['status'],'cancelled')
        self.assertEqual(self.call('/api/reconcile',{'key':body['key']})[1]['status'],'cancelled')
        self.assertEqual(len(self.call('/api/bookings/events',{'key':body['key']})[1]['events']),2)
