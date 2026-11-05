"""Canonical USD fee schema. Amounts are exact strings; no currency conversion."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

def amount(value):
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        raise ValueError('Amounts must be decimal strings or integers, never floats')
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('Invalid amount') from exc
    if not result.is_finite() or not 0 <= result <= Decimal('1000000') or result.as_tuple().exponent < -2:
        raise ValueError('Amount must be nonnegative, at most 1000000, with at most two decimals')
    return result

def cents(value):
    return format(value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP), '.2f')

def validate_fees(fees, currency='USD'):
    if currency != 'USD':
        raise ValueError('Only USD is supported; currencies are never silently converted')
    if not isinstance(fees, list) or not 1 <= len(fees) <= 60:
        raise ValueError('fees must contain 1–60 components')
    result, ids = [], set()
    for fee in fees:
        if not isinstance(fee, dict) or set(fee) - {'id','label','amount','cadence','required','refundable','source'}:
            raise ValueError('Invalid fee component fields')
        for field in ('id','label'):
            if not isinstance(fee.get(field), str) or not 1 <= len(fee[field].strip()) <= 120:
                raise ValueError('Fee ' + field + ' is required')
        if fee['id'] in ids:
            raise ValueError('Fee IDs must be unique')
        ids.add(fee['id'])
        if fee.get('cadence') not in ('monthly','once'):
            raise ValueError('Fee cadence must be monthly or once')
        for key in ('required','refundable'):
            if key in fee and type(fee[key]) is not bool:
                raise ValueError(key + ' must be boolean')
        if fee.get('refundable', False) and fee['cadence'] != 'once':
            raise ValueError('Refundable deposits must be one-time charges')
        if not isinstance(fee.get('source',''), str) or len(fee.get('source','')) > 2000:
            raise ValueError('Fee source must be text of at most 2000 characters')
        result.append({**fee, 'amount': None if fee.get('amount') is None else cents(amount(fee['amount'])), 'required':fee.get('required',True),'refundable':fee.get('refundable',False)})
    return result
