"""Immutable candle and signal records. Dates are ISO-format market-local sessions."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Candle:
    session: str
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True, slots=True)
class BreakoutSignal:
    session: str
    symbol: str
    reference_close: float
    indicative_stop: float
    prior_high: float
    volume_ratio: float
    momentum_63d: float
    note: str = "EOD signal only; not an executable order"
