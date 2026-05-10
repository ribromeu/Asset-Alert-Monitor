# Asset Alert Monitor

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![CI](https://img.shields.io/badge/%E2%9C%94%20CI-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-pytest-0A9EDC?logo=pytest&logoColor=white)
![Data](https://img.shields.io/badge/Data-Yahoo%20Finance-6001D2)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux-lightgrey)

Price and momentum alert system for any Yahoo Finance ticker. Runs on GitHub Actions, sends HTML emails with full quantitative context.

Built as a personal quant project at the intersection of portfolio monitoring, risk analysis, and software engineering.

---

## What it does

Every time it runs, the system:

1. Evaluates all alert rules defined in `config.py` against live Yahoo Finance data
2. Checks three rule types: `price_above` (ceiling), `price_below` (floor), `pct_change` over N days
3. Fetches macro context: S&P 500, NASDAQ, VIX, Gold, DXY, US 10Y yield
4. Computes per-asset risk metrics: returns (1d/5d/1m/3m/1y), annualised volatility, Sharpe ratio, max drawdown, RSI-14, 52-week high/low
5. Runs CAPM regression vs SPY (252-day OLS): Jensen's alpha, beta, R²
6. Benchmarks each asset against inflation (RINF ETF proxy), risk-free rate, and the S&P 500
7. Sends an HTML email — only when alerts fire (default), or always with `--force-send`

---

## Email preview


<img width="625" height="797" alt="Screenshot 2026-05-10 at 16 19 51" src="https://github.com/user-attachments/assets/664eb9b9-aa9a-42a5-86d8-96b844259328" />
<img width="626" height="178" alt="Screenshot 2026-05-10 at 16 20 15" src="https://github.com/user-attachments/assets/67e44413-0b2d-4acf-bf67-479d664174b6" />

---

## Email content

Every alert email contains five sections:

| Section | Metrics |
|---|---|
| **Trigger** | Which rule fired, exact trigger description |
| **Returns** | 1d, 5d, 1m, 3m, 1y |
| **Risk** | Ann. volatility, Sharpe ratio, max drawdown, RSI-14, 52W high/low |
| **CAPM** | Beta, Alpha (annualised), R² — all vs SPY (252d OLS) |
| **Macro** | SPY, NASDAQ, VIX, Gold, DXY, US 10Y yield |
| **Inflation** | Real return, excess vs risk-free, excess vs market |

The email is plain Python stdlib — no external libraries. HTML is self-contained with inline styles and renders correctly on Gmail, Outlook, and Apple Mail.

---

## Alert types

```python
# ceiling — alert when price rises above value
{"ticker": "AAPL", "type": "price_above", "value": 220.0, "description": "AAPL above $220"}

# floor — alert when price falls below value
{"ticker": "AAPL", "type": "price_below", "value": 180.0, "description": "AAPL below $180"}

# % move in N days — positive = up alert, negative = down alert
{"ticker": "SPY",  "type": "pct_change",  "value": -5.0, "window_days": 5, "description": "SPY down 5% in 5 days"}
```

All alerts live in `config.py`. No other file needs to change.

---

## Setup

**1. Fork this repo**

**2. Add GitHub Secrets**

Go to Settings → Secrets and variables → Actions → New repository secret:

| Secret | Value |
|---|---|
| `GMAIL_USER` | your Gmail address |
| `GMAIL_APP_PASS` | 16-char App Password from [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) |
| `ALERT_TO` | recipient email (comma-separated for multiple) |

**3. Edit `config.py`**

Add or remove alerts. Each entry is a dict with `ticker`, `name`, `type`, `value`, and `description`. Optionally add `window_days` for `pct_change` rules.

**4. Run**

- **Scheduled:** automatically at 21:30 UTC (16:30 ET) on market days (Mon–Fri)
- **Manual:** Actions → Asset Alert Monitor → Run workflow
  - *Force send:* tick "Send email even if no alerts triggered"
  - *Dry run:* tick "Dry run" — builds the email and uploads the HTML as a downloadable artifact, no email sent

---

## Local run

```bash
git clone https://github.com/ribromeu/Asset-Alert-Monitor
cd Asset-Alert-Monitor
pip install -r requirements.txt

# copy and fill in credentials
cp .env.example .env

# run normally (reads .env via shell export)
export $(cat .env | xargs)
python main.py

# dry run — writes HTML to /tmp/alert_preview.html
python main.py --dry-run

# force send even if no alerts triggered
python main.py --force-send
```

---

## Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## Architecture

```
config.py          — alert rules and benchmark tickers (edit here)
analytics.py       — Yahoo Finance fetch, RSI, alpha/beta, macro context
email_alert.py     — HTML email builder and SMTP sender (stdlib only)
main.py            — orchestrator
.github/
  workflows/
    main.yml       — GitHub Actions (scheduled + manual trigger)
tests/
  test_analytics.py — unit tests
```

The codebase is structured in clearly delimited blocks, each with an inline comment header explaining what it does, its dependencies, and where it feeds downstream — the same pattern used across all projects in this portfolio.

---

## Data sources

| Data | Source |
|---|---|
| Asset prices | Yahoo Finance via `yfinance` |
| Macro benchmarks | Yahoo Finance (`^GSPC`, `^IXIC`, `^VIX`, `^TNX`, `GC=F`, `DX-Y.NYB`) |
| Inflation proxy | RINF ETF (iShares TIPS Bond) via Yahoo Finance |

---

## References

- Jensen (1968) — Alpha as risk-adjusted excess return
- Sharpe (1964) — CAPM and the Sharpe ratio
- Wilder (1978) — RSI methodology

---

## Background

I built this during my BS Economics program (minors in Finance and Data Analysis) as a practical tool for tracking a personal watchlist with rigorous quantitative context. The goal was to go beyond simple price alerts — each notification carries the full risk profile of the asset (volatility, drawdown, momentum, CAPM attribution) and benchmarks it against the market, inflation, and the risk-free rate, so the signal is immediately actionable without needing to open a terminal or a spreadsheet.

---

## License

MIT
