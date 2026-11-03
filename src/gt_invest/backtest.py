"""Daily event-driven backtest of the breakout scanner on point-in-time NSE data.

Research only: every fill is simulated and nothing is sent anywhere. The protocol is in
docs/STRATEGY.md section 5. Signals come from the same `scan_breakout` and sizing from the
same `size_position` as the live scan, so paper and research share one set of rules.
"""
from collections import deque
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from itertools import islice

from .bhavcopy import continues
from .models import BreakoutSignal, Candle
from .risk import RiskLimits, size_position
from .strategy import BreakoutConfig, average_close, scan_breakout

D = Decimal
PAISA = D("0.01")


def _d(x: float) -> Decimal:
    return D(str(x))


@dataclass(frozen=True)
class Costs:
    """Upstox equity delivery charges, from upstox.com/brokerage-charges on 2026-11-04."""
    brokerage_per_order: Decimal = D("20")
    stt: Decimal = D("0.001")            # buy and sell
    exchange: Decimal = D("0.0000307")   # NSE since 2026-03-01 (0.00297% before); used throughout
    sebi: Decimal = D("0.000001")        # ₹10 per crore
    stamp_on_buy: Decimal = D("0.00015")
    dp_per_sell: Decimal = D("20")       # per stock per day sold
    gst: Decimal = D("0.18")             # on brokerage, exchange, SEBI and DP charges

    def charges(self, notional: Decimal, buy: bool) -> Decimal:
        fixed = self.brokerage_per_order + (0 if buy else self.dp_per_sell)
        gst_base = fixed + notional * (self.exchange + self.sebi)
        taxes = notional * (self.stt + (self.stamp_on_buy if buy else 0))
        return (gst_base * (1 + self.gst) + taxes).quantize(PAISA, ROUND_HALF_UP)


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: Decimal = D("100000")
    monthly_contribution: Decimal = D("20000")
    slippage: Decimal = D("0.0025")     # per fill, always against us
    max_entry_gap: Decimal = D("0.03")  # skip if the next open is over 3% above the signal close
    trail_sessions: int = 20            # sell at the next open after a close below this average
    strategy: BreakoutConfig = field(default_factory=BreakoutConfig)
    limits: RiskLimits = field(default_factory=RiskLimits)
    costs: Costs = field(default_factory=Costs)


@dataclass
class Position:
    symbol: str
    quantity: int
    entry_session: str
    entry_price: Decimal
    stop: Decimal
    cost: Decimal  # notional plus buy charges
    last: Candle
    sell_next_open: bool = False


@dataclass(frozen=True)
class Trade:
    symbol: str
    entry_session: str
    exit_session: str
    quantity: int
    entry_price: Decimal
    exit_price: Decimal
    charges: Decimal
    pnl: Decimal          # after all charges
    planned_loss: Decimal  # at the stop, before charges
    reason: str


@dataclass
class Result:
    config: BacktestConfig
    curve: list[tuple[str, float, float]] = field(default_factory=list)  # session, NAV per unit, value
    flows: list[tuple[str, Decimal]] = field(default_factory=list)       # contributions
    trades: list[Trade] = field(default_factory=list)
    open_positions: list[Position] = field(default_factory=list)
    skipped: dict[str, int] = field(default_factory=dict)


def run(days: list[list[Candle]], start: str, config: BacktestConfig | None = None) -> Result:
    """Simulate trading from session `start`; earlier days only warm up the indicators.

    `days` is oldest first, one list of candles per session, as `bhavcopy.load` returns it.
    """
    cfg = config or BacktestConfig()
    s = cfg.strategy
    window = max(s.breakout_sessions, s.fast_sessions, s.slow_sessions, s.momentum_sessions) + 1
    result = Result(cfg)
    runs: dict[str, deque[Candle]] = {}
    positions: dict[str, Position] = {}
    pending: list[BreakoutSignal] = []
    cash, units, month = D(0), D(0), None

    def value() -> Decimal:
        return cash + sum(p.quantity * _d(p.last.close) for p in positions.values())

    def sell(p: Position, price: Decimal, session: str, reason: str) -> None:
        nonlocal cash
        price = price.quantize(PAISA, ROUND_HALF_UP)
        notional = price * p.quantity
        charges = cfg.costs.charges(notional, buy=False)
        cash += notional - charges
        result.trades.append(Trade(
            p.symbol, p.entry_session, session, p.quantity, p.entry_price, price,
            p.cost - p.entry_price * p.quantity + charges, notional - charges - p.cost,
            (p.entry_price - p.stop) * p.quantity, reason,
        ))
        del positions[p.symbol]

    def skip(reason: str) -> None:
        result.skipped[reason] = result.skipped.get(reason, 0) + 1

    for day in days:
        session = day[0].session
        today = {c.symbol: c for c in day}
        for symbol in [x for x in runs if x not in today]:
            del runs[symbol]  # missing session: the series restarts, as in bhavcopy.histories
        for symbol, bar in today.items():
            series = runs.get(symbol)
            if series and continues(series[-1], bar):
                series.append(bar)
            else:
                runs[symbol] = deque([bar], maxlen=window)
        if session < start:
            continue

        if session[:7] != month:  # contribute on the first session of each month
            amount = cfg.initial_cash if month is None else cfg.monthly_contribution
            nav = value() / units if units else D(100)
            units += amount / nav
            cash += amount
            result.flows.append((session, amount))
            month = session[:7]

        # At the open: gaps we can't trust, trailing exits, gaps through the stop.
        slip_down = 1 - cfg.slippage
        for p in list(positions.values()):
            bar = today.get(p.symbol)
            if bar is None:
                continue  # suspended, moved series or delisted: can't sell, stays at last price
            if not continues(p.last, bar):
                # ponytail: >25% overnight on unadjusted data is almost always a split/bonus;
                # closing at the last price is neutral, so a real crash would be flattered here.
                sell(p, _d(p.last.close), session, "unadjusted gap, closed at last price")
            elif bar.high == bar.low:
                pass  # one price all day: locked at a circuit, assume no fill
            elif p.sell_next_open:
                sell(p, _d(bar.open) * slip_down, session, "trailing exit")
            elif _d(bar.open) <= p.stop:
                sell(p, _d(bar.open) * slip_down, session, "gapped through stop")

        # At the open: yesterday's signals, strongest momentum first.
        equity = value()
        for sig in sorted(pending, key=lambda x: -x.momentum_63d):
            bar = today.get(sig.symbol)
            if sig.symbol in positions:
                continue
            if bar is None or bar.high == bar.low:
                skip("not tradable next session")
                continue
            open_, stop = _d(bar.open), _d(sig.indicative_stop)
            if open_ > _d(sig.reference_close) * (1 + cfg.max_entry_gap) or open_ <= stop:
                skip("next open too far from signal close")
                continue
            price = (open_ * (1 + cfg.slippage)).quantize(PAISA, ROUND_HALF_UP)
            proposal = size_position(equity, cash, price, stop, cfg.limits) if cash > 0 else None
            qty = proposal.quantity if proposal else 0
            while qty and price * qty + cfg.costs.charges(price * qty, buy=True) > cash:
                qty -= 1
            if not qty:
                skip("no cash or under one share")
                continue
            cost = price * qty + cfg.costs.charges(price * qty, buy=True)
            cash -= cost
            positions[sig.symbol] = Position(sig.symbol, qty, session, price, stop, cost, bar)
        pending = []

        # During the session: stops, then mark to the close and look for tomorrow's exits/entries.
        for p in list(positions.values()):
            bar = today.get(p.symbol)
            if bar is None:
                continue
            if bar.high != bar.low and _d(bar.low) <= p.stop:
                sell(p, p.stop * slip_down, session, "stop")
                continue
            p.last = bar
            series = runs[p.symbol]
            if len(series) >= cfg.trail_sessions and bar.close < average_close(list(series), cfg.trail_sessions):
                p.sell_next_open = True
        for symbol, series in runs.items():
            # cheap pre-check (close above the prior highs) before the full scanner
            if len(series) == window and series[-1].close > max(
                    b.high for b in islice(series, window - 1 - s.breakout_sessions, window - 1)):
                if sig := scan_breakout(list(series), s):
                    pending.append(sig)

        result.curve.append((session, float(value() / units), float(value())))

    result.open_positions = list(positions.values())
    return result


def xirr(flows: list[tuple[date, float]]) -> float | None:
    """Annual money-weighted return: the rate that makes the dated flows sum to zero.

    Deposits are negative, the final value positive. Bisection; None if there is no sign change.
    """
    t0 = flows[0][0]

    def npv(rate: float) -> float:
        return sum(a / (1 + rate) ** ((d - t0).days / 365) for d, a in flows)

    lo, hi = -0.99, 10.0
    if npv(lo) * npv(hi) > 0:
        return None
    for _ in range(100):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def max_drawdown(navs: list[float]) -> float:
    peak, worst = navs[0], 0.0
    for nav in navs:
        peak = max(peak, nav)
        worst = min(worst, nav / peak - 1)
    return worst


def estimated_tax(trades: list[Trade]) -> Decimal:
    """Rough capital-gains tax: per financial year, 20% of net short-term gains (held up to a
    year) plus 12.5% of net long-term gains above ₹1.25 lakh.

    ponytail: no set-off of short-term losses against long-term gains or carry-forward.
    """
    years: dict[int, list[Decimal]] = {}
    for t in trades:
        d = date.fromisoformat(t.exit_session)
        held_long = (d - date.fromisoformat(t.entry_session)).days > 365
        fy = years.setdefault(d.year if d.month >= 4 else d.year - 1, [D(0), D(0)])
        fy[held_long] += t.pnl
    return sum((D("0.20") * max(st, D(0)) + D("0.125") * max(lt - D("125000"), D(0))
                for st, lt in years.values()), D(0)).quantize(PAISA)


def _stats(result: Result, sessions: tuple[str, str]) -> dict[str, str]:
    navs = [nav for s, nav, _ in result.curve if sessions[0] <= s <= sessions[1]]
    trades = [t for t in result.trades if sessions[0] < t.exit_session <= sessions[1]]
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]

    def pct(t: Trade) -> float:
        return float(t.pnl / (t.entry_price * t.quantity))

    return {
        "Return (time-weighted)": f"{navs[-1] / navs[0] - 1:+.1%}",
        "Max drawdown": f"{max_drawdown(navs):.1%}",
        "Closed trades": str(len(trades)),
        "Win rate": f"{len(wins) / len(trades):.0%}" if trades else "n/a",
        "Average win": f"{sum(map(pct, wins)) / len(wins):+.1%}" if wins else "n/a",
        "Average loss": f"{sum(map(pct, losses)) / len(losses):+.1%}" if losses else "n/a",
    }


def report(result: Result, index: list[Candle], index_name: str) -> str:
    """Markdown report. `index` is the benchmark's daily candles, bought with the same deposits."""
    first, last = result.curve[0][0], result.curve[-1][0]
    mid = result.curve[len(result.curve) // 2][0]
    cfg, costs = result.config, result.config.costs
    final = D(str(result.curve[-1][2])) - sum(
        (cfg.costs.charges(p.quantity * _d(p.last.close), buy=False) for p in result.open_positions), D(0))
    deposited = sum((a for _, a in result.flows), D(0))
    closes = sorted((c.session, c.close) for c in index)

    def index_close(session: str) -> float:
        return [c for s, c in closes if s <= session][-1]

    bench_units = sum(float(a) / index_close(s) for s, a in result.flows)
    bench_final = bench_units * index_close(last)
    flows = [(date.fromisoformat(s), -float(a)) for s, a in result.flows]
    end = date.fromisoformat(last)
    strategy_irr = xirr(flows + [(end, float(final))])
    bench_irr = xirr(flows + [(end, bench_final)])
    charges = sum((t.charges for t in result.trades), D(0))
    beyond = [t for t in result.trades if -t.pnl > t.planned_loss + t.charges]
    reasons: dict[str, int] = {}
    for t in result.trades:
        reasons[t.reason] = reasons.get(t.reason, 0) + 1
    halves = [_stats(result, ("", mid)), _stats(result, (mid, last))]  # a trade counts in its exit half

    def fmt(x: float | None) -> str:
        return "n/a" if x is None else f"{x:+.1%}"

    lines = [
        f"# Backtest: breakout scanner V1, {first} to {last}",
        "",
        "> Simulated research result on historical data. Not a recommendation, not a forecast, and",
        "> not evidence that the strategy will make money. Past simulated returns do not guarantee",
        "> future returns. No orders were placed.",
        "",
        "## Data and method",
        "",
        f"- **Data:** official NSE bhavcopy files, mainboard `EQ` series, every stock that traded on each day,"
        " including ones later delisted (no survivorship filter). Prices are **not** split/bonus adjusted;"
        " a stock's history restarts at any overnight gap over 25% or missing session.",
        f"- **Period:** {len(result.curve)} trading sessions after a 200-session warm-up. One market regime;"
        " too short for a real walk-forward test. Parameters were fixed in advance, not fitted to this data.",
        "- **Signals:** `strategy.scan_breakout` with default `BreakoutConfig` (20-session high, volume ≥1.5×,"
        " 63-session return ≥30%, above 50/200-session averages, ₹3 crore average turnover).",
        f"- **Entry:** next session's open + {cfg.slippage:.2%} slippage; skipped if that open is more than"
        f" {cfg.max_entry_gap:.0%} above the signal close, at or below the stop, or locked at a circuit."
        " Strongest 63-session momentum first.",
        f"- **Size:** `risk.size_position`: planned loss at the stop ≤{cfg.limits.max_loss_fraction_of_equity:.1%}"
        f" of equity, position ≤{cfg.limits.max_notional_fraction_of_equity:.0%} of equity, limited by cash.",
        f"- **Exits:** stop 7% below the signal close (filled at the stop, or at the open if the price gapped"
        f" through it, minus slippage); sell at the next open after a close below the"
        f" {cfg.trail_sessions}-session average. No fill on a day locked at a circuit.",
        f"- **Charges (Upstox delivery, 2026-11-04):** ₹{costs.brokerage_per_order} per order, STT"
        f" {costs.stt:.1%} both sides, NSE {costs.exchange * 100:.5f}%, SEBI ₹10/crore, stamp"
        f" {costs.stamp_on_buy:.3%} on buys, DP ₹{costs.dp_per_sell} per sale, GST 18% on fees.",
        f"- **Cash:** ₹{cfg.initial_cash:,} at the start, ₹{cfg.monthly_contribution:,} on the first session"
        " of each month. Existing Groww holdings are not modelled.",
        f"- **Benchmark:** {index_name} price index (Upstox), bought at the close with the same deposits."
        " No dividends and no fund costs, so it is understated by roughly the dividend yield.",
        "",
        "## Result",
        "",
        "| | Strategy | Benchmark |",
        "|---|---|---|",
        f"| Deposited | ₹{deposited:,.0f} | ₹{deposited:,.0f} |",
        f"| Final value (open positions after sell charges) | ₹{final:,.0f} | ₹{bench_final:,.0f} |",
        f"| Money-weighted return (annual) | {fmt(strategy_irr)} | {fmt(bench_irr)} |",
        f"| Return (time-weighted, whole period) | {result.curve[-1][1] / 100 - 1:+.1%} | "
        f"{index_close(last) / index_close(first) - 1:+.1%} |",
        f"| Max drawdown | {max_drawdown([n for _, n, _ in result.curve]):.1%} | "
        f"{max_drawdown([c for s, c in closes if first <= s <= last]):.1%} |",
        "",
        f"- Closed trades: {len(result.trades)}; open at the end: {len(result.open_positions)}.",
        f"- Charges paid: ₹{charges:,.0f}. Estimated capital-gains tax on closed trades (not deducted"
        f" above): ₹{estimated_tax(result.trades):,.0f}.",
        f"- Exits by reason: " + ", ".join(f"{r} {n}" for r, n in sorted(reasons.items())) + ".",
        f"- Trades that lost more than planned at the stop: {len(beyond)}.",
        f"- Signals not taken: " + (", ".join(f"{r} {n}" for r, n in sorted(result.skipped.items())) or "none") + ".",
        "",
        "## Stability: first half vs second half",
        "",
        f"| | {first} to {mid} | {mid} to {last} |",
        "|---|---|---|",
        *[f"| {k} | {halves[0][k]} | {halves[1][k]} |" for k in halves[0]],
        "",
        "## Closed trades",
        "",
        "| Symbol | Entry | Exit | Qty | Entry ₹ | Exit ₹ | P&L after charges ₹ | Reason |",
        "|---|---|---|---|---|---|---|---|",
        *[f"| {t.symbol} | {t.entry_session} | {t.exit_session} | {t.quantity} | {t.entry_price} |"
          f" {t.exit_price} | {t.pnl:,.0f} | {t.reason} |" for t in result.trades],
    ]
    if result.open_positions:
        lines += ["", "## Open at the end", "", "| Symbol | Entry | Qty | Entry ₹ | Last close ₹ | Last traded |",
                  "|---|---|---|---|---|---|",
                  *[f"| {p.symbol} | {p.entry_session} | {p.quantity} | {p.entry_price} | {p.last.close} |"
                    f" {p.last.session} |" for p in result.open_positions]]
    return "\n".join(lines) + "\n"
