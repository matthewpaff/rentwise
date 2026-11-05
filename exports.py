"""Portable comparison exports with formula-safe spreadsheet cells."""
import csv
import io
import json

def spreadsheet_cell(value):
    value=str(value)
    if value.lstrip().startswith(('=','+','-','@')) or value.startswith(('\t','\r','\n')):
        return "'"+value
    return value

def comparison_export(results,format='json'):
    if format=='json':
        return json.dumps({'schema':'rentwise.comparison.v1','sandbox':True,'disclaimer':'Known-cost comparison only; no booking or price guarantee.','listings':results},ensure_ascii=False,indent=2)
    if format!='csv':raise ValueError('Export format must be json or csv')
    output=io.StringIO(newline='')
    writer=csv.writer(output)
    writer.writerow(['id','name','kind','currency','months','monthly_known','lease_expense_known','deposit_refundable','cash_outlay_known','price_complete','unknown_fees','source','observed_at','source_excerpt'])
    for item in results:
        c=item['cost']
        row=[item['id'],item['name'],item['kind'],c.get('currency','USD'),c['months'],c['monthly'],c['total'],c.get('refundable_deposits','0.00'),c.get('cash_outlay',c['total']),c['complete'],'; '.join(c['unknown']),item['source'],item['observed_at'],item['excerpt']]
        writer.writerow([spreadsheet_cell(v) for v in row])
    return output.getvalue()
