"""Synthetic demonstration only. Nothing is fetched from or sent to a broker."""
import argparse
from datetime import date, timedelta
from decimal import Decimal

from .models import Candle
from .strategy import scan_breakout
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


def main() -> None:
    parser = argparse.ArgumentParser(description="GT Invest: paper-only research")
    parser.add_argument("--demo", action="store_true", help="Run only a synthetic signal demonstration")
    args = parser.parse_args()
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
