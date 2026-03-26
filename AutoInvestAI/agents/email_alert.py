# ============================================================
#  agents/email_alert.py
#  Professional Email Alert System for AutoInvest AI
#  Developer: A. SHANMUGANAADHAN
#  
#  Sends rich HTML + plain-text alerts via SMTP (Gmail/Outlook/etc.)
# ============================================================

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email              import encoders
import io
import time


# ─────────────────────────────────────────────────────────────
#  HTML EMAIL TEMPLATE
# ─────────────────────────────────────────────────────────────

def _build_html(
    stock_name: str,
    stock_ticker: str,
    price: float,
    change_pct: float,
    trend: str,
    rsi: float,
    decision: str,
    conf: int,
    explanation: str,
    risk: str,
    portfolio_summary: str = "",
    developer: str = "A. SHANMUGANAADHAN",
) -> str:

    dec_key = "BUY" if "BUY" in decision else ("SELL" if "SELL" in decision else "HOLD")
    colors  = {
        "BUY":  {"bg": "#064e3b", "border": "#10b981", "badge": "#10b981", "text": "#34d399"},
        "SELL": {"bg": "#450a0a", "border": "#ef4444", "badge": "#ef4444", "text": "#f87171"},
        "HOLD": {"bg": "#1c1917", "border": "#f59e0b", "badge": "#f59e0b", "text": "#fbbf24"},
    }
    c = colors.get(dec_key, colors["HOLD"])
    chg_color = "#10b981" if change_pct >= 0 else "#ef4444"
    chg_sym   = "▲" if change_pct >= 0 else "▼"
    timestamp = time.strftime("%d %B %Y  %H:%M IST")

    portfolio_section = ""
    if portfolio_summary:
        portfolio_section = f"""
        <div style="margin-top:24px;padding:18px 24px;background:#111827;border-radius:12px;
                    border:1px solid #1e293b;">
            <p style="margin:0 0 10px;font-size:13px;color:#00c6ff;font-weight:700;
                      letter-spacing:1px;text-transform:uppercase;">
                📋 Your Portfolio Context
            </p>
            <p style="margin:0;font-size:14px;color:#94a3b8;line-height:1.7;">
                {portfolio_summary}
            </p>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>AutoInvest AI Alert — {stock_name}</title>
</head>
<body style="margin:0;padding:0;background:#0a0e1a;font-family:'Segoe UI',Helvetica,Arial,sans-serif;">

<!-- Wrapper -->
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0e1a;padding:32px 0;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0"
       style="max-width:620px;width:100%;border-radius:20px;overflow:hidden;
              border:1px solid #1e293b;background:#0d1117;">

  <!-- TOP BAR -->
  <tr>
    <td style="background:linear-gradient(135deg,#0072ff,#7c3aed);
               padding:4px 0;text-align:center;font-size:11px;color:#fff;
               letter-spacing:3px;font-weight:700;text-transform:uppercase;">
      ⚡ AutoInvest AI · Market Intelligence Signal
    </td>
  </tr>

  <!-- HEADER -->
  <tr>
    <td style="padding:28px 32px 20px;background:#0d1117;">
      <table width="100%">
        <tr>
          <td>
            <p style="margin:0;font-size:11px;color:#475569;letter-spacing:2px;
                      text-transform:uppercase;">AI Market Alert</p>
            <h1 style="margin:6px 0 0;font-size:28px;font-weight:800;
                       color:#e2e8f0;letter-spacing:-0.5px;">
              📊 {stock_name}
              <span style="font-size:14px;color:#475569;font-weight:400;">
                &nbsp;({stock_ticker.replace('.NS','')})
              </span>
            </h1>
          </td>
          <td align="right" valign="top">
            <p style="margin:0;font-size:11px;color:#475569;">{timestamp}</p>
            <p style="margin:4px 0 0;font-size:13px;color:#64748b;">NSE India</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- PRICE ROW -->
  <tr>
    <td style="padding:0 32px 24px;">
      <table width="100%" style="background:#111827;border-radius:14px;
                                  border:1px solid #1e293b;overflow:hidden;">
        <tr>
          <td style="padding:20px 24px;border-right:1px solid #1e293b;">
            <p style="margin:0;font-size:11px;color:#475569;text-transform:uppercase;
                      letter-spacing:1px;">Current Price</p>
            <p style="margin:6px 0 0;font-size:32px;font-weight:800;color:#e2e8f0;
                      font-family:'Courier New',monospace;">
              ₹{price:,.2f}
            </p>
          </td>
          <td style="padding:20px 24px;border-right:1px solid #1e293b;">
            <p style="margin:0;font-size:11px;color:#475569;text-transform:uppercase;
                      letter-spacing:1px;">Change Today</p>
            <p style="margin:6px 0 0;font-size:24px;font-weight:700;color:{chg_color};">
              {chg_sym} {abs(change_pct):.2f}%
            </p>
          </td>
          <td style="padding:20px 24px;border-right:1px solid #1e293b;">
            <p style="margin:0;font-size:11px;color:#475569;text-transform:uppercase;
                      letter-spacing:1px;">Trend</p>
            <p style="margin:6px 0 0;font-size:20px;font-weight:700;color:#7dd3fc;">
              {trend}
            </p>
          </td>
          <td style="padding:20px 24px;">
            <p style="margin:0;font-size:11px;color:#475569;text-transform:uppercase;
                      letter-spacing:1px;">RSI</p>
            <p style="margin:6px 0 0;font-size:24px;font-weight:700;
                      color:{'#ef4444' if rsi>70 else '#10b981' if rsi<30 else '#f97316'};">
              {rsi:.1f}
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- DECISION BADGE -->
  <tr>
    <td style="padding:0 32px 24px;">
      <div style="background:{c['bg']};border:2px solid {c['border']};
                  border-radius:16px;padding:24px 28px;">
        <table width="100%">
          <tr>
            <td>
              <p style="margin:0;font-size:12px;color:{c['text']};letter-spacing:2px;
                        text-transform:uppercase;font-weight:600;">AI Decision</p>
              <p style="margin:8px 0 0;font-size:42px;font-weight:900;
                        color:{c['badge']};letter-spacing:1px;">
                {decision}
              </p>
            </td>
            <td align="right" valign="middle">
              <div style="background:rgba(0,0,0,0.3);border-radius:50%;
                          width:80px;height:80px;display:inline-block;
                          text-align:center;line-height:80px;
                          border:2px solid {c['border']};">
                <span style="font-size:28px;font-weight:900;color:{c['badge']};">
                  {conf}%
                </span>
              </div>
              <p style="margin:6px 0 0;font-size:11px;color:{c['text']};
                        text-align:center;text-transform:uppercase;letter-spacing:1px;">
                Confidence
              </p>
            </td>
          </tr>
        </table>
      </div>
    </td>
  </tr>

  <!-- ANALYSIS -->
  <tr>
    <td style="padding:0 32px 24px;">
      <div style="background:#111827;border-radius:14px;border:1px solid #1e293b;
                  padding:20px 24px;">
        <p style="margin:0 0 12px;font-size:13px;color:#00c6ff;font-weight:700;
                  letter-spacing:1px;text-transform:uppercase;">
          💡 AI Analysis
        </p>
        <p style="margin:0;font-size:15px;color:#cbd5e1;line-height:1.75;">
          {explanation}
        </p>
      </div>
    </td>
  </tr>

  <!-- AGENTIC STEPS -->
  <tr>
    <td style="padding:0 32px 24px;">
      <table width="100%" cellspacing="8">
        <tr>
          <td width="33%" style="background:#0f1f3d;border-radius:12px;padding:14px 16px;
                                  border:1px solid #1e3a5f;text-align:center;">
            <p style="margin:0;font-size:20px;">🔍</p>
            <p style="margin:4px 0 2px;font-size:11px;color:#00c6ff;font-weight:700;
                      text-transform:uppercase;">Step 1</p>
            <p style="margin:0;font-size:12px;color:#94a3b8;">Signal Detected</p>
          </td>
          <td width="33%" style="background:#0f1f3d;border-radius:12px;padding:14px 16px;
                                  border:1px solid #1e3a5f;text-align:center;">
            <p style="margin:0;font-size:20px;">🧠</p>
            <p style="margin:4px 0 2px;font-size:11px;color:#7c3aed;font-weight:700;
                      text-transform:uppercase;">Step 2</p>
            <p style="margin:0;font-size:12px;color:#94a3b8;">Context Enriched</p>
          </td>
          <td width="33%" style="background:#0f1f3d;border-radius:12px;padding:14px 16px;
                                  border:1px solid #1e3a5f;text-align:center;">
            <p style="margin:0;font-size:20px;">🚨</p>
            <p style="margin:4px 0 2px;font-size:11px;color:#10b981;font-weight:700;
                      text-transform:uppercase;">Step 3</p>
            <p style="margin:0;font-size:12px;color:#94a3b8;">Alert Generated</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- RISK + PORTFOLIO -->
  <tr>
    <td style="padding:0 32px 24px;">
      <table width="100%">
        <tr>
          <td width="48%" style="background:#111827;border-radius:12px;padding:14px 18px;
                                  border:1px solid #1e293b;">
            <p style="margin:0 0 4px;font-size:11px;color:#475569;text-transform:uppercase;
                      letter-spacing:1px;">Risk Level</p>
            <p style="margin:0;font-size:18px;font-weight:700;color:#f59e0b;">{risk}</p>
          </td>
          <td width="4%"></td>
          <td width="48%" style="background:#111827;border-radius:12px;padding:14px 18px;
                                  border:1px solid #1e293b;">
            <p style="margin:0 0 4px;font-size:11px;color:#475569;text-transform:uppercase;
                      letter-spacing:1px;">Portfolio</p>
            <p style="margin:0;font-size:18px;font-weight:700;color:#7dd3fc;">
              Personalised ✓
            </p>
          </td>
        </tr>
      </table>
      {portfolio_section}
    </td>
  </tr>

  <!-- DISCLAIMER -->
  <tr>
    <td style="padding:0 32px 28px;">
      <div style="background:#0d1117;border-radius:10px;border:1px solid #f59e0b33;
                  padding:14px 18px;">
        <p style="margin:0;font-size:12px;color:#78716c;line-height:1.6;">
          ⚠️ <strong style="color:#f59e0b;">Disclaimer:</strong>
          This alert is generated by AutoInvest AI for educational purposes only.
          It does not constitute financial advice. Always consult a SEBI-registered
          investment advisor before making investment decisions.
        </p>
      </div>
    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="background:#060a12;padding:20px 32px;border-top:1px solid #1e293b;">
      <table width="100%">
        <tr>
          <td>
            <p style="margin:0;font-size:13px;font-weight:700;color:#00c6ff;
                      letter-spacing:1px;">📊 AUTOINVEST AI</p>
            <p style="margin:3px 0 0;font-size:11px;color:#374151;">
              Developed by {developer}
            </p>
          </td>
          <td align="right">
            <p style="margin:0;font-size:11px;color:#374151;">v2.0 Professional</p>
            <p style="margin:3px 0 0;font-size:11px;color:#374151;">NSE India</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def _build_plain(stock_name, ticker, price, change_pct, trend,
                 rsi, decision, conf, explanation, risk) -> str:
    chg_sym = "+" if change_pct >= 0 else ""
    return f"""
AutoInvest AI — Market Intelligence Alert
==========================================
Stock   : {stock_name} ({ticker.replace('.NS','')})
Price   : Rs {price:,.2f}
Change  : {chg_sym}{change_pct:.2f}% today
Trend   : {trend}
RSI     : {rsi:.1f}
Risk    : {risk}

AI DECISION: {decision}
Confidence : {conf}%

Analysis:
{explanation}

─────────────────────────────────────────
Agentic Pipeline:
  Step 1 — Signal Detected (RSI + Trend)
  Step 2 — Context Enriched (Portfolio-aware)
  Step 3 — Alert Generated

Disclaimer: For educational purposes only. Not financial advice.
Consult a SEBI-registered advisor before investing.

AutoInvest AI · Developed by A. SHANMUGANAADHAN
"""


# ─────────────────────────────────────────────────────────────
#  PUBLIC SEND FUNCTION
# ─────────────────────────────────────────────────────────────

def send_alert_email(
    smtp_host: str,
    smtp_port: int,
    sender_email: str,
    sender_password: str,
    recipient_email: str,
    stock_name: str,
    stock_ticker: str,
    price: float,
    change_pct: float,
    trend: str,
    rsi: float,
    decision: str,
    conf: int,
    explanation: str,
    risk: str,
    portfolio_summary: str = "",
    audio_bytes: bytes | None = None,
) -> tuple[bool, str]:
    """
    Send a rich HTML market alert email.

    Returns:
        (success: bool, message: str)
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = (
            f"🚨 AutoInvest AI Alert: {decision} — {stock_name} "
            f"(₹{price:,.0f} · {conf}% Confidence)"
        )
        msg["From"]    = f"AutoInvest AI <{sender_email}>"
        msg["To"]      = recipient_email

        plain = _build_plain(stock_name, stock_ticker, price, change_pct,
                             trend, rsi, decision, conf, explanation, risk)
        html  = _build_html(stock_name, stock_ticker, price, change_pct,
                            trend, rsi, decision, conf, explanation, risk,
                            portfolio_summary)

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html,  "html"))

        # Attach audio if provided
        if audio_bytes:
            part = MIMEBase("audio", "mpeg")
            part.set_payload(audio_bytes)
            encoders.encode_base64(part)
            safe_name = stock_ticker.replace(".NS", "")
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="autoinvest_{safe_name}_summary.mp3"'
            )
            msg.attach(part)

        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())

        return True, f"✅ Alert email sent to {recipient_email}"

    except smtplib.SMTPAuthenticationError:
        return False, ("❌ SMTP Authentication failed. "
                       "Use an App Password (not your main password) for Gmail.")
    except smtplib.SMTPConnectError:
        return False, f"❌ Could not connect to {smtp_host}:{smtp_port}. Check host/port."
    except Exception as e:
        return False, f"❌ Email failed: {str(e)}"


# ─────────────────────────────────────────────────────────────
#  SMTP PRESET CONFIGS
# ─────────────────────────────────────────────────────────────

SMTP_PRESETS = {
    "Gmail":   {"host": "smtp.gmail.com",    "port": 465,
                "note": "Use Gmail App Password (not your main password). "
                        "Enable 2FA → Google Account → Security → App Passwords."},
    "Outlook": {"host": "smtp.office365.com","port": 587,
                "note": "Use your Outlook/Hotmail password."},
    "Yahoo":   {"host": "smtp.mail.yahoo.com","port": 465,
                "note": "Use Yahoo App Password."},
    "Custom":  {"host": "",                  "port": 587,
                "note": "Enter your SMTP server details manually."},
}