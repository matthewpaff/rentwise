import unittest
from finance import fee_totals, validate_fees

def fee(id, value, cadence='monthly', **kwargs):
    return dict(id=id,label=id,amount=value,cadence=cadence,**kwargs)

class FeeTests(unittest.TestCase):
    def test_deposit_is_cash_not_expense(self):
        result=fee_totals([fee('rent','1000'),fee('deposit','700','once',refundable=True),fee('admin','50','once')],3)
        self.assertEqual(result['total'],'3050.00')
        self.assertEqual(result['cash_outlay'],'3750.00')
        self.assertEqual(result['move_in_cash'],'1750.00')

    def test_optional_unknown_does_not_hide_required_price(self):
        fees=[fee('rent','1000'),fee('parking',None,required=False)]
        self.assertTrue(fee_totals(fees)['complete'])
        self.assertFalse(fee_totals(fees,include_optional=True)['complete'])

    def test_currency_and_duplicate_fee_rejection(self):
        with self.assertRaises(ValueError):validate_fees([fee('rent','2')],'EUR')
        with self.assertRaises(ValueError):validate_fees([fee('rent','2'),fee('rent','3')])
        with self.assertRaises(ValueError):validate_fees([fee('deposit','2',refundable=True)])

    def test_float_cannot_enter_canonical_engine(self):
        with self.assertRaises(ValueError):fee_totals([fee('rent',0.1)])

    def test_invalid_falsy_credits_are_not_treated_as_absent(self):
        for value in [False,0,'',{}]:
            with self.subTest(value=value),self.assertRaises(ValueError):fee_totals([fee('rent','1')],credits=value)

    def test_credit_is_conditional_and_does_not_reduce_move_in_cash(self):
        credits=[{'label':'12-month concession','amount':'500','minimum_months':12}]
        self.assertEqual(fee_totals([fee('rent','1000')],6,credits=credits)['credit_total'],'0.00')
        result=fee_totals([fee('rent','1000')],12,credits=credits)
        self.assertEqual(result['total'],'11500.00')
        self.assertEqual(result['move_in_cash'],'1000.00')
        with self.assertRaises(ValueError):fee_totals([fee('rent','1')],1,credits=[{'label':'bad','amount':'2'}])

    def test_effective_monthly_rounds_half_up_without_changing_total(self):
        result=fee_totals([fee('rent','0.01'),fee('fee','0.01','once')],2)
        self.assertEqual(result['effective_monthly'],'0.02')
        self.assertEqual(result['total'],'0.03')
        self.assertIn('0.01 monthly × 2',result['explanation'])
