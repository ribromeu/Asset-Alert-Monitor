# ──────────────────────────────────────────────────────────────────
# config.py — Alert configuration
#
# WHAT IT DOES: defines all assets and alert thresholds.
# Edit ONLY this file to add/remove assets or change thresholds.
#
# ALERT TYPES:
#   price_above   : triggers when price > value (ceiling)
#   price_below   : triggers when price < value (floor)
#   pct_change    : triggers when % change in X days > abs(value)
#                   (positive = up alert, negative = down alert)
# ──────────────────────────────────────────────────────────────────

ALERTS = [
    # ── Equities ──────────────────────────────────────────────────
    {
        "ticker":      "AAPL",
        "name":        "Apple Inc.",
        "type":        "price_above",
        "value":       220.0,          # alert if price > $220
        "description": "Resistance ceiling at $220",
    },
    {
        "ticker":      "AAPL",
        "name":        "Apple Inc.",
        "type":        "price_below",
        "value":       180.0,          # alert if price < $180
        "description": "Support floor at $180",
    },
    {
        "ticker":      "SPY",
        "name":        "S&P 500 ETF",
        "type":        "pct_change",
        "value":       -5.0,           # alert if drops > 5% in window
        "window_days": 5,
        "description": "SPY down >5% in 5 days",
    },
    {
        "ticker":      "SPY",
        "name":        "S&P 500 ETF",
        "type":        "pct_change",
        "value":       5.0,            # alert if up > 5% in window
        "window_days": 5,
        "description": "SPY up >5% in 5 days",
    },
    # ── Crypto ────────────────────────────────────────────────────
    {
        "ticker":      "BTC-USD",
        "name":        "Bitcoin",
        "type":        "price_above",
        "value":       110000.0,
        "description": "BTC above $110k",
    },
    {
        "ticker":      "BTC-USD",
        "name":        "Bitcoin",
        "type":        "price_below",
        "value":       80000.0,
        "description": "BTC below $80k",
    },
    # ── Fixed income / rates ───────────────────────────────────────
    {
        "ticker":      "TLT",
        "name":        "20+ Year Treasury ETF",
        "type":        "pct_change",
        "value":       -3.0,
        "window_days": 10,
        "description": "TLT down >3% in 10 days (rates spike)",
    },
    # ── Add your own below ─────────────────────────────────────────
    # {
    #     "ticker":      "NVDA",
    #     "name":        "NVIDIA Corp.",
    #     "type":        "price_above",
    #     "value":       1000.0,
    #     "description": "NVDA above $1000",
    # },
]

# ── Benchmark tickers (used in every email for context) ────────────
BENCHMARKS = {
    "sp500":     "^GSPC",   # S&P 500
    "nasdaq":    "^IXIC",   # NASDAQ Composite
    "vix":       "^VIX",    # VIX
    "gold":      "GC=F",    # Gold futures
    "dxy":       "DX-Y.NYB",# US Dollar Index
    "us10y":     "^TNX",    # 10Y Treasury yield
    "inflation": "RINF",    # Inflation expectations ETF (proxy)
}

# ── Macro context window ───────────────────────────────────────────
MACRO_LOOKBACK_DAYS = 252   # 1 trading year for beta/alpha calc
ALPHA_BETA_WINDOW   = 252   # rolling window for regression
