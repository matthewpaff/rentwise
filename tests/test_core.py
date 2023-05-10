import json
from pathlib import Path
import tempfile
import unittest
from engine import BookingStore, costs, money, validate_listing
from model_adapter import OllamaAdapter, validate_preferences

class CostTests(unittest.TestCase):
    def setUp(self):
        self.item = json.loads((Path(__file__).resolve().parents[1] / 'data.json').read_text())[0]

    def test_decimal_exactness_and_optional(self):
        self.item.update(base='0.10', required='0.20', optional='0.01', upfront='0.05')
        self.assertEqual(costs(self.item, 3)['total'], '0.95')
        self.assertEqual(costs(self.item, 3, True)['total'], '0.98')

    def test_unknown_is_never_claimed_complete(self):
        result=costs(self.item)
        self.assertFalse(result['complete'])
        self.assertEqual(result['unknown'], ['Electricity usage'])
        self.assertEqual(result['monthly'], '1775.00')

    def test_bad_money_and_term(self):
        for value in ['NaN','Infinity','-1','1.001',True,None]:
            with self.subTest(value=value), self.assertRaises(ValueError): money(value)
        with self.assertRaises(ValueError): costs(self.item, True)
        self.item['kind']='apartment'
        with self.assertRaises(ValueError): validate_listing(self.item)

class BookingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.now=100.0
        self.path=Path(self.tmp.name)/'db.sqlite3'
        self.store=BookingStore(self.path, lambda:self.now)

    def tearDown(self): self.tmp.cleanup()

    def test_consent_required(self):
        for consent in [False, 'true', 1, None]:
            with self.assertRaises(ValueError): self.store.book('request-01','home',consent)

    def test_idempotency_persists_and_conflict_rejected(self):
        first=self.store.book('request-01','home',True)
        other=BookingStore(self.path, lambda:999)
        self.assertEqual(first,other.book('request-01','home',True))
        with self.assertRaises(ValueError): other.book('request-01','different',True)

    def test_pending_timeout_reconciliation(self):
        self.store.book('request-01','home',True)
        self.assertEqual(self.store.reconcile('request-01')['status'],'pending')
        self.now += 6
        self.assertEqual(self.store.book('request-01','home',True)['status'],'pending')
        self.assertEqual(self.store.reconcile('request-01')['status'],'sandbox_confirmed')
        self.assertEqual(self.store.reconcile('request-01')['status'],'sandbox_confirmed')
        with self.assertRaises(ValueError):self.store.reconcile([])

class ModelTests(unittest.TestCase):
    def test_mock_structured_transport(self):
        calls=[]
        def transport(payload):
            calls.append(payload)
            return {'message':{'content':'{"budget":"1800","kind":"whole","months":12}'}}
        result=OllamaAdapter('example',transport).propose_preferences('Entire home under 1800')
        self.assertEqual(result['budget'],'1800.00')
        self.assertFalse(calls[0]['stream'])
        self.assertEqual(calls[0]['format'],'json')

    def test_malformed_and_untrusted_model_fields(self):
        for output in ['[]','{"consent":true}','{"known_only":"yes"}','{"months":false}','not json']:
            adapter=OllamaAdapter('example',lambda _: {'message':{'content':output}})
            with self.subTest(output=output),self.assertRaises(ValueError):adapter.propose_preferences('test')

    def test_transport_failure_is_visible(self):
        def fail(_): raise OSError('offline')
        with self.assertRaises(OSError):OllamaAdapter('example',fail).propose_preferences('test')

    def test_strict_filter_booleans(self):
        with self.assertRaises(ValueError):validate_preferences({'known_only':1})

if __name__=='__main__':unittest.main()
