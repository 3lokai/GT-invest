"""A deliberately simple EOD price/volume breakout hypothesis.

Not the full Qullamaggie/Minervini methods. Does not execute orders.
"""
from dataclasses import dataclass
from .models import Candle, BreakoutSignal


@dataclass(frozen=True)
class BreakoutConfig:
    breakout_sessions: int = 20
    fast_sessions: int = 50
    slow_sessions: int = 200
    momentum_sessions: int = 63
    minimum_return_63d: float = 0.30
    minimum_volume_ratio: float = 1.5
    minimum_average_turnover_inr: float = 30_000_000.0
    indicative_stop_fraction: float = 0.07


def average_close(candles: list[Candle], sessions: int) -> float:
    return sum(bar.close for bar in candles[-sessions:]) / sessions


def trend_label(candles: list[Candle], config: BreakoutConfig | None = None) -> str | None:
    """'uptrend', 'weakening' or 'downtrend' from the last close and its 50/200-session averages.

    A description of the chart, not a buy or sell recommendation. None without enough history.
    """
    c = config or BreakoutConfig()
    if len(candles) < c.slow_sessions:
        return None
    close = candles[-1].close
    fast, slow = average_close(candles, c.fast_sessions), average_close(candles, c.slow_sessions)
    if close > fast > slow:
        return "uptrend"
    if close < slow and fast < slow:
        return "downtrend"
    return "weakening"


def scan_breakout(candles: list[Candle], config: BreakoutConfig | None = None) -> BreakoutSignal | None:
    """Return an EOD candidate, or None. Caller supplies chronological daily candles.

    The reference close cannot be traded retroactively; a backtest must fill at
    a subsequent session using its own cost, liquidity and slippage model.
    """
    c = config or BreakoutConfig()
    needed = max(c.breakout_sessions, c.fast_sessions, c.slow_sessions, c.momentum_sessions)
    if len(candles) < needed + 1:
        return None
    if len({row.session for row in candles}) != len(candles):
        return None
    if any(candles[i].session >= candles[i + 1].session for i in range(len(candles) - 1)):
        return None
    if len({row.symbol for row in candles}) != 1:
        return None
    if any(
        row.close <= 0 or row.open <= 0 or row.low <= 0 or row.high <= 0
        or row.volume <= 0 or row.high < max(row.open, row.close, row.low)
        or row.low > min(row.open, row.close, row.high)
        for row in candles
    ):
        return None
    past, today = candles[:-1], candles[-1]
    recent = past[-c.breakout_sessions:]
    old_high = max(bar.high for bar in recent)
    if today.close <= old_high:
        return None
    recent_average_volume = sum(bar.volume for bar in recent) / len(recent)
    if today.volume < c.minimum_volume_ratio * recent_average_volume:
        return None
    recent_turnover = sum(bar.close * bar.volume for bar in recent) / len(recent)
    if recent_turnover < c.minimum_average_turnover_inr:
        return None
    fast_avg, slow_avg = average_close(candles, c.fast_sessions), average_close(candles, c.slow_sessions)
    if today.close <= fast_avg or today.close <= slow_avg or fast_avg <= slow_avg:
        return None
    reference_price = past[-c.momentum_sessions].close
    momentum = today.close / reference_price - 1
    if momentum < c.minimum_return_63d:
        return None
    return BreakoutSignal(
        session=today.session,
        symbol=today.symbol,
        reference_close=today.close,
        indicative_stop=round(today.close * (1 - c.indicative_stop_fraction), 2),
        prior_high=old_high,
        volume_ratio=today.volume / recent_average_volume,
        momentum_63d=momentum,
    )
