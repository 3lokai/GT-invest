import unittest
from datetime import date
from decimal import Decimal

from gt_invest.__main__ import example_candles
from gt_invest.backtest import BacktestConfig, Costs, run, xirr
from gt_invest.models import Candle


def days_with(*after):
    """The synthetic breakout (signal on its last bar, close 190, stop 176.70) plus later bars."""
    bars = example_candles()
    extra = [Candle(f"2025-08-{10 + i:02d}", "SYNTHETIC_DEMO", o, h, l, c, 1_000_000)
             for i, (o, h, l, c) in enumerate(after)]
    return [[b] for b in bars + extra], bars[-1].session


class TestBacktest(unittest.TestCase):
    def test_upstox_delivery_charges(self):
        # ₹20 + 0.00317% exchange/SEBI, GST 18% on both; 0.1% STT + 0.015% stamp
        self.assertEqual(Costs().charges(Decimal("6318.84"), buy=True), Decimal("31.10"))
        self.assertEqual(Costs().charges(Decimal("5816.58"), buy=False), Decimal("53.23"))

    def test_enters_next_open_and_stops_out(self):
        days, start = days_with((191, 193, 189, 192), (185, 186, 175, 176))
        result = run(days, start)
        [t] = result.trades
        # risk 0.5% of ₹1L = ₹500 over (191.48 - 176.70) per share -> 33 shares
        self.assertEqual((t.quantity, t.entry_price, t.exit_price), (33, Decimal("191.48"), Decimal("176.26")))
        self.assertEqual((t.reason, t.pnl), ("stop", Decimal("-586.59")))
        self.assertEqual(result.open_positions, [])

    def test_skips_entry_when_next_open_gaps_too_far(self):
        days, start = days_with((197, 199, 196, 198))  # > 3% above the 190 signal close
        result = run(days, start)
        self.assertEqual((result.trades, result.open_positions), ([], []))
        self.assertEqual(result.skipped, {"next open too far from signal close": 1})

    def test_no_fill_while_locked_at_circuit_then_gap_exit(self):
        days, start = days_with((191, 193, 189, 192), (170, 170, 170, 170), (172, 174, 171, 173))
        [t] = run(days, start).trades
        self.assertEqual((t.exit_session, t.reason, t.exit_price), ("2025-08-12", "gapped through stop", Decimal("171.57")))

    def test_minimum_trade_notional_filter_is_opt_in(self):
        days, start = days_with((191, 193, 189, 192))
        base = run(days, start)
        self.assertEqual(len(base.open_positions), 1)
        filtered = run(days, start, BacktestConfig(min_position_notional=Decimal("10000")))
        self.assertEqual(filtered.open_positions, [])
        self.assertEqual(filtered.skipped.get("position below minimum notional"), 1)

    def test_negative_research_amounts_rejected(self):
        days, start = days_with((191, 193, 189, 192))
        with self.assertRaises(ValueError):
            run(days, start, BacktestConfig(min_position_notional=Decimal("-1")))

    def test_xirr(self):
        self.assertAlmostEqual(xirr([(date(2025, 1, 1), -100), (date(2026, 1, 1), 110)]), 0.10, places=6)


if __name__ == "__main__":
    unittest.main()
