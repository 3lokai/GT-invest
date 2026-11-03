import unittest
from decimal import Decimal
from gt_invest.risk import size_position


class TestPositionSizing(unittest.TestCase):
    def test_risk_budget_limited(self):
        p = size_position(Decimal("100000"), Decimal("20000"), Decimal("100"), Decimal("94"))
        self.assertIsNotNone(p)
        self.assertEqual(p.quantity, 83)
        self.assertEqual(p.planned_loss_at_stop_inr, Decimal("498"))
        self.assertLessEqual(p.estimated_notional_inr, Decimal("10000"))

    def test_cash_budget_limited(self):
        p = size_position(Decimal("100000"), Decimal("3000"), Decimal("100"), Decimal("99"))
        self.assertEqual(p.quantity, 30)

    def test_stop_above_entry_rejected(self):
        self.assertIsNone(size_position(Decimal("100000"), Decimal("3000"), Decimal("100"), Decimal("101")))

    def test_no_fractional_shares(self):
        self.assertIsNone(size_position(Decimal("100000"), Decimal("3000"), Decimal("10000"), Decimal("9000")))

    def test_float_money_rejected(self):
        with self.assertRaises(ValueError):
            size_position(100000, Decimal("3000"), Decimal("100"), Decimal("90"))


if __name__ == "__main__":
    unittest.main()
