import csv
import io
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from cli import main

class CliTests(unittest.TestCase):
    def run_cli(self,args,source=''):
        output,error=io.StringIO(),io.StringIO()
        code=main(args,io.StringIO(source),output,error)
        return code,output.getvalue(),error.getvalue()

    def test_default_input_json_and_csv_are_readable(self):
        code,output,error=self.run_cli(['--kind','whole','--known-only'])
        self.assertEqual(code,0,error)
        self.assertEqual(json.loads(output)['listings'][0]['id'],'mesa-one')
        code,output,error=self.run_cli(['--format','csv','--sort','monthly'])
        self.assertEqual(code,0,error)
        rows=list(csv.DictReader(io.StringIO(output)))
        self.assertEqual(len(rows),4)
        self.assertEqual(rows[0]['id'],'juniper-room')

    def test_stdin_rejects_bad_shapes_and_duplicate_fields(self):
        for source in ['null','{}','[]','[{"id":"one","id":"two"}]']:
            code,output,error=self.run_cli(['--input','-'],source)
            self.assertEqual(code,2)
            self.assertEqual(output,'')
            self.assertTrue(error.startswith('Rentwise:'))

    def test_large_file_and_missing_file_fail_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'large.json';path.write_text(' '*100001)
            self.assertEqual(self.run_cli(['--input',str(path)])[0],2)
            self.assertEqual(self.run_cli(['--input',str(path.with_name('missing.json'))])[0],2)

    def test_real_process_redirects_unicode_output_as_utf8(self):
        root=Path(__file__).resolve().parents[1]
        data=json.loads((root/'data.json').read_text())
        data[0]['name']='Café 桜 – sample'
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'input.json';path.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
            result=subprocess.run([sys.executable,str(root/'cli.py'),'--input',str(path)],capture_output=True,check=True)
        payload=json.loads(result.stdout.decode('utf-8'))
        self.assertTrue(any(x['name']=='Café 桜 – sample' for x in payload['listings']))
