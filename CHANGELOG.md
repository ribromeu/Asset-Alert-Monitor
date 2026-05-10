# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0] — 2026-05-10

### Added
- Core alert engine: `price_above`, `price_below`, `pct_change` rule types
- Analytics module: returns (1d/5d/1m/3m/1y), annualised volatility, Sharpe ratio, max drawdown, RSI-14, 52W high/low
- CAPM regression vs SPY (252-day OLS): Jensen's alpha, beta, R²
- Inflation benchmarking via RINF ETF proxy
- Macro context: SPY, NASDAQ, VIX, Gold, DXY, US 10Y yield
- HTML email builder using Python stdlib only (no external libraries)
- GitHub Actions workflow: scheduled runs at 21:30 UTC (16:30 ET) on market days
- Manual trigger with `dry_run` and `force_send` inputs
- Dry run mode: saves HTML preview as downloadable artifact
- Unit tests via pytest
- `.env.example` template for local setup
