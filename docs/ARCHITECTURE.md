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
- `src/gt_invest/upstox.py`: default data source; read-only download/cache/parse of Upstox split/bonus-adjusted daily candles, rate-limited.
- `src/gt_invest/bhavcopy.py`: `--source nse` fallback from official NSE bhavcopy files; `histories()` trims each stock's history at gaps it cannot trust, for both sources.
- `src/gt_invest/__main__.py`: synthetic demo (`--demo`) and market-wide EOD scan (`--scan`); prints candidates only.
- Future: point-in-time instrument lists and delisted names, `backtest/` event-driven portfolio simulation, `brokers/upstox/` isolated read/write adapters, `journal/` append-only audit, `reports/` LLM-friendly summaries.

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
Credentials must live in secret management (locally: git-ignored `.env`), never in GitHub. Verified against official docs on 2026-11-03:

| Need | Access | Notes |
|---|---|---|
| Market data (candles, quotes, instruments) | **Upstox Analytics Token** (`UPSTOX_ANALYTICS_TOKEN`) | Read-only, valid 1 year, free, no OAuth redirect, no static IP for market-data APIs. Cannot place orders. Daily candles are split/bonus adjusted (checked on JSWDULUX and BANSALWIRE). |
| Existing portfolio (Groww) | **Groww official MCP** (`https://mcp.groww.in/mcp`), used interactively by Claude Code | Read tools are allow-listed in `.claude/settings.json`; likely order-tool names are denied. Holdings data stays out of the repo. |
| Live orders (M5 only) | Upstox OAuth app (API key/secret, redirect URI) + **registered static IP** | Exchange rules since 2026-04-01: static IP for order APIs, ≤10 orders/sec without algo registration, no plain market orders (market price protection applies). Not implemented. |

Not used: Upstox MCP (read-only, but the portfolio is in Groww and the token covers data), Upstox `upstox-skill` plugin (places live orders, forbidden), Groww Trade API (₹499/month; MCP covers read needs).
