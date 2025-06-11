"""Deterministic, provider-independent rental decision and sandbox booking core."""
from decimal import Decimal, InvalidOperation
from contextlib import contextmanager
import json
import sqlite3
import time
from datetime import date
from finance import validate_fees, validate_credits, fee_totals

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
    try:
        date.fromisoformat(item['observed_at'])
    except ValueError as exc:
        raise ValueError('observed_at must be an ISO calendar date') from exc
    currency=item.get('currency','USD')
    if currency!='USD':
        raise ValueError('Only USD listings are supported')
    if 'fees' in item:
        fees=validate_fees(item['fees'],currency)
        result={k:item[k] for k in ('id','name','area','kind','source','excerpt','observed_at')}
        result.update(currency=currency,fees=fees,credits=validate_credits(item.get('credits',[])))
        # Compatibility totals are derived rather than trusted when components exist.
        def subtotal(cadence,required):
            return format(sum((money(f['amount']) for f in fees if f['amount'] is not None and f['cadence']==cadence and f['required']==required),money('0')),'.2f')
        base=sum((money(f['amount']) for f in fees if f['id'] in ('rent','base') and f['required'] and f['cadence']=='monthly' and f['amount'] is not None),money('0'))
        result.update(base=format(base,'.2f'),required=format(money(subtotal('monthly',True))-base,'.2f'),optional=subtotal('monthly',False),upfront=format(sum((money(f['amount']) for f in fees if f['amount'] is not None and f['cadence']=='once'),money('0')),'.2f'),unknown=[f['label'] for f in fees if f['required'] and f['amount'] is None])
        completeness=item.get('price_completeness','unspecified')
        if completeness not in ('complete','partial','unspecified'):
            raise ValueError('price_completeness must be complete, partial or unspecified')
        if completeness=='complete' and result['unknown']:
            raise ValueError('Complete price cannot contain unknown required fees')
        result['price_completeness']=completeness
        return result
    for key in MONEY_KEYS:
        money(item.get(key))
    if not isinstance(item.get('unknown'), list) or len(item['unknown']) > 30 or any(not isinstance(x, str) or len(x) > 200 for x in item['unknown']):
        raise ValueError('unknown must be an array of fee names')
    return {**{k: item[k] for k in ('id','name','area','kind','source','excerpt','observed_at','unknown')}, **{k: format(money(item[k]), '.2f') for k in MONEY_KEYS}}

def costs(item, months=12, include_optional=False):
    if 'fees' in item:
        result=fee_totals(item['fees'],months,include_optional,item.get('credits'))
        result['complete']=result['complete'] and item.get('price_completeness')=='complete'
        result.update(source=item['source'],excerpt=item['excerpt'])
        return result
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
            db.execute('CREATE TABLE IF NOT EXISTS booking_events (id INTEGER PRIMARY KEY AUTOINCREMENT, booking_key TEXT NOT NULL, occurred REAL NOT NULL, previous_status TEXT, status TEXT NOT NULL, reason TEXT NOT NULL)')

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
        if not isinstance(listing,str) or not 1<=len(listing)<=60:
            raise ValueError('Invalid listing ID')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous=db.execute('SELECT * FROM bookings WHERE key=?',(key,)).fetchone()
            if previous:
                if previous[1]!=listing:raise ValueError('Idempotency key already belongs to another listing')
                return self.serialize(previous)
            existing=db.execute('SELECT key FROM bookings WHERE listing=? AND status IN (?,?) AND key<>?',(listing,'pending','sandbox_confirmed',key)).fetchone()
            if existing:raise ValueError('An active sandbox request already exists for this listing; inspect booking history')
            created=db.execute('INSERT OR IGNORE INTO bookings VALUES (?, ?, ?, ?)', (key, listing, self.clock(), 'pending')).rowcount
            if created:
                db.execute('INSERT INTO booking_events(booking_key,occurred,previous_status,status,reason) VALUES(?,?,?,?,?)',(key,self.clock(),None,'pending','Explicit consent recorded; local simulation only'))
            row = db.execute('SELECT * FROM bookings WHERE key=?', (key,)).fetchone()
            if row[1] != listing:
                raise ValueError('Idempotency key already belongs to another listing')
        return self.serialize(row)

    def reconcile(self, key):
        if not isinstance(key, str) or not 8 <= len(key) <= 100:
            raise ValueError('Invalid idempotency key')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM bookings WHERE key=?', (key,)).fetchone()
            if not row:
                raise ValueError('Unknown sandbox booking')
            # Simulate a delayed provider acknowledgement; no real external action.
            if row[3] == 'pending' and self.clock() - row[2] >= 5:
                db.execute('UPDATE bookings SET status=? WHERE key=?', ('sandbox_confirmed', key))
                db.execute('INSERT INTO booking_events(booking_key,occurred,previous_status,status,reason) VALUES(?,?,?,?,?)',(key,self.clock(),'pending','sandbox_confirmed','Simulated delayed acknowledgement'))
            row = db.execute('SELECT * FROM bookings WHERE key=?', (key,)).fetchone()
        return self.serialize(row)

    def cancel(self,key,consent):
        if consent is not True:raise ValueError('Explicit sandbox cancellation consent is required')
        if not isinstance(key,str) or not 8<=len(key)<=100:raise ValueError('Invalid idempotency key')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM bookings WHERE key=?',(key,)).fetchone()
            if not row:raise ValueError('Unknown sandbox booking')
            if row[3] not in ('pending','sandbox_confirmed','cancelled'):
                raise ValueError('Illegal sandbox state transition')
            if row[3]!='cancelled':
                db.execute('UPDATE bookings SET status=? WHERE key=?',('cancelled',key))
                db.execute('INSERT INTO booking_events(booking_key,occurred,previous_status,status,reason) VALUES(?,?,?,?,?)',(key,self.clock(),row[3],'cancelled','User explicitly cancelled local simulation'))
            row=db.execute('SELECT * FROM bookings WHERE key=?',(key,)).fetchone()
        return self.serialize(row)

    def history(self,limit=100):
        if type(limit) is not int or not 1<=limit<=500:raise ValueError('History limit must be 1–500')
        with self.connect() as db:
            rows=db.execute('SELECT * FROM bookings ORDER BY created DESC,key LIMIT ?',(limit,)).fetchall()
        return [self.serialize(row) for row in rows]

    def events(self,key):
        self.status(key)
        with self.connect() as db:
            rows=db.execute('SELECT occurred,previous_status,status,reason FROM booking_events WHERE booking_key=? ORDER BY id',(key,)).fetchall()
        return [dict(zip(('occurred','previous_status','status','reason'),row)) for row in rows]

    def status(self,key):
        if not isinstance(key,str) or not 8<=len(key)<=100:raise ValueError('Invalid idempotency key')
        with self.connect() as db:
            row=db.execute('SELECT * FROM bookings WHERE key=?',(key,)).fetchone()
        if not row:raise ValueError('Unknown sandbox booking')
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
