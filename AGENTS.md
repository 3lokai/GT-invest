# Instructions for coding agents working on GT Invest

This is a **financial trading research system**. Optimize for reproducibility and loss containment, not speed of execution.

1. Read README.md and docs/HANDOVER.md, docs/PRODUCT.md, docs/ARCHITECTURE.md, docs/SAFETY.md, docs/STRATEGY.md before making changes.
2. Run tests and add regression tests for every signal, position-sizing or execution change.
3. Never enable live trading, transfer money, change a stop, or place/modify/cancel orders without explicit user authorization. No automatic sell recommendations are executed.
4. Only read-only broker access exists (Upstox Analytics Token for market data, Groww MCP read tools); no trading endpoint is connected. Do not claim anything is live, validated, profitable, or backtested until evidence is stored in the repository.
5. LLMs can explain and research, but cannot determine final order quantity, bypass guards, inject instrument IDs or directly call broker-trading endpoints.
6. Never commit credentials, access tokens, holdings with personal identifiers, trade confirmations, account statements or PII. Public repo: use sanitized samples.
7. Paper and live implementations must share the same deterministic trading logic; live implementation is a separately enabled adapter with per-order approval, exchange-hours checks, immutable audit log and idempotency keys.
8. Use point-in-time data, historical constituent membership, corporate-action adjustments, and conservative fill/slippage assumptions when backtesting.
9. Default universe: Indian NSE mainboard cash equity. Exclude trading suspensions, restrictive surveillance lists, insufficient-liquidity securities and SME lots unless explicitly tested.
10. For all money values and final order arithmetic use decimal.Decimal; no float rounding of executable quantities or limits.
11. Communicate in simple English. Each recommendation must include why, what could go wrong, estimated loss at stop (not guaranteed), and required approval.
12. Prefer small, reviewable PRs over opaque changes. Keep root README current.
