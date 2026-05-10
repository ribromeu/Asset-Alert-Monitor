# tests/test_analytics.py
# Run: pytest tests/ -v

import numpy as np
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from analytics import compute_rsi, compute_alpha_beta, inflation_comparison


def make_prices(values):
    return pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values), freq="B"))


def test_rsi_overbought():
    # strongly trending up → RSI should be high
    prices = make_prices([100 + i * 2 for i in range(30)])
    rsi = compute_rsi(prices)
    assert rsi > 60, f"Expected RSI > 60, got {rsi:.1f}"


def test_rsi_oversold():
    # strongly trending down → RSI should be low
    prices = make_prices([200 - i * 2 for i in range(30)])
    rsi = compute_rsi(prices)
    assert rsi < 40, f"Expected RSI < 40, got {rsi:.1f}"


def test_rsi_range():
    import random
    random.seed(42)
    prices = make_prices([100 + random.gauss(0, 1) for _ in range(50)])
    rsi = compute_rsi(prices)
    assert 0 <= rsi <= 100, f"RSI out of range: {rsi}"


def test_inflation_comparison_positive_real():
    macro = {
        "inflation": {"ret_21d": 0.003},    # 0.3% monthly → ~3.6% annual
        "us10y":     {"current": 4.5},
        "sp500":     {"ret_21d": 0.08},
    }
    result = inflation_comparison(0.15, macro)   # 15% 1Y return
    assert result["real_return"] > 0, "Expected positive real return"


def test_inflation_comparison_negative_excess():
    macro = {
        "inflation": {"ret_21d": 0.001},
        "us10y":     {"current": 4.5},
        "sp500":     {"ret_21d": 0.20},     # market returned 20%
    }
    result = inflation_comparison(0.05, macro)   # asset returned 5%
    assert result["excess_vs_market"] < 0, "Expected negative alpha vs market"


def test_alert_price_above():
    from analytics import evaluate_alert
    # use SPY which always has data; set ceiling very high → not triggered
    alert = {
        "ticker": "SPY", "name": "SPY", "type": "price_above",
        "value": 9999.0, "description": "test"
    }
    result = evaluate_alert(alert)
    assert result["triggered"] is False


def test_alert_price_below():
    from analytics import evaluate_alert
    # set floor very low → not triggered
    alert = {
        "ticker": "SPY", "name": "SPY", "type": "price_below",
        "value": 0.01, "description": "test"
    }
    result = evaluate_alert(alert)
    assert result["triggered"] is False
