# Architecture

## Flow
```text
NSE/Upstox historical market data (future adapter)
     ↓
Daily EOD scanner  →  strategy signals  →  risk sizing/portfolio exposure
                                              ↓
Historical replay / paper ledger ← order proposal
                                              ↓
                              narrative assistant (read-only)
                                              ↓
                                  Telegram/web report
                                              ↓
                           optional user-approved order
                                              ↓
                              future Upstox executor
                                              ↓
                                 reconciliation/audit
```

## Boundaries
- `src/gt_invest/strategy.py`: pure end-of-day indicator + breakout logic.
- `src/gt_invest/risk.py`: independently testable position-size limits.
- `src/gt_invest/models.py`: immutable input/output models.
- `src/gt_invest/bhavcopy.py`: read-only download/cache/parse of official NSE bhavcopy files; trims each stock's history at gaps it cannot trust.
- `src/gt_invest/__main__.py`: synthetic demo (`--demo`) and market-wide EOD scan (`--scan`); prints candidates only.
- Future: corporate-action adjustment, Upstox data adapter, `backtest/` event-driven portfolio simulation, `brokers/upstox/` isolated read/write adapters, `journal/` append-only audit, `reports/` LLM-friendly summaries.

## Execution safety contract
A signal is **not** an order. A proposal is **not** an order. In the future, the executor must independently re-check approved instrument, symbol-to-token mapping, available funds, lot size, max exposure, approvals, live-paper setting and current exchange state. A new approval is required if anything material changes. Broker order placement, modification and cancellation are disabled in the current version.

## Data quality and testing
- Completed daily candles only, with reproducible timezone/date handling.
- Historical constituent membership and delisted names to minimize survivorship bias.
- Splits, bonuses and dividends handled consistently, using adjusted candles or event records.
- Avoid look-ahead bias: an EOD closing signal is not assumed fillable at that closing price.
- Conservative broker fees, exchange levies, DP charges, price gaps, market impact, halts and circuit locks.
- No live trading just because a backtest looks good. Evaluate forward/paper results.
- Avoid storing personal broker data in the public repository.

## Deployment
Intended target: isolated Coolify service with scheduled jobs, encrypted secrets, separate paper/live configuration, immutable event trail, and manual approvals. Not yet deployed.

## Authentication
Credentials must live in secret management, never in GitHub. Upstox authorization, access-token expiry, API permission scopes, pricing and trading-IP requirements must be checked against current official docs during implementation.
