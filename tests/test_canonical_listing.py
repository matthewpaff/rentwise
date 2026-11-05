import json
from pathlib import Path
import unittest
from engine import costs, validate_listing

class CanonicalListingTests(unittest.TestCase):
    def setUp(self):self.item=json.loads((Path(__file__).resolve().parents[1]/'fee-lab.json').read_text())[0]

    def test_sample_costs_do_not_double_count_derived_legacy_fields(self):
        normalized=validate_listing(self.item)
        self.assertEqual(normalized['base'],'1500.00')
        self.assertEqual(normalized['required'],'60.00')
        result=costs(normalized)
        self.assertEqual(result['total'],'18545.00')
        self.assertEqual(result['cash_outlay'],'19345.00')
        self.assertEqual(result['refundable_deposits'],'800.00')
        self.assertEqual(costs(normalized,include_optional=True)['monthly'],'1650.00')

    def test_missing_price_completeness_is_not_an_implicit_guarantee(self):
        del self.item['price_completeness']
        result=costs(validate_listing(self.item))
        self.assertFalse(result['complete'])
        self.assertEqual(result['unknown'],[])

    def test_complete_claim_conflicts_with_unpriced_required_fee(self):
        self.item['fees'][1]['amount']=None
        with self.assertRaises(ValueError):validate_listing(self.item)
        self.item['price_completeness']='partial'
        result=costs(validate_listing(self.item))
        self.assertFalse(result['complete'])
        self.assertIn('Water service',result['unknown'])

    def test_currency_and_observation_date_must_be_explicitly_supported(self):
        self.item['currency']='EUR'
        with self.assertRaises(ValueError):validate_listing(self.item)
        self.item['currency']='USD';self.item['observed_at']='2026-02-30'
        with self.assertRaises(ValueError):validate_listing(self.item)
