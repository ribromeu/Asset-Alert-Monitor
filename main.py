# ──────────────────────────────────────────────────────────────────
# main.py — Orchestrator
#
# WHAT IT DOES: runs all alert evaluations, fetches macro context,
# builds the email, and sends it.
#
# RUN: python main.py
#      python main.py --dry-run     (prints email HTML, no send)
#      python main.py --force-send  (sends even if no alerts triggered)
# ──────────────────────────────────────────────────────────────────

import sys
import argparse
from analytics import evaluate_alert, fetch_macro_context
from email_alert import build_email_html, build_subject, send_email
from config import ALERTS


def main():
    parser = argparse.ArgumentParser(description="Asset Alert Monitor")
    parser.add_argument("--dry-run",     action="store_true",
                        help="Build email but do not send")
    parser.add_argument("--force-send",  action="store_true",
                        help="Send email even if no alerts triggered")
    args = parser.parse_args()

    print("=" * 60)
    print("Asset Alert Monitor")
    print("=" * 60)

    # ── 1. evaluate all alerts ────────────────────────────────────
    results = []
    for alert in ALERTS:
        print(f"\n▶ Checking {alert['ticker']} — {alert['description']}")
        try:
            result = evaluate_alert(alert)
            status = "🚨 TRIGGERED" if result["triggered"] else "✅ OK"
            print(f"  {status} | Price: ${result['current_price']:.2f} "
                  f"| 1d: {result['day_chg_pct']:+.2f}%")
            results.append(result)
        except Exception as e:
            print(f"  ❌ Error: {e}")

    # ── 2. fetch macro context ────────────────────────────────────
    print("\n▶ Fetching macro context...")
    try:
        macro_ctx = fetch_macro_context()
        print(f"  SPY: ${macro_ctx.get('sp500',{}).get('current',0):.2f} | "
              f"VIX: {macro_ctx.get('vix',{}).get('current',0):.1f} | "
              f"10Y: {macro_ctx.get('us10y',{}).get('current',0):.2f}%")
    except Exception as e:
        print(f"  ❌ Macro fetch error: {e}")
        macro_ctx = {}

    # ── 3. decide whether to send ─────────────────────────────────
    triggered_count = sum(1 for r in results if r["triggered"])
    print(f"\n{'='*60}")
    print(f"Alerts triggered: {triggered_count} / {len(results)} rules evaluated")

    if not results:
        print("No results to send. Exiting.")
        sys.exit(0)

    should_send = triggered_count > 0 or args.force_send

    # ── 4. build email ────────────────────────────────────────────
    html    = build_email_html(results, macro_ctx)
    subject = build_subject(results)
    print(f"Subject: {subject}")

    if args.dry_run:
        print("\n[DRY RUN] Email HTML written to /tmp/alert_preview.html")
        with open("/tmp/alert_preview.html", "w") as f:
            f.write(html)
        return

    # ── 5. send ───────────────────────────────────────────────────
    if should_send:
        print("\n▶ Sending email...")
        send_email(html, subject)
    else:
        print("\n✅ No alerts triggered. Email not sent.")
        print("   Use --force-send to send regardless.")


if __name__ == "__main__":
    main()
