# Asset Alert Monitor

Price and momentum alert system for any Yahoo Finance ticker. Runs on GitHub Actions, sends HTML emails with full quantitative context.

---

## What it does

Every run:

1. Evaluates all alert rules in `config.py` against live Yahoo Finance data
2. Checks: `price_above` (ceiling), `price_below` (floor), `pct_change` in N days (min/max over time window)
3. Fetches S&P 500, NASDAQ, VIX, Gold, DXY, US 10Y yield for macro context
4. Computes per-asset: returns (1d/5d/1m/3m/1y), annualised volatility, Sharpe ratio, max drawdown, RSI-14, 52W high/low, Jensen's alpha and beta vs SPY (252d OLS regression)
5. Compares asset vs inflation (RINF ETF proxy), risk-free rate, and S&P 500
6. Sends an HTML email — only when alerts fire (default), or always with `--force-send`

---

## Email content

| Section | Metrics |
|---|---|
| Trigger | Which rule fired, exact trigger description |
| Returns | 1d, 5d, 1m, 3m, 1y |
| Risk | Ann. vol, Sharpe, max drawdown, RSI-14, 52W high/low |
| CAPM | Beta, Alpha (annualised), R² — all vs SPY |
| Macro | SPY, NASDAQ, VIX, Gold, DXY, US 10Y |
| Inflation | Real return, excess vs risk-free, excess vs market |

---

## Alert types

```python
# ceiling — alert when price > value
{"ticker": "AAPL", "type": "price_above", "value": 220.0, ...}

# floor — alert when price < value
{"ticker": "AAPL", "type": "price_below", "value": 180.0, ...}

# % move in N days — positive = up alert, negative = down alert
{"ticker": "SPY",  "type": "pct_change",  "value": -5.0, "window_days": 5, ...}
```

All alerts live in `config.py`. No other file needs to change.

---

## Setup

### 1. Fork this repo

### 2. Add GitHub Secrets

`Settings → Secrets and variables → Actions → New repository secret`

| Secret | Value |
|---|---|
| `GMAIL_USER` | your Gmail address |
| `GMAIL_APP_PASS` | 16-char [App Password](https://myaccount.google.com/apppasswords) |
| `ALERT_TO` | recipient email (comma-separated for multiple) |

### 3. Edit `config.py`

Add or remove alerts. Each entry is a dict with `ticker`, `name`, `type`, `value`, and `description`.

### 4. Run

- **Scheduled**: automatically at 16:30 UTC (12:30 PM ET) on market days
- **Manual**: `Actions → Asset Alert Monitor → Run workflow`
- **Force send**: tick "Send email even if no alerts triggered" on manual run
- **Dry run**: tick "Dry run" — builds the email and uploads HTML as an artifact, no send

---

## Local run

```bash
git clone https://github.com/YOUR_USER/asset-alert-monitor
cd asset-alert-monitor
pip install -r requirements.txt

# copy and fill credentials
cp .env.example .env

# run (reads .env automatically via shell export or python-dotenv)
export $(cat .env | xargs)
python main.py

# dry run — writes /tmp/alert_preview.html
python main.py --dry-run

# force send even with no alerts
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
    asset_alert.yml — GitHub Actions (scheduled + manual)
tests/
  test_analytics.py — unit tests
```

---

## Data sources

| Data | Source |
|---|---|
| Asset prices | Yahoo Finance via yfinance |
| Macro benchmarks | Yahoo Finance (^GSPC, ^VIX, ^TNX, GC=F, DX-Y.NYB) |
| Inflation proxy | RINF ETF (iShares TIPS Bond) via Yahoo Finance |

---

## References

- Jensen (1968) — Alpha as risk-adjusted excess return
- Sharpe (1964) — CAPM and the Sharpe ratio
- Wilder (1978) — RSI methodology

---

## License

MIT
