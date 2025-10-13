import csv
from datetime import date
import io
import json
from pathlib import Path
import unittest
from decision import evaluate
from exports import comparison_export, spreadsheet_cell

class DecisionTests(unittest.TestCase):
    def setUp(self):self.listings=json.loads((Path(__file__).resolve().parents[1]/'data.json').read_text())

    def test_budget_exclusions_have_reasons_and_unknown_warning(self):
        result=evaluate(self.listings,{'budget':'1200'},today=date(2026,11,5))
        self.assertEqual(len(result['results']),2)
        self.assertEqual(len(result['excluded']),2)
        self.assertTrue(result['results'][0]['warnings'])
        self.assertIn('exceeds budget',result['excluded'][0]['reasons'][0])

    def test_ties_are_stable_under_input_reordering(self):
        items=self.listings[:2]
        for item in items:item.update(base='1000',required='0',upfront='0',unknown=[])
        first=evaluate(items)['results']
        second=evaluate(list(reversed(items)))['results']
        self.assertEqual([x['id'] for x in first],[x['id'] for x in second])

    def test_stale_and_future_sources_are_flagged(self):
        self.assertTrue(any('older' in x for x in evaluate(self.listings,today=date(2027,1,1))['results'][0]['warnings']))
        self.assertTrue(any('future' in x for x in evaluate(self.listings,today=date(2026,1,1))['results'][0]['warnings']))

    def test_csv_neutralizes_formula_prefixes_and_retains_citations(self):
        self.listings[0]['name']=' =HYPERLINK("x")'
        results=evaluate(self.listings)['results']
        rows=list(csv.DictReader(io.StringIO(comparison_export(results,'csv'))))
        target=next(row for row in rows if row['id']==self.listings[0]['id'])
        self.assertTrue(target['name'].startswith("'"))
        self.assertEqual(target['source_excerpt'],self.listings[0]['excerpt'])
        for value in ['=1','+1','-1','@x','\ttext','\ntext']:
            self.assertTrue(spreadsheet_cell(value).startswith("'"))

    def test_json_export_declares_no_action_authority(self):
        output=json.loads(comparison_export(evaluate(self.listings)['results']))
        self.assertTrue(output['sandbox'])
        self.assertEqual(output['schema'],'rentwise.comparison.v1')

    def test_invalid_falsy_preferences_are_not_defaults(self):
        for value in [False,0,'',[]]:
            with self.subTest(value=value),self.assertRaises(ValueError):evaluate(self.listings,value)
