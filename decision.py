"""Explainable deterministic ranking shared by HTTP and command line."""
from datetime import date
from decimal import Decimal
from engine import costs, money
from workspace import corpus
from model_adapter import validate_preferences

def evaluate(listings,preferences=None,today=None):
    preferences=validate_preferences(preferences or {})
    listings=corpus(listings)
    today=today or date.today()
    budget=money(preferences.get('budget','1000000'))
    months=preferences.get('months',12)
    results=[]
    excluded=[]
    for item in listings:
        cost=costs(item,months,preferences.get('optional',False))
        reasons=[]
        if money(cost['monthly'])>budget:reasons.append('Known monthly cost exceeds budget')
        if preferences.get('kind','all') not in ('all',item['kind']):reasons.append('Space type does not match')
        if preferences.get('known_only',False) and not cost['complete']:reasons.append('Price is not fully specified')
        if reasons:
            excluded.append({'id':item['id'],'reasons':reasons})
            continue
        warnings=[]
        if not cost['complete']:warnings.append('Known-cost lower bound: full price is not established')
        if cost['unknown']:warnings.append('Unpriced charges: '+', '.join(cost['unknown']))
        observed=date.fromisoformat(item['observed_at'])
        age=(today-observed).days
        if age>30:warnings.append('Source observation is older than 30 days; recheck before acting')
        if age<0:warnings.append('Source observation is in the future; verify provenance')
        results.append({**item,'cost':cost,'warnings':warnings,'ranking':{'basis':'known lease expense ascending, then complete price, then listing ID','known_budget_headroom':format(budget-money(cost['monthly']),'.2f')}})
    mode=preferences.get('sort','total')
    def order(item):
        cost=item['cost']
        if mode=='monthly':primary=Decimal(cost['monthly'])
        elif mode=='effective':primary=Decimal(cost['total'])/months
        elif mode=='completeness':primary=not cost['complete']
        else:primary=Decimal(cost['total'])
        return primary,not cost['complete'],Decimal(cost['total']),item['id']
    results.sort(key=order)
    for item in results:item['ranking']['basis']={'total':'known lease expense','monthly':'known recurring monthly cost','effective':'exact effective monthly expense','completeness':'explicit price completeness'}[mode]+' ascending; deterministic price and ID tie-breaks'
    for rank,item in enumerate(results,1):item['ranking']['position']=rank
    return {'results':results,'excluded':excluded,'preferences':preferences,'method':'Deterministic Decimal arithmetic; unknown fees excluded and flagged. Ranking uses known lease expense, not a prediction of final price.'}
