"""Conservative single-position sizing, never an executable order."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN


@dataclass(frozen=True)
class RiskLimits:
    max_loss_fraction_of_equity: Decimal = Decimal("0.005")
    max_notional_fraction_of_equity: Decimal = Decimal("0.10")


@dataclass(frozen=True)
class PositionProposal:
    quantity: int
    estimated_notional_inr: Decimal
    planned_loss_at_stop_inr: Decimal
    stop_price_inr: Decimal


def size_position(
    equity_inr: Decimal,
    available_cash_inr: Decimal,
    entry_price_inr: Decimal,
    stop_price_inr: Decimal,
    limits: RiskLimits | None = None,
) -> PositionProposal | None:
    """Risk-size a whole-share proposal. No fees, gaps or liquidity guarantee.

    Guardrails for aggregate risk, existing positions and execution are separate
    mandatory work before any live trading.
    """
    l = limits or RiskLimits()
    vals = (equity_inr, available_cash_inr, entry_price_inr, stop_price_inr)
    if any(not isinstance(v, Decimal) or not v.is_finite() for v in vals):
        raise ValueError("Pass finite Decimal values for all amounts")
    if equity_inr <= 0 or available_cash_inr <= 0 or entry_price_inr <= 0:
        return None
    if stop_price_inr <= 0 or stop_price_inr >= entry_price_inr:
        return None
    if not (Decimal("0") < l.max_loss_fraction_of_equity < Decimal("1")):
        raise ValueError("Invalid loss fraction")
    if not (Decimal("0") < l.max_notional_fraction_of_equity <= Decimal("1")):
        raise ValueError("Invalid position fraction")

    unit_risk = entry_price_inr - stop_price_inr
    budget_loss = equity_inr * l.max_loss_fraction_of_equity
    budget_notional = min(available_cash_inr, equity_inr * l.max_notional_fraction_of_equity)
    by_risk = int((budget_loss / unit_risk).to_integral_value(rounding=ROUND_DOWN))
    by_notional = int((budget_notional / entry_price_inr).to_integral_value(rounding=ROUND_DOWN))
    qty = min(by_risk, by_notional)
    if qty < 1:
        return None
    return PositionProposal(
        quantity=qty,
        estimated_notional_inr=entry_price_inr * qty,
        planned_loss_at_stop_inr=unit_risk * qty,
        stop_price_inr=stop_price_inr,
    )
