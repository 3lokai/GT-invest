"""Synthetic demonstration only. Nothing is fetched from or sent to a broker."""
import argparse
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from . import backtest as engine, bhavcopy, upstox
from .models import Candle
from .strategy import average_close, scan_breakout, trend_label
from .risk import size_position


def example_candles() -> list[Candle]:
    """Fabricated values for a smoke test; not real stock data."""
    start = date(2025, 1, 1)
    bars: list[Candle] = []
    for i in range(220):
        price = 100 + 0.25 * i
        bars.append(Candle(
            session=(start + timedelta(days=i)).isoformat(), symbol="SYNTHETIC_DEMO",
            open=price - 0.25, high=price + 0.3,
            low=price - 0.5, close=price, volume=1_000_000,
        ))
    bars.append(Candle(
        session=(start + timedelta(days=220)).isoformat(), symbol="SYNTHETIC_DEMO",
        open=185, high=192, low=183, close=190, volume=2_000_000,
    ))
    return bars


def scan(as_of: date, source: str) -> None:
    print(f"NSE EOD SCAN ({source} data) — research candidates only, not recommendations, no orders.")
    days = (upstox if source == "upstox" else bhavcopy).load(as_of, sessions=220)
    # Upstox history is already split-adjusted; the cut then only catches missing sessions and bad prints.
    runs = bhavcopy.histories(days)
    hits = [s for run in runs.values() if (s := scan_breakout(run))]
    print(f"Session {days[-1][0].session}: {len(runs)} EQ stocks, "
          f"{sum(len(r) >= 201 for r in runs.values())} with enough clean history, {len(hits)} candidates.")
    for s in sorted(hits, key=lambda s: -s.momentum_63d):
        print(f"{s.symbol:<14} close ₹{s.reference_close:>10.2f}  stop ₹{s.indicative_stop:>10.2f}  "
              f"volume {s.volume_ratio:4.1f}x  63d {s.momentum_63d:+.0%}")


def trend(symbols: list[str], as_of: date) -> None:
    print("TREND CHECK — describes each chart, not a buy or sell recommendation, no orders.")
    runs = upstox.history(symbols, as_of, sessions=220)
    for symbol in symbols:
        run = runs.get(symbol)
        label = trend_label(run) if run else None
        if label is None:
            why = "not in the NSE mainboard EQ list" if run is None else f"only {len(run)} sessions of history"
            print(f"{symbol:<14} no label: {why}")
            continue
        close = run[-1].close
        print(f"{symbol:<14} {label:<10} {run[-1].session}  close ₹{close:>9.2f}  "
              f"50d avg ₹{average_close(run, 50):>9.2f}  200d avg ₹{average_close(run, 200):>9.2f}  "
              f"63d {close / run[-64].close - 1:+.0%}")
    print("uptrend: close > 50d avg > 200d avg. downtrend: close and 50d avg both below 200d avg. "
          "weakening: anything in between.")


def latest() -> None:
    """Three uncached requests: the newest session Upstox has published (for timing the scan).

    Several stocks, because one stock's candle can be missing (RELIANCE lacked 2026-11-03).
    """
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    runs = upstox.history(["HDFCBANK", "INFY", "SBIN"], now.date(), sessions=5, ttl=0)
    print(f"{now:%Y-%m-%d %H:%M} IST  Upstox latest daily candle: {max(r[-1].session for r in runs.values())}")


def backtest(end: date) -> None:
    """Breakout backtest on every NSE file since July 2024; writes the report to reports/."""
    days = bhavcopy.load(end)
    result = engine.run(days, start=days[200][0].session)  # the scanner needs 201 sessions
    first, last = result.curve[0][0], result.curve[-1][0]
    key = "NSE_INDEX|Nifty 500"
    data = upstox.fetch(key, date.fromisoformat(first), date.fromisoformat(last), upstox.token(), ttl=0)
    text = engine.report(result, upstox.parse(data, "NIFTY 500"), "Nifty 500")
    path = Path("reports") / f"backtest-breakout-v1-{last}.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text(text)
    print(text.split("## Stability")[0])
    print(f"Full report: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="GT Invest: paper-only research")
    parser.add_argument("--demo", action="store_true", help="Run only a synthetic signal demonstration")
    parser.add_argument("--scan", action="store_true", help="Scan NSE mainboard stocks")
    parser.add_argument("--source", choices=("upstox", "nse"), default="upstox",
                        help="--scan data: Upstox adjusted candles (default) or raw NSE bhavcopy files")
    parser.add_argument("--trend", nargs="+", metavar="SYMBOL", help="Label each symbol's chart trend (Upstox data)")
    parser.add_argument("--latest", action="store_true", help="Print the latest session Upstox has published")
    parser.add_argument("--backtest", action="store_true", help="Backtest the breakout scanner on NSE files since July 2024")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today(), help="Last session date for --scan/--trend")
    args = parser.parse_args()
    if args.latest:
        latest()
        return
    if args.backtest:
        backtest(args.as_of)
        return
    if args.trend:
        trend([s.upper() for s in args.trend], args.as_of)
        return
    if args.scan:
        scan(args.as_of, args.source)
        return
    if not args.demo:
        parser.print_help()
        return
    print("SYNTHETIC DEMO — not actual market data, not a recommendation, no orders.")
    signal = scan_breakout(example_candles())
    if signal is None:
        print("No eligible signal under current research rules.")
        return
    proposal = size_position(
        equity_inr=Decimal("100000"), available_cash_inr=Decimal("20000"),
        entry_price_inr=Decimal(str(signal.reference_close)),
        stop_price_inr=Decimal(str(signal.indicative_stop)),
    )
    print(f"End-of-day research candidate: {signal.symbol} ({signal.session})")
    print("Why: price breakout, volume confirmation, qualifying trend and momentum.")
    if proposal:
        print(f"Illustrative size: {proposal.quantity} shares, ₹{proposal.estimated_notional_inr}")
        print(f"Planned loss at indicative stop: ₹{proposal.planned_loss_at_stop_inr} (NOT guaranteed)")
    print("Status: observation only. A next-session execution could have a different price.")


if __name__ == "__main__":
    main()
