import unittest
from gt_invest.__main__ import example_candles
from gt_invest.models import Candle
from gt_invest.strategy import scan_breakout


class TestBreakout(unittest.TestCase):
    def test_synthetic_breakout(self):
        signal = scan_breakout(example_candles())
        self.assertIsNotNone(signal)
        self.assertEqual(signal.symbol, "SYNTHETIC_DEMO")
        self.assertGreater(signal.volume_ratio, 1.5)

    def test_rejects_no_breakout(self):
        bars = example_candles()
        last = bars[-1]
        bars[-1] = Candle(last.session, last.symbol, 150, 154, 148, 151, 2_000_000)
        self.assertIsNone(scan_breakout(bars))

    def test_rejects_short_history(self):
        self.assertIsNone(scan_breakout(example_candles()[-10:]))

    def test_rejects_low_volume(self):
        bars = example_candles()
        last = bars[-1]
        bars[-1] = Candle(last.session, last.symbol, last.open, last.high, last.low, last.close, 500_000)
        self.assertIsNone(scan_breakout(bars))

    def test_rejects_volume_between_one_and_threshold(self):
        bars = example_candles()
        last = bars[-1]
        bars[-1] = Candle(last.session, last.symbol, last.open, last.high, last.low, last.close, 1_200_000)
        self.assertIsNone(scan_breakout(bars))

    def test_accepts_volume_exactly_at_threshold(self):
        bars = example_candles()
        last = bars[-1]
        bars[-1] = Candle(last.session, last.symbol, last.open, last.high, last.low, last.close, 1_500_000)
        self.assertAlmostEqual(scan_breakout(bars).volume_ratio, 1.5)

    def test_momentum_measured_exactly_63_sessions_back(self):
        bars = example_candles()
        signal = scan_breakout(bars)
        self.assertAlmostEqual(signal.momentum_63d, bars[-1].close / bars[-1 - 63].close - 1)

    def test_rejects_duplicate_session(self):
        bars = example_candles()
        bars[-1] = Candle(bars[-2].session, bars[-1].symbol, 185, 192, 183, 190, 2_000_000)
        self.assertIsNone(scan_breakout(bars))


if __name__ == "__main__":
    unittest.main()
