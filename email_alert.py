# ──────────────────────────────────────────────────────────────────
# email_alert.py — HTML email builder and sender
#
# WHAT IT DOES: builds a rich HTML email with triggered alerts,
# per-asset metrics table, macro context, and inflation comparison.
# Uses Python stdlib only (smtplib + email) — no external deps.
#
# DEPENDENCIES: analytics.py, config.py
# CALLED BY: main.py
# ──────────────────────────────────────────────────────────────────

import smtplib
import ssl
import os
import numpy as np
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# ── BLOCK 1 — Formatting helpers ───────────────────────────────────

def _fmt(value, fmt=".2f", suffix="", prefix="") -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    return f"{prefix}{value:{fmt}}{suffix}"


def _pct(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    sign = "+" if value > 0 else ""
    color = "#16a34a" if value > 0 else "#dc2626"
    return f'<span style="color:{color};font-weight:600">{sign}{value:.2f}%</span>'


def _neutral(value, fmt=".2f", suffix="") -> str:
    return _fmt(value, fmt=fmt, suffix=suffix)


def _color_rsi(rsi) -> str:
    if rsi is None or (isinstance(rsi, float) and np.isnan(rsi)):
        return "N/A"
    if rsi >= 70:
        color, label = "#dc2626", f"Overbought ({rsi:.1f})"
    elif rsi <= 30:
        color, label = "#2563eb", f"Oversold ({rsi:.1f})"
    else:
        color, label = "#374151", f"{rsi:.1f}"
    return f'<span style="color:{color}">{label}</span>'


def _color_beta(beta) -> str:
    if beta is None or (isinstance(beta, float) and np.isnan(beta)):
        return "N/A"
    if beta > 1.5:
        color = "#dc2626"
    elif beta > 1.0:
        color = "#d97706"
    elif beta < 0:
        color = "#7c3aed"
    else:
        color = "#374151"
    return f'<span style="color:{color}">{beta:.2f}</span>'


# ── BLOCK 2 — Asset section builder ────────────────────────────────

def _build_asset_section(result: dict, macro_ctx: dict, infl: dict) -> str:
    m  = result["metrics"]
    t  = result["ticker"]
    n  = result["name"]
    cp = result["current_price"]

    triggered_banner = ""
    if result["triggered"]:
        triggered_banner = f"""
        <div style="background:#fef2f2;border-left:4px solid #dc2626;
                    padding:12px 16px;margin-bottom:16px;border-radius:4px">
          <strong style="color:#dc2626">🚨 ALERT TRIGGERED</strong>
          <div style="margin-top:4px;color:#374151">{result['trigger_desc']}</div>
          <div style="color:#6b7280;font-size:13px;margin-top:2px">{result['description']}</div>
        </div>"""

    # ── returns table ──────────────────────────────────────────────
    returns_rows = f"""
        <tr><td>1 Day</td><td>{_pct(result['day_chg_pct'])}</td></tr>
        <tr><td>5 Days</td><td>{_pct(m['ret_5d']*100 if not np.isnan(m['ret_5d'] or 0) else np.nan)}</td></tr>
        <tr><td>1 Month (21d)</td><td>{_pct(m['ret_21d']*100 if not np.isnan(m['ret_21d'] or 0) else np.nan)}</td></tr>
        <tr><td>3 Months (63d)</td><td>{_pct(m['ret_63d']*100 if not np.isnan(m['ret_63d'] or 0) else np.nan)}</td></tr>
        <tr><td>1 Year (252d)</td><td>{_pct(m['ret_252d']*100 if not np.isnan(m['ret_252d'] or 0) else np.nan)}</td></tr>
    """

    # safe pct helpers that handle None and nan
    def safe_pct(v):
        try:
            return _pct(float(v) * 100)
        except Exception:
            return "N/A"

    # ── risk / quant table ─────────────────────────────────────────
    risk_rows = f"""
        <tr><td>Ann. Volatility</td><td>{_neutral(m['vol_ann']*100 if not np.isnan(m.get('vol_ann',np.nan)) else np.nan, suffix='%')}</td></tr>
        <tr><td>Sharpe Ratio</td><td>{_neutral(m['sharpe'])}</td></tr>
        <tr><td>Max Drawdown</td><td>{_pct(m['max_drawdown']*100 if not np.isnan(m.get('max_drawdown',np.nan)) else np.nan)}</td></tr>
        <tr><td>RSI (14)</td><td>{_color_rsi(m['rsi_14'])}</td></tr>
        <tr><td>52W High</td><td>{_fmt(m['high_52w'], prefix='$')} ({_fmt(m['pct_from_high'], suffix='%')} from here)</td></tr>
        <tr><td>52W Low</td><td>{_fmt(m['low_52w'], prefix='$')} (+{_fmt(m['pct_from_low'], suffix='%')} from here)</td></tr>
    """

    # ── alpha / beta ───────────────────────────────────────────────
    capm_rows = f"""
        <tr><td>Beta (vs SPY)</td><td>{_color_beta(m['beta'])}</td></tr>
        <tr><td>Alpha (annualised)</td><td>{_pct(m['alpha']*100 if not np.isnan(m.get('alpha',np.nan)) else np.nan)}</td></tr>
        <tr><td>R² (vs SPY)</td><td>{_neutral(m['r_squared'])}</td></tr>
    """

    # ── macro comparison ───────────────────────────────────────────
    def mc(label):
        d = macro_ctx.get(label, {})
        cur = d.get("current", np.nan)
        r1  = d.get("ret_1d", np.nan)
        return f"{_fmt(cur)} ({_pct(r1)})"

    macro_rows = f"""
        <tr><td>S&P 500</td><td>{mc('sp500')}</td></tr>
        <tr><td>NASDAQ</td><td>{mc('nasdaq')}</td></tr>
        <tr><td>VIX</td><td>{mc('vix')}</td></tr>
        <tr><td>Gold</td><td>{mc('gold')}</td></tr>
        <tr><td>DXY</td><td>{mc('dxy')}</td></tr>
        <tr><td>US 10Y Yield</td><td>{_fmt(macro_ctx.get('us10y',{}).get('current',np.nan), suffix='%')}</td></tr>
    """

    # ── inflation comparison ───────────────────────────────────────
    ret_1y = m.get("ret_252d", np.nan)
    infl_rows = f"""
        <tr><td>Asset 1Y Return</td><td>{_pct(ret_1y*100 if not np.isnan(ret_1y or 0) else np.nan)}</td></tr>
        <tr><td>Infl. Proxy (1m ann.)</td><td>{_fmt(infl.get('infl_proxy_1m',np.nan), suffix='%')}</td></tr>
        <tr><td>Real Return (est.)</td><td>{_pct(infl.get('real_return',np.nan))}</td></tr>
        <tr><td>Excess vs Risk-Free</td><td>{_pct(infl.get('excess_vs_rf',np.nan))}</td></tr>
        <tr><td>Excess vs S&P 500</td><td>{_pct(infl.get('excess_vs_market',np.nan))}</td></tr>
    """

    table_style = """
        width:100%;border-collapse:collapse;font-size:14px;margin-bottom:8px
    """
    row_style = "padding:6px 10px;border-bottom:1px solid #f3f4f6"
    head_style = "background:#f9fafb;color:#6b7280;font-size:12px;text-transform:uppercase;letter-spacing:.05em"

    def make_table(header, rows):
        return f"""
        <table style="{table_style}">
          <thead>
            <tr>
              <th style="{head_style};{row_style};text-align:left" colspan="2">{header}</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>"""

    return f"""
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;
                padding:20px;margin-bottom:24px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;
                  margin-bottom:16px">
        <div>
          <h2 style="margin:0;font-size:20px;color:#111827">{n}</h2>
          <span style="color:#6b7280;font-size:14px">{t}</span>
        </div>
        <div style="text-align:right">
          <div style="font-size:26px;font-weight:700;color:#111827">${cp:,.2f}</div>
          <div>{_pct(result['day_chg_pct'])} today</div>
        </div>
      </div>
      {triggered_banner}
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div>
          {make_table("Returns", returns_rows)}
          {make_table("Inflation & Macro", infl_rows)}
        </div>
        <div>
          {make_table("Risk Metrics", risk_rows)}
          {make_table("CAPM (vs SPY, 1Y)", capm_rows)}
        </div>
      </div>
      {make_table("Market Context (today)", macro_rows)}
    </div>"""


# ── BLOCK 3 — Full email builder ────────────────────────────────────

def build_email_html(results: list, macro_ctx: dict) -> str:
    """Build the full HTML email from a list of evaluated alert results."""
    from analytics import inflation_comparison

    now = datetime.now().strftime("%B %d, %Y — %H:%M UTC")
    triggered_count = sum(1 for r in results if r["triggered"])

    subject_line_color = "#dc2626" if triggered_count > 0 else "#1d4ed8"
    subject_text = (
        f"🚨 {triggered_count} ALERT{'S' if triggered_count != 1 else ''} TRIGGERED"
        if triggered_count > 0 else "✅ Daily Asset Monitor — No Alerts"
    )

    asset_sections = []
    seen = set()
    for r in results:
        key = r["ticker"]
        infl = inflation_comparison(r["metrics"].get("ret_252d", np.nan) or np.nan, macro_ctx)
        section = _build_asset_section(r, macro_ctx, infl)
        asset_sections.append(section)

    # dedupe triggered alerts summary at top
    triggered_summary = ""
    if triggered_count > 0:
        items = "".join(
            f"<li style='margin:4px 0'><strong>{r['name']} ({r['ticker']})</strong>: "
            f"{r['trigger_desc']}</li>"
            for r in results if r["triggered"]
        )
        triggered_summary = f"""
        <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;
                    padding:16px;margin-bottom:24px">
          <h3 style="margin:0 0 8px;color:#dc2626">🚨 Triggered Alerts</h3>
          <ul style="margin:0;padding-left:20px;color:#374151">{items}</ul>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,
             BlinkMacSystemFont,'Segoe UI',sans-serif">
  <div style="max-width:760px;margin:0 auto;padding:24px">

    <!-- header -->
    <div style="background:{subject_line_color};border-radius:8px;
                padding:20px 24px;margin-bottom:24px">
      <h1 style="margin:0;color:#fff;font-size:22px">{subject_text}</h1>
      <div style="color:rgba(255,255,255,.75);font-size:13px;margin-top:4px">{now}</div>
    </div>

    {triggered_summary}

    <!-- asset cards -->
    {"".join(asset_sections)}

    <!-- footer -->
    <div style="text-align:center;color:#9ca3af;font-size:12px;padding:16px 0">
      Data via Yahoo Finance · Alpha/Beta vs SPY (252d OLS) ·
      Real return uses RINF ETF as inflation proxy ·
      Not investment advice
    </div>
  </div>
</body>
</html>"""


# ── BLOCK 4 — SMTP sender ──────────────────────────────────────────

def send_email(html_body: str, subject: str):
    """
    Send HTML email via Gmail SMTP.
    Reads credentials from environment variables (GitHub Secrets).

    Required env vars:
      GMAIL_USER      — sender address
      GMAIL_APP_PASS  — Gmail App Password (not your login password)
      ALERT_TO        — recipient address (comma-separated for multiple)
    """
    sender    = os.environ["GMAIL_USER"]
    password  = os.environ["GMAIL_APP_PASS"]
    recipient = os.environ["ALERT_TO"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Asset Alert Monitor <{sender}>"
    msg["To"]      = recipient

    msg.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient.split(","), msg.as_string())

    print(f"✅ Email sent to {recipient}")


def build_subject(results: list) -> str:
    triggered = [r for r in results if r["triggered"]]
    if not triggered:
        return "✅ Asset Monitor — No Alerts Triggered"
    names = ", ".join(f"{r['ticker']}" for r in triggered[:3])
    suffix = f" +{len(triggered)-3} more" if len(triggered) > 3 else ""
    return f"🚨 ALERT: {names}{suffix} — Asset Monitor"
