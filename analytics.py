# ──────────────────────────────────────────────────────────────────
# analytics.py — Data fetching and metric computation
#
# WHAT IT DOES: pulls Yahoo Finance data, checks alert thresholds,
# computes alpha/beta vs S&P 500, RSI, Sharpe, drawdown, and
# macro comparison metrics.
#
# DEPENDENCIES: yfinance, numpy, pandas, scipy
# USED IN: main.py, email_alert.py
# ──────────────────────────────────────────────────────────────────

import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from scipy import stats
from config import BENCHMARKS, MACRO_LOOKBACK_DAYS, ALPHA_BETA_WINDOW


# ── BLOCK 1 — Raw price fetch ──────────────────────────────────────

def fetch_prices(ticker: str, days: int = MACRO_LOOKBACK_DAYS + 30) -> pd.Series:
    """Download adjusted close prices for a given ticker."""
    end   = datetime.today()
    start = end - timedelta(days=days)
    try:
        df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        if df.empty:
            raise ValueError(f"No data returned for {ticker}")
        col = "Close"
        series = df[col].squeeze()
        return series.dropna()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch {ticker}: {e}")


def fetch_current_price(ticker: str) -> float:
    """Return the most recent closing price."""
    prices = fetch_prices(ticker, days=7)
    return float(prices.iloc[-1])


# ── BLOCK 2 — Alert evaluation ─────────────────────────────────────

def evaluate_alert(alert: dict) -> dict:
    """
    Evaluate a single alert rule against current market data.
    Returns a result dict with triggered flag, current metrics, and context.
    """
    ticker  = alert["ticker"]
    atype   = alert["type"]
    value   = alert["value"]
    window  = alert.get("window_days", 1)

    # fetch enough history for pct_change window + macro lookback
    lookback = max(window + 5, MACRO_LOOKBACK_DAYS + 30)
    prices   = fetch_prices(ticker, days=lookback)

    current_price = float(prices.iloc[-1])
    prev_price    = float(prices.iloc[-2]) if len(prices) > 1 else current_price

    # ── trigger logic ──────────────────────────────────────────────
    triggered = False
    trigger_desc = ""

    if atype == "price_above":
        triggered    = current_price > value
        trigger_desc = f"Price ${current_price:.2f} crossed above ceiling ${value:.2f}"

    elif atype == "price_below":
        triggered    = current_price < value
        trigger_desc = f"Price ${current_price:.2f} crossed below floor ${value:.2f}"

    elif atype == "pct_change":
        # look back `window` trading days
        if len(prices) >= window + 1:
            ref_price = float(prices.iloc[-(window + 1)])
        else:
            ref_price = float(prices.iloc[0])

        pct = (current_price - ref_price) / ref_price * 100

        if value > 0:
            triggered    = pct > value
            trigger_desc = f"+{pct:.2f}% in {window} days (threshold: +{value:.2f}%)"
        else:
            triggered    = pct < value
            trigger_desc = f"{pct:.2f}% in {window} days (threshold: {value:.2f}%)"
    else:
        raise ValueError(f"Unknown alert type: {atype}")

    # ── compute per-asset metrics ──────────────────────────────────
    metrics = compute_asset_metrics(ticker, prices)

    return {
        "ticker":       ticker,
        "name":         alert["name"],
        "type":         atype,
        "threshold":    value,
        "window_days":  window,
        "description":  alert["description"],
        "triggered":    triggered,
        "trigger_desc": trigger_desc,
        "current_price": current_price,
        "prev_close":   prev_price,
        "day_chg_pct":  (current_price - prev_price) / prev_price * 100,
        "metrics":      metrics,
    }


# ── BLOCK 3 — Asset metrics ────────────────────────────────────────

def compute_asset_metrics(ticker: str, prices: pd.Series) -> dict:
    """
    Compute: returns, volatility, Sharpe, max drawdown,
    RSI-14, alpha, beta vs S&P 500.
    """
    rets = prices.pct_change().dropna()

    # ── basic stats ────────────────────────────────────────────────
    ret_1d   = float(rets.iloc[-1])               if len(rets) >= 1   else np.nan
    ret_5d   = float(prices.iloc[-1] / prices.iloc[-6] - 1)  if len(prices) >= 7  else np.nan
    ret_21d  = float(prices.iloc[-1] / prices.iloc[-22] - 1) if len(prices) >= 23 else np.nan
    ret_63d  = float(prices.iloc[-1] / prices.iloc[-64] - 1) if len(prices) >= 65 else np.nan
    ret_252d = float(prices.iloc[-1] / prices.iloc[-253] - 1) if len(prices) >= 254 else np.nan

    # annualised vol
    vol_ann = float(rets.std() * np.sqrt(252)) if len(rets) >= 20 else np.nan

    # Sharpe (risk-free ≈ 5.25% annualised, May 2026 estimate)
    rf_daily = 0.0525 / 252
    sharpe   = float((rets.mean() - rf_daily) / rets.std() * np.sqrt(252)) if len(rets) >= 20 else np.nan

    # max drawdown (rolling peak)
    rolling_max  = prices.cummax()
    drawdown     = (prices - rolling_max) / rolling_max
    max_drawdown = float(drawdown.min())

    # RSI-14
    rsi = compute_rsi(prices, period=14)

    # ── alpha / beta vs SPY ────────────────────────────────────────
    alpha, beta, r_squared = compute_alpha_beta(ticker, prices)

    # ── 52-week high / low ─────────────────────────────────────────
    w52 = prices.tail(252)
    high_52w = float(w52.max())
    low_52w  = float(w52.min())
    current  = float(prices.iloc[-1])
    pct_from_high = (current - high_52w) / high_52w * 100
    pct_from_low  = (current - low_52w)  / low_52w  * 100

    return {
        "ret_1d":        ret_1d,
        "ret_5d":        ret_5d,
        "ret_21d":       ret_21d,
        "ret_63d":       ret_63d,
        "ret_252d":      ret_252d,
        "vol_ann":       vol_ann,
        "sharpe":        sharpe,
        "max_drawdown":  max_drawdown,
        "rsi_14":        rsi,
        "alpha":         alpha,
        "beta":          beta,
        "r_squared":     r_squared,
        "high_52w":      high_52w,
        "low_52w":       low_52w,
        "pct_from_high": pct_from_high,
        "pct_from_low":  pct_from_low,
    }


def compute_rsi(prices: pd.Series, period: int = 14) -> float:
    """Standard Wilder RSI."""
    delta = prices.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    # when avg_loss = 0, RSI = 100 (perfect uptrend)
    rs  = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    # fill RSI = 100 where avg_loss was 0 and avg_gain > 0
    rsi = rsi.fillna(100)
    return float(rsi.iloc[-1]) if not rsi.empty else np.nan


def compute_alpha_beta(ticker: str, asset_prices: pd.Series) -> tuple:
    """
    OLS regression of asset excess returns on SPY excess returns.
    Returns (alpha_annualised, beta, r_squared).
    Alpha is Jensen's alpha: annualised intercept of CAPM regression.
    """
    try:
        spy_prices = fetch_prices("SPY", days=ALPHA_BETA_WINDOW + 30)

        # align on common dates
        asset_rets = asset_prices.pct_change().dropna()
        spy_rets   = spy_prices.pct_change().dropna()
        common     = asset_rets.index.intersection(spy_rets.index)

        if len(common) < 60:
            return (np.nan, np.nan, np.nan)

        y = asset_rets.loc[common].values
        x = spy_rets.loc[common].values

        slope, intercept, r_value, _, _ = stats.linregress(x, y)

        beta      = float(slope)
        alpha_ann = float(intercept * 252)   # annualise daily alpha
        r_sq      = float(r_value ** 2)

        return (alpha_ann, beta, r_sq)

    except Exception:
        return (np.nan, np.nan, np.nan)


# ── BLOCK 4 — Macro context ────────────────────────────────────────

def fetch_macro_context() -> dict:
    """
    Fetch benchmark data for macro comparison table in the email.
    Returns current level + 1d/5d/21d change for each benchmark.
    """
    context = {}
    for label, ticker in BENCHMARKS.items():
        try:
            prices = fetch_prices(ticker, days=35)
            cur    = float(prices.iloc[-1])
            prev   = float(prices.iloc[-2]) if len(prices) > 1 else cur

            ret_1d  = (cur - prev) / prev * 100
            ret_5d  = (cur / float(prices.iloc[-6]) - 1) * 100  if len(prices) >= 7  else np.nan
            ret_21d = (cur / float(prices.iloc[-22]) - 1) * 100 if len(prices) >= 23 else np.nan

            context[label] = {
                "ticker":  ticker,
                "current": cur,
                "ret_1d":  ret_1d,
                "ret_5d":  ret_5d,
                "ret_21d": ret_21d,
            }
        except Exception:
            context[label] = {"ticker": ticker, "current": np.nan,
                               "ret_1d": np.nan, "ret_5d": np.nan, "ret_21d": np.nan}

    return context


# ── BLOCK 5 — Inflation comparison ────────────────────────────────

def inflation_comparison(asset_ret_1y: float, macro_ctx: dict) -> dict:
    """
    Compare 1-year asset return against:
      - Inflation proxy (RINF ETF 1y return)
      - 10Y Treasury yield (risk-free benchmark)
      - S&P 500 1y return
    Returns real return and excess returns.
    """
    infl_ret = macro_ctx.get("inflation", {}).get("ret_21d", np.nan)  # 1m proxy
    sp500_1y = macro_ctx.get("sp500", {}).get("ret_21d", np.nan)
    us10y    = macro_ctx.get("us10y",  {}).get("current", np.nan)      # annualised yield %

    real_return         = asset_ret_1y - (infl_ret * 12 if not np.isnan(infl_ret) else np.nan)
    excess_vs_rf        = asset_ret_1y * 100 - (us10y if not np.isnan(us10y) else np.nan)
    excess_vs_market    = asset_ret_1y * 100 - (sp500_1y if not np.isnan(sp500_1y) else np.nan)

    return {
        "real_return":      real_return,
        "excess_vs_rf":     excess_vs_rf,
        "excess_vs_market": excess_vs_market,
        "infl_proxy_1m":    infl_ret,
        "us10y_yield":      us10y,
        "sp500_1y_pct":     sp500_1y,
    }
