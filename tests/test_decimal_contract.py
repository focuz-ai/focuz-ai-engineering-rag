from dataclasses import replace
from datetime import date
from decimal import Decimal, ROUND_DOWN, localcontext
from fractions import Fraction
import unittest
from rag.core import Principal
from rag.estimation import HistoricalEstimator, HistoricalTask, fixture, price


def exact_cents(hours, rate, contingency):
    value = Fraction(hours) * Fraction(rate) * (1 + Fraction(contingency) / 100) * 100
    cents = (2 * value.numerator + value.denominator) // (2 * value.denominator)
    return f'{cents // 100}.{cents % 100:02d}'


class DecimalContractTests(unittest.TestCase):
    def test_cent_boundaries_independent_of_global_decimal_context(self):
        cases = [('1', '1.00499999999999999999999999999', '0', '1.00'),
                 ('1', '1.005', '0', '1.01'),
                 ('1', '1.00500000000000000000000000001', '0', '1.01'),
                 ('1', '0.00499999999999999999999999999', '0', '0.00'),
                 ('1', '0.005', '0', '0.01'),
                 ('100000', '1000000', '100', '200000000000.00'),
                 ('1e-64', '1e-64', '0', '0.00')]
        with localcontext() as context:
            context.prec, context.rounding, context.Emin, context.Emax = 3, ROUND_DOWN, -9, 9
            for signal in context.traps:
                context.traps[signal] = True
            context.clear_flags()
            for hours, rate, contingency, expected in cases:
                with self.subTest(hours=hours, rate=rate):
                    self.assertEqual(price(hours, rate, contingency), expected)
            self.assertEqual((context.prec, context.rounding, context.Emin, context.Emax), (3, ROUND_DOWN, -9, 9))
            self.assertFalse(any(context.flags.values()))

    def test_high_precision_prices_match_independent_fraction_oracle(self):
        for index in range(1, 26):
            digits = (str(7919 * index) * 20)[:64]
            hours, rate, contingency = '1.' + digits, '0.' + digits, '0.' + digits
            with self.subTest(index=index):
                self.assertEqual(price(hours, rate, contingency), exact_cents(hours, rate, contingency))

    def test_explicit_scale_limits_and_exact_median_guard_digit(self):
        self.assertEqual(price('1e-64', '1', '1e-64'), '0.00')
        for hours, rate, contingency in (('1e-65', '1', '0'), ('1', '1e-65', '0'), ('1', '1', '1e-65')):
            with self.subTest(hours=hours, rate=rate, contingency=contingency), self.assertRaisesRegex(ValueError, '64 decimales'):
                price(hours, rate, contingency)
        sample = fixture()[0]
        with self.assertRaisesRegex(ValueError, '63 decimales'):
            HistoricalEstimator([HistoricalTask(sample.document, '1e-64')])
        estimator = HistoricalEstimator([
            HistoricalTask(sample.document, '100000'),
            HistoricalTask(replace(sample.document, id='small'), '1e-63')])
        with localcontext() as context:
            context.prec = 3
            for signal in context.traps:
                context.traps[signal] = True
            result = estimator.estimate('Autenticación login usuarios', Principal('A', ('analyst',)), date(2026, 11, 2))
            self.assertEqual(Fraction(result['hours']), (Fraction('100000') + Fraction('1e-63')) / 2)
            self.assertEqual(Decimal(result['hours']).as_tuple().exponent, -64)
            self.assertEqual(price(result['hours'], '1'), '50000.00')
