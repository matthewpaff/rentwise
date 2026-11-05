"""Deterministic, provider-independent rental decision and sandbox booking core."""
from decimal import Decimal, InvalidOperation
from contextlib import contextmanager
import json
import sqlite3
import time

MONEY_KEYS = ('base', 'required', 'optional', 'upfront')

def money(value):
    if isinstance(value, bool):
        raise ValueError('Money must be a non-negative decimal string')
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError('Invalid money amount')
    if not number.is_finite() or number < 0 or number > Decimal('1000000') or number.as_tuple().exponent < -2:
        raise ValueError('Money must have at most two decimal places and be between 0 and 1000000')
    return number

def validate_listing(item):
    if not isinstance(item, dict):
        raise ValueError('Each listing must be an object')
    for key in ('id', 'name', 'area', 'kind', 'source', 'excerpt', 'observed_at'):
        if not isinstance(item.get(key), str) or not item[key].strip() or len(item[key]) > 2000:
            raise ValueError('Missing or invalid field: ' + key)
    if item['kind'] not in ('room', 'whole'):
        raise ValueError('kind must be room or whole')
    if len(item['id']) > 60 or not all(c.isalnum() or c in '-_' for c in item['id']):
        raise ValueError('id must contain only letters, digits, underscores or hyphens')
    for key in MONEY_KEYS:
        money(item.get(key))
    if not isinstance(item.get('unknown'), list) or len(item['unknown']) > 30 or any(not isinstance(x, str) or len(x) > 200 for x in item['unknown']):
        raise ValueError('unknown must be an array of fee names')
    return {**{k: item[k] for k in ('id','name','area','kind','source','excerpt','observed_at','unknown')}, **{k: format(money(item[k]), '.2f') for k in MONEY_KEYS}}

def costs(item, months=12, include_optional=False):
    if isinstance(months, bool) or not isinstance(months, int) or not 1 <= months <= 60:
        raise ValueError('months must be an integer from 1 to 60')
    monthly = money(item['base']) + money(item['required'])
    if include_optional:
        monthly += money(item['optional'])
    total = monthly * months + money(item['upfront'])
    return {'monthly': format(monthly, '.2f'), 'upfront': format(money(item['upfront']), '.2f'), 'total': format(total, '.2f'), 'months': months, 'complete': not item['unknown'], 'unknown': item['unknown'], 'optional_included': include_optional, 'source': item['source'], 'excerpt': item['excerpt']}

class BookingStore:
    """Local simulation only. A pending request cannot be retried as a new booking."""
    def __init__(self, path, clock=time.time):
        self.path, self.clock = str(path), clock
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS bookings (key TEXT PRIMARY KEY, listing TEXT NOT NULL, created REAL NOT NULL, status TEXT NOT NULL)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        try:
            with db:
                yield db
        finally:
            db.close()

    def book(self, key, listing, consent):
        if consent is not True:
            raise ValueError('Explicit sandbox consent is required')
        if not isinstance(key, str) or not 8 <= len(key) <= 100:
            raise ValueError('An idempotency key of 8–100 characters is required')
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO bookings VALUES (?, ?, ?, ?)', (key, listing, self.clock(), 'pending'))
            row = db.execute('SELECT * FROM bookings WHERE key=?', (key,)).fetchone()
            if row[1] != listing:
                raise ValueError('Idempotency key already belongs to another listing')
        return self.serialize(row)

    def reconcile(self, key):
        if not isinstance(key, str) or not 8 <= len(key) <= 100:
            raise ValueError('Invalid idempotency key')
        with self.connect() as db:
            row = db.execute('SELECT * FROM bookings WHERE key=?', (key,)).fetchone()
            if not row:
                raise ValueError('Unknown sandbox booking')
            # Simulate a delayed provider acknowledgement; no real external action.
            if row[3] == 'pending' and self.clock() - row[2] >= 5:
                db.execute('UPDATE bookings SET status=? WHERE key=?', ('sandbox_confirmed', key))
            row = db.execute('SELECT * FROM bookings WHERE key=?', (key,)).fetchone()
        return self.serialize(row)

    def serialize(self, row):
        return {'key': row[0], 'listing': row[1], 'created': row[2], 'status': row[3], 'sandbox': True, 'message': 'Simulation only. No property is reserved, payment collected, or host contacted.'}

class ModelAdapter:
    """Integration boundary: implement propose_preferences(text) -> dict.

    An implementation may suggest filters; it must never authorize bookings,
    calculate trusted prices, or bypass validate_listing. No model is called here.
    """
    def propose_preferences(self, text):
        raise NotImplementedError('No model provider configured; this demo is deterministic')
