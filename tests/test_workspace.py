from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest
from workspace import Workspace

class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'workspace.sqlite3'
        self.store=Workspace(self.path)
        self.listings=json.loads((Path(__file__).resolve().parents[1]/'data.json').read_text())

    def tearDown(self):self.tmp.cleanup()

    def test_versions_preserve_original_and_archive_is_reversible(self):
        original=self.store.create_collection('My corpus',self.listings,'User authored samples')
        updated=json.loads(json.dumps(self.listings))
        updated[0]['name']='Revised name'
        latest=self.store.revise_collection(original['id'],updated,'Corrected title',1)
        self.assertEqual(latest['version'],2)
        self.assertEqual(self.store.collection(original['id'],1)['listings'][0]['name'],self.listings[0]['name'])
        self.assertEqual(len(self.store.versions(original['id'])),2)
        self.store.archive_collection(original['id'])
        self.assertEqual(self.store.collections(),[])
        self.assertEqual(len(self.store.collections(True)),1)
        with self.assertRaises(ValueError):self.store.revise_collection(original['id'],updated,'test',2)
        self.store.archive_collection(original['id'],False)
        self.assertEqual(len(Workspace(self.path).collections()),1)

    def test_concurrent_edits_cannot_overwrite_revision(self):
        key=self.store.create_collection('Shared local corpus',self.listings,'Sample')['id']
        def save(_):
            try:return self.store.revise_collection(key,self.listings,'Concurrent edit',1)['version']
            except ValueError:return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(save,range(2))),[2,'conflict'])

    def test_saved_search_survives_reopen_and_rejects_authority(self):
        saved=self.store.save_search('Affordable',{'budget':'1500','kind':'room'})
        self.assertEqual(Workspace(self.path).searches()[0]['preferences']['budget'],'1500.00')
        with self.assertRaises(ValueError):self.store.save_search('Bad',{'consent':True})
        self.store.delete_search(saved['id'])
        self.assertEqual(self.store.searches(),[])

    def test_invalid_import_is_atomic(self):
        with self.assertRaises(ValueError):self.store.create_collection('Bad',self.listings*2,'Duplicate IDs')
        self.assertEqual(self.store.collections(),[])

    def test_diff_reports_added_removed_and_changed_without_mutating_versions(self):
        key=self.store.create_collection('Diff research',self.listings,'Sample')['id']
        revised=json.loads(json.dumps(self.listings[1:]))
        revised[0]['base']='1100'
        addition=dict(self.listings[0],id='new-sample')
        self.store.revise_collection(key,revised+[addition],'Price correction',1)
        diff=self.store.diff(key,1,2)
        self.assertEqual(diff['added'],['new-sample'])
        self.assertEqual(diff['removed'],['cedar-studio'])
        self.assertEqual(diff['changed'][0]['fields']['base']['before'],'1090.00')
        self.assertEqual(diff['changed'][0]['fields']['base']['after'],'1100.00')
