import io
import unittest
import zipfile

from gt_invest.bhavcopy import histories, parse
from gt_invest.models import Candle

HEADER = ("TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,"
          "FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,"
          "LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,"
          "TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4")


def row(symbol, series, close, isin="INE000000000"):
    return (f"2026-10-30,2026-10-30,CM,NSE,STK,1,{isin},{symbol},{series},,,,,{symbol} LTD,"
            f"{close},{close + 1},{close - 1},{close},{close},{close},,{close},,,1000,0,10,F1,1,,,,,")


def zipped(*lines):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("bhav.csv", "\n".join([HEADER, *lines]) + "\n")
    return buf.getvalue()


def c(day, symbol, open_, close):
    return Candle(f"2026-10-{day:02d}", symbol, open_, max(open_, close), min(open_, close), close, 1000)


class TestBhavcopy(unittest.TestCase):
    def test_parse_keeps_only_mainboard_eq(self):
        candles = parse(zipped(row("GOOD", "EQ", 100.5), row("SMEONE", "SM", 50), row("WATCHED", "BE", 20),
                                 row("GOLDETF", "EQ", 90, "INF000000000")))
        self.assertEqual([x.symbol for x in candles], ["GOOD"])
        self.assertEqual((candles[0].session, candles[0].close, candles[0].volume), ("2026-10-30", 100.5, 1000))

    def test_history_cut_at_split_gap(self):
        days = [[c(1, "S", 100, 100)], [c(2, "S", 101, 102)], [c(3, "S", 51, 52)], [c(4, "S", 52, 53)]]
        self.assertEqual([x.session for x in histories(days)["S"]], ["2026-10-03", "2026-10-04"])

    def test_history_cut_at_missing_session(self):
        days = [[c(1, "S", 100, 100)], [], [c(3, "S", 100, 101)], [c(4, "S", 101, 102)]]
        self.assertEqual(len(histories(days)["S"]), 2)

    def test_normal_moves_kept_and_delisted_dropped(self):
        days = [[c(1, "S", 100, 100), c(1, "GONE", 10, 10)], [c(2, "S", 115, 118)], [c(3, "S", 118, 100)]]
        h = histories(days)
        self.assertEqual(len(h["S"]), 3)
        self.assertNotIn("GONE", h)


if __name__ == "__main__":
    unittest.main()
