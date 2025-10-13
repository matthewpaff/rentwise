import json
from pathlib import Path
import tempfile
import unittest
from workspace import Workspace

class SnapshotTests(unittest.TestCase):
    def test_snapshot_retains_calculation_and_source_after_input_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace=Workspace(Path(tmp)/'db.sqlite3')
            listings=json.loads((Path(__file__).resolve().parents[1]/'data.json').read_text())
            saved=workspace.save_snapshot('Before correction',listings,{'months':6,'kind':'room'})
            listings[1]['base']='9999'
            reloaded=Workspace(workspace.path).snapshot(saved['id'])
            self.assertEqual(saved,reloaded)
            self.assertEqual(len(reloaded['payload']['results']),2)
            self.assertEqual(reloaded['payload']['preferences']['months'],6)
            self.assertTrue(reloaded['payload']['sandbox'])
            self.assertEqual(len(workspace.snapshots()),1)

    def test_empty_or_unauthorized_snapshot_is_not_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace=Workspace(Path(tmp)/'db.sqlite3')
            listings=json.loads((Path(__file__).resolve().parents[1]/'data.json').read_text())
            with self.assertRaises(ValueError):workspace.save_snapshot('None',listings,{'budget':'0'})
            with self.assertRaises(ValueError):workspace.save_snapshot('Bad',listings,{'consent':True})
            self.assertEqual(workspace.snapshots(),[])
