import os

import requests

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM = os.getenv("RESEND_FROM", "Borderless <onboarding@resend.dev>")


def send_tracking_email(to_email: str, ticker: str, quote: dict | None) -> None:
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY is not set on the backend")

    price_line = ""
    if quote and not quote.get("error") and quote.get("price") is not None:
        chg = quote.get("change_pct_today")
        chg_text = f" ({chg:+.2f}% today)" if chg is not None else ""
        price_line = (
            f"<p style='font-size:20px;margin:4px 0 16px;'>"
            f"<strong>${quote['price']:.2f}</strong>{chg_text}</p>"
        )

    html = f"""
    <div style="font-family:-apple-system,sans-serif;max-width:480px;color:#111;">
      <p style="font-family:monospace;font-size:11px;letter-spacing:0.08em;
                text-transform:uppercase;color:#888;margin:0 0 6px;">Borderless</p>
      <h2 style="margin:0 0 12px;">You're now tracking {ticker}</h2>
      {price_line}
      <p style="color:#606060;font-size:14px;line-height:1.5;">
        We'll treat this as your watchlist signup for {ticker}. This is a one-time
        confirmation from the Borderless prototype — not personalized financial advice.
      </p>
    </div>
    """

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": RESEND_FROM,
            "to": [to_email],
            "subject": f"You're tracking {ticker} on Borderless",
            "html": html,
        },
        timeout=15,
    )
    if not resp.ok:
        raise RuntimeError(f"Resend API error {resp.status_code}: {resp.text}")
