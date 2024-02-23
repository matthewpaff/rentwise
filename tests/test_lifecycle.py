from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from engine import BookingStore

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.now=100
        self.store=BookingStore(Path(self.tmp.name)/'booking.sqlite3',lambda:self.now)
    def tearDown(self):self.tmp.cleanup()

    def test_cancel_is_terminal_and_retry_never_reactivates(self):
        self.store.book('request-01','sample',True)
        self.store.cancel('request-01',True)
        self.now=110
        self.assertEqual(self.store.reconcile('request-01')['status'],'cancelled')
        self.assertEqual(self.store.book('request-01','sample',True)['status'],'cancelled')
        self.assertEqual(len(self.store.events('request-01')),2)

    def test_concurrent_distinct_keys_only_create_one_active_request(self):
        def create(n):
            try:return self.store.book('request-'+str(n),'sample',True)['status']
            except ValueError:return 'duplicate'
        with ThreadPoolExecutor(max_workers=4) as pool:
            statuses=list(pool.map(create,range(4)))
        self.assertEqual(statuses.count('pending'),1)
        self.assertEqual(statuses.count('duplicate'),3)
        self.assertEqual(len(self.store.history()),1)

    def test_reconciliation_race_emits_single_transition(self):
        self.store.book('request-01','sample',True)
        self.now=110
        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(lambda _:self.store.reconcile('request-01'),range(3)))
        self.assertEqual(len(self.store.events('request-01')),2)
        with self.assertRaises(ValueError):self.store.cancel('request-01','yes')
        self.assertEqual(self.store.status('request-01')['status'],'sandbox_confirmed')
