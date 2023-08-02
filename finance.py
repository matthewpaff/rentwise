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

def validate_credits(credits):
    if not isinstance(credits,list) or len(credits)>20:
        raise ValueError('credits must be an array of at most 20 items')
    normalized=[]
    for credit in credits:
        if not isinstance(credit,dict) or set(credit)-{'label','amount','minimum_months','source'}:
            raise ValueError('Invalid credit fields')
        if not isinstance(credit.get('label'),str) or not 1<=len(credit['label'].strip())<=200:
            raise ValueError('Credit label is required')
        minimum=credit.get('minimum_months',1)
        if type(minimum) is not int or not 1<=minimum<=60:
            raise ValueError('Credit minimum_months must be 1–60')
        if not isinstance(credit.get('source',''),str) or len(credit.get('source',''))>2000:
            raise ValueError('Invalid credit source')
        normalized.append({**credit,'amount':cents(amount(credit.get('amount'))),'minimum_months':minimum})
    return normalized

def fee_totals(fees, months=12, include_optional=False, credits=None):
    if type(months) is not int or not 1 <= months <= 60:
        raise ValueError('months must be an integer from 1 to 60')
    if type(include_optional) is not bool:
        raise ValueError('include_optional must be boolean')
    fees = validate_fees(fees)
    included = [f for f in fees if f['required'] or include_optional]
    monthly = sum((amount(f['amount']) for f in included if f['cadence']=='monthly' and f['amount'] is not None), Decimal(0))
    upfront = sum((amount(f['amount']) for f in included if f['cadence']=='once' and f['amount'] is not None), Decimal(0))
    unknown = [f['label'] for f in included if f['amount'] is None]
    deposits = sum((amount(f['amount']) for f in included if f['refundable'] and f['amount'] is not None), Decimal(0))
    total = monthly*months+upfront-deposits
    eligible = [c for c in validate_credits(credits or []) if months>=c['minimum_months']]
    credit_total = sum((amount(c['amount']) for c in eligible),Decimal(0))
    if credit_total>total:
        raise ValueError('Eligible credits cannot exceed known nonrefundable lease cost')
    total -= credit_total
    return {'monthly':cents(monthly),'upfront':cents(upfront),'total':cents(total),'cash_outlay':cents(total+deposits),'credits_applied':eligible,'credit_total':cents(credit_total),'refundable_deposits':cents(deposits),'move_in_cash':cents(monthly+upfront),'months':months,'currency':'USD','complete':not unknown,'unknown':unknown,'optional_included':include_optional,'components':included}
