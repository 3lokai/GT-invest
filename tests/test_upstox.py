import gzip
import json
import unittest
from collections import deque

from gt_invest.models import Candle
from gt_invest.upstox import _throttle, by_day, parse, parse_instruments

# Shape of a real v3 historical-candle response (newest first); values are made up.
RESPONSE = json.dumps({"status": "success", "data": {"candles": [
    ["2026-11-02T00:00:00+05:30", 1228.1, 1300.0, 1214.2, 1300.0, 88121121, 0],
    ["2026-10-30T00:00:00+05:30", 1170.4, 1174.6, 1152.5, 1164.9, 14753650, 0],
]}}).encode()


def c(session, symbol):
    return Candle(session, symbol, 10, 11, 9, 10, 100)


class TestUpstox(unittest.TestCase):
    def test_parse_sorts_oldest_first_and_uses_ist_date(self):
        candles = parse(RESPONSE, "RELIANCE")
        self.assertEqual([x.session for x in candles], ["2026-10-30", "2026-11-02"])
        self.assertEqual((candles[1].symbol, candles[1].close, candles[1].volume), ("RELIANCE", 1300.0, 88121121))

    def test_instruments_keep_only_mainboard_eq(self):
        rows = [
            {"segment": "NSE_EQ", "instrument_type": "EQ", "trading_symbol": "GOOD", "instrument_key": "NSE_EQ|INE1", "isin": "INE1"},
            {"segment": "NSE_EQ", "instrument_type": "EQ", "trading_symbol": "GOLDETF", "instrument_key": "NSE_EQ|INF1", "isin": "INF1"},
            {"segment": "NSE_EQ", "instrument_type": "SM", "trading_symbol": "SMEONE", "instrument_key": "NSE_EQ|INE2"},
            {"segment": "NSE_EQ", "instrument_type": "BE", "trading_symbol": "WATCHED", "instrument_key": "NSE_EQ|INE3"},
            {"segment": "NSE_FO", "instrument_type": "FUT", "trading_symbol": "GOOD FUT", "instrument_key": "NSE_FO|1"},
        ]
        self.assertEqual(parse_instruments(gzip.compress(json.dumps(rows).encode())), {"GOOD": "NSE_EQ|INE1"})

    def test_by_day_groups_sessions_and_drops_half_published_last_day(self):
        full = [c(s, sym) for s in ("2026-10-30", "2026-11-02") for sym in "ABCDEFGHIJ"]
        days = by_day(full + [c("2026-11-03", "A")])
        self.assertEqual([d[0].session for d in days], ["2026-10-30", "2026-11-02"])
        self.assertEqual(len(days[-1]), 10)
        self.assertEqual(len(by_day(full + [c("2026-11-03", s) for s in "ABCDEFGHI"])), 3)

    def test_throttle_waits_once_a_window_is_full(self):
        now, sleeps, sent = [0.0], [], deque(maxlen=2000)
        clock = lambda: now[0]
        def sleep(seconds):
            sleeps.append(seconds)
            now[0] += seconds
        for _ in range(50):
            _throttle(sent, clock, sleep)
        self.assertEqual(sleeps, [])
        _throttle(sent, clock, sleep)  # 51st request inside the same second
        self.assertEqual(sleeps, [1.0])
        for _ in range(2000 - 51):
            now[0] += 0.2  # 5 per second: under the 1 s and 1 min limits
            _throttle(sent, clock, sleep)
        sleeps.clear()
        _throttle(sent, clock, sleep)  # 2001st request: must wait for the 30-minute window
        self.assertGreater(sum(sleeps), 1000)


if __name__ == "__main__":
    unittest.main()
