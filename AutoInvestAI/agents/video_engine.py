# ============================================================
#  agents/video_engine.py
#  AI Market Video Engine — Agentic Architecture
#  Developer: A. SHANMUGANAADHAN
#  
#  Pipeline:
#    Step 1: detect_signal(portfolio)
#    Step 2: enrich_with_context(signal)
#    Step 3: generate_actionable_alert(enriched)
#    → Auto-generate narrated market video (BytesIO, no file path)
# ============================================================

import io
import time
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import yfinance as yf

try:
    from gtts import gTTS
    GTTS_OK = True
except ImportError:
    GTTS_OK = False

try:
    import imageio
    IMAGEIO_OK = True
except ImportError:
    IMAGEIO_OK = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch
    MPL_OK = True
except ImportError:
    MPL_OK = False


# ─────────────────────────────────────────────────────────────
#  COLOUR PALETTE
# ─────────────────────────────────────────────────────────────
PALETTE = {
    "bg":       (10,  14,  26),
    "card":     (17,  24,  39),
    "accent":   (0,  198, 255),
    "green":    (16, 185, 129),
    "red":      (239, 68,  68),
    "yellow":   (245,158,  11),
    "purple":   (124, 58, 237),
    "text":     (226,232,240),
    "muted":    (100,116,139),
}

W, H = 1280, 720   # frame dimensions


# ─────────────────────────────────────────────────────────────
#  UTILITY HELPERS
# ─────────────────────────────────────────────────────────────

def _hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _pil_color(key: str) -> tuple:
    return PALETTE[key]


def _rgba(key: str, alpha: int = 255) -> tuple:
    r, g, b = PALETTE[key]
    return (r, g, b, alpha)


def _get_font(size: int = 28, bold: bool = False):
    """Return a PIL font — falls back to default if no system fonts."""
    try:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
        for p in paths:
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    except Exception:
        pass
    return ImageFont.load_default()


def _draw_gradient_bg(draw: ImageDraw.Draw, w: int = W, h: int = H):
    """Dark radial-ish gradient background."""
    for y in range(h):
        ratio = y / h
        r = int(10  + ratio * 5)
        g = int(14  + ratio * 8)
        b = int(26  + ratio * 20)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def _draw_grid(draw: ImageDraw.Draw, w: int = W, h: int = H):
    """Subtle grid lines."""
    for x in range(0, w, 80):
        draw.line([(x, 0), (x, h)], fill=(255, 255, 255, 12), width=1)
    for y in range(0, h, 60):
        draw.line([(0, y), (w, y)], fill=(255, 255, 255, 12), width=1)


def _draw_accent_bar(draw: ImageDraw.Draw, w: int = W):
    """Top accent bar."""
    for i in range(4):
        alpha = 255 - i * 40
        draw.line([(0, i), (w, i)], fill=(*PALETTE["accent"], alpha))


def _pill(draw: ImageDraw.Draw, x, y, text, bg_color, text_color=(255,255,255), font=None):
    """Draw a rounded pill badge."""
    if font is None:
        font = _get_font(18, bold=True)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 16, 8
    rx0, ry0 = x, y
    rx1, ry1 = x + tw + pad_x * 2, y + th + pad_y * 2
    # rounded rect
    r = 14
    draw.rounded_rectangle([rx0, ry0, rx1, ry1], radius=r, fill=bg_color)
    draw.text((rx0 + pad_x, ry0 + pad_y), text, fill=text_color, font=font)
    return rx1 - rx0


# ─────────────────────────────────────────────────────────────
#  FRAME GENERATORS
# ─────────────────────────────────────────────────────────────

def _frame_title(stock_name: str, decision: str, price: float,
                 change_pct: float, conf: int) -> Image.Image:
    """Frame 1 — Title / Hero card."""
    img = Image.new("RGB", (W, H), PALETTE["bg"])
    draw = ImageDraw.Draw(img, "RGBA")

    _draw_gradient_bg(draw)
    _draw_grid(draw)
    _draw_accent_bar(draw)

    # Branding
    f_brand = _get_font(22, bold=True)
    draw.text((36, 18), "📊 AUTOINVEST AI  ·  MARKET INTELLIGENCE", fill=PALETTE["accent"], font=f_brand)
    draw.text((W - 200, 18), "NSE INDIA", fill=PALETTE["muted"], font=_get_font(18))

    # Divider
    draw.line([(36, 56), (W - 36, 56)], fill=(*PALETTE["accent"], 60), width=1)

    # Stock name
    f_stock = _get_font(64, bold=True)
    draw.text((80, 100), stock_name.upper(), fill=PALETTE["text"], font=f_stock)

    # Price
    f_price = _get_font(88, bold=True)
    draw.text((80, 178), f"₹ {price:,.2f}", fill=PALETTE["accent"], font=f_price)

    # Change
    chg_color = PALETTE["green"] if change_pct >= 0 else PALETTE["red"]
    chg_sym   = "▲" if change_pct >= 0 else "▼"
    f_chg = _get_font(38, bold=True)
    draw.text((80, 290), f"{chg_sym} {abs(change_pct):.2f}%  TODAY", fill=chg_color, font=f_chg)

    # Decision badge
    dec_key = "BUY" if "BUY" in decision else ("SELL" if "SELL" in decision else "HOLD")
    badge_colors = {
        "BUY":  ((*PALETTE["green"],), (6, 78, 59, 200)),
        "SELL": ((*PALETTE["red"],),   (69, 10, 10, 200)),
        "HOLD": ((*PALETTE["yellow"],),(28, 25, 23, 200)),
    }
    t_col, b_col = badge_colors.get(dec_key, badge_colors["HOLD"])
    f_dec = _get_font(52, bold=True)
    draw.rounded_rectangle([80, 355, 420, 445], radius=22, fill=b_col)
    draw.text((110, 362), f"● {decision}", fill=t_col[:3], font=f_dec)

    # Confidence arc (right side)
    cx, cy, cr = 980, 300, 140
    # Background arc
    draw.ellipse([cx-cr, cy-cr, cx+cr, cy+cr], outline=(*PALETTE["card"],), width=18)
    # Progress arc
    import math
    end_angle = -90 + (conf / 100) * 360
    steps = max(1, int((conf / 100) * 120))
    for i in range(steps):
        angle = math.radians(-90 + (i / 120) * 360)
        x1 = cx + (cr - 9) * math.cos(angle)
        y1 = cy + (cr - 9) * math.sin(angle)
        x2 = cx + (cr + 9) * math.cos(angle)
        y2 = cy + (cr + 9) * math.sin(angle)
        alpha = 200 + int(55 * i / steps)
        draw.line([(x1, y1), (x2, y2)], fill=(*PALETTE["accent"], alpha), width=3)

    f_conf_big = _get_font(58, bold=True)
    f_conf_lbl = _get_font(22)
    draw.text((cx - 52, cy - 38), f"{conf}%", fill=PALETTE["text"], font=f_conf_big)
    draw.text((cx - 55, cy + 30), "CONFIDENCE", fill=PALETTE["muted"], font=f_conf_lbl)

    # Footer
    draw.line([(36, H - 50), (W - 36, H - 50)], fill=(*PALETTE["accent"], 40), width=1)
    f_foot = _get_font(18)
    draw.text((36, H - 38), "AutoInvest AI · Developed by A. SHANMUGANAADHAN · Not financial advice",
              fill=PALETTE["muted"], font=f_foot)
    draw.text((W - 280, H - 38), time.strftime("%d %b %Y  %H:%M IST"),
              fill=PALETTE["muted"], font=f_foot)

    return img


def _frame_chart(data: pd.DataFrame, stock_name: str, decision: str) -> Image.Image:
    """Frame 2 — Price chart + RSI (matplotlib → PIL)."""
    if not MPL_OK:
        return _frame_placeholder("Chart unavailable — install matplotlib")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(W/100, H/100),
                                    gridspec_kw={"height_ratios": [3, 1]},
                                    facecolor="#0a0e1a")
    fig.subplots_adjust(hspace=0.08, left=0.07, right=0.97, top=0.92, bottom=0.08)

    dates = data["Date"] if "Date" in data.columns else np.arange(len(data))
    close = data["Close"].values
    ma20  = data["MA20"].values  if "MA20"  in data.columns else close
    ma50  = data["MA50"].values  if "MA50"  in data.columns else close
    rsi   = data["RSI"].values   if "RSI"   in data.columns else np.full(len(close), 50)
    bb_u  = data["BB_Upper"].values if "BB_Upper" in data.columns else None
    bb_l  = data["BB_Lower"].values if "BB_Lower" in data.columns else None

    ax1.set_facecolor("#111827")
    ax2.set_facecolor("#111827")

    # Price fill
    dec_color = "#10b981" if "BUY" in decision else ("#ef4444" if "SELL" in decision else "#f59e0b")
    ax1.fill_between(range(len(close)), close, close.min() * 0.98,
                     alpha=0.12, color=dec_color)
    ax1.plot(range(len(close)), close, color=dec_color, linewidth=2.5, label="Price", zorder=5)
    ax1.plot(range(len(ma20)), ma20, color="#00c6ff", linewidth=1.5, linestyle="--",
             label="MA20", alpha=0.9)
    ax1.plot(range(len(ma50)), ma50, color="#f59e0b", linewidth=1.5, linestyle=":",
             label="MA50", alpha=0.9)
    if bb_u is not None and bb_l is not None:
        ax1.fill_between(range(len(bb_u)), bb_u, bb_l, alpha=0.06, color="#7c3aed")
        ax1.plot(range(len(bb_u)), bb_u, color="#7c3aed", linewidth=1, alpha=0.5)
        ax1.plot(range(len(bb_l)), bb_l, color="#7c3aed", linewidth=1, alpha=0.5)

    ax1.set_title(f"{stock_name}  —  Price & Indicators",
                  color="#e2e8f0", fontsize=16, pad=10, fontweight="bold")
    ax1.set_ylabel("Price (₹)", color="#64748b", fontsize=11)
    ax1.tick_params(colors="#64748b", labelbottom=False)
    ax1.spines[:].set_color("#1e293b")
    ax1.yaxis.label.set_color("#64748b")
    ax1.legend(loc="upper left", facecolor="#111827", edgecolor="#1e293b",
               labelcolor="#e2e8f0", fontsize=10)
    ax1.grid(color="#1e293b", linewidth=0.6)

    # RSI
    rsi_color = np.where(rsi > 70, "#ef4444", np.where(rsi < 30, "#10b981", "#f97316"))
    ax2.plot(range(len(rsi)), rsi, color="#f97316", linewidth=2)
    ax2.fill_between(range(len(rsi)), rsi, 50, where=(rsi > 50), alpha=0.15, color="#ef4444")
    ax2.fill_between(range(len(rsi)), rsi, 50, where=(rsi < 50), alpha=0.15, color="#10b981")
    ax2.axhline(70, color="#ef4444", linewidth=1, linestyle="--", alpha=0.7)
    ax2.axhline(30, color="#10b981", linewidth=1, linestyle="--", alpha=0.7)
    ax2.axhline(50, color="#94a3b8", linewidth=0.8, linestyle=":", alpha=0.5)
    ax2.set_ylabel("RSI", color="#64748b", fontsize=11)
    ax2.set_ylim(0, 100)
    ax2.tick_params(colors="#64748b")
    ax2.spines[:].set_color("#1e293b")
    ax2.grid(color="#1e293b", linewidth=0.6)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, facecolor="#0a0e1a")
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB").resize((W, H))


def _frame_analysis(trend: str, rsi: float, decision: str,
                    explanation: str, risk: str) -> Image.Image:
    """Frame 3 — AI Analysis breakdown."""
    img = Image.new("RGB", (W, H), PALETTE["bg"])
    draw = ImageDraw.Draw(img, "RGBA")
    _draw_gradient_bg(draw)
    _draw_grid(draw)
    _draw_accent_bar(draw)

    # Header
    f_h = _get_font(30, bold=True)
    draw.text((36, 18), "📊 AUTOINVEST AI  ·  ANALYSIS BREAKDOWN", fill=PALETTE["accent"], font=f_h)
    draw.line([(36, 58), (W - 36, 58)], fill=(*PALETTE["accent"], 50), width=1)

    # Left column — indicators
    metrics = [
        ("TREND",      trend,          "accent"),
        ("RSI",        f"{rsi:.1f}",   "red" if rsi > 70 else "green" if rsi < 30 else "yellow"),
        ("RISK LEVEL", risk,           "muted"),
    ]
    f_lbl = _get_font(20)
    f_val = _get_font(48, bold=True)
    y = 90
    for lbl, val, col in metrics:
        draw.rounded_rectangle([50, y, 360, y + 110], radius=16,
                               fill=(*PALETTE["card"], 200))
        draw.text((72, y + 12), lbl, fill=PALETTE["muted"], font=f_lbl)
        draw.text((72, y + 40), val, fill=PALETTE[col], font=f_val)
        y += 128

    # Decision centre
    dec_key = "BUY" if "BUY" in decision else ("SELL" if "SELL" in decision else "HOLD")
    dc_map = {
        "BUY":  ((6,78,59,220),   PALETTE["green"]),
        "SELL": ((69,10,10,220),  PALETTE["red"]),
        "HOLD": ((28,25,23,220),  PALETTE["yellow"]),
    }
    bg_col, fg_col = dc_map.get(dec_key, dc_map["HOLD"])
    draw.rounded_rectangle([420, 90, 860, 210], radius=24, fill=bg_col)
    f_dec = _get_font(80, bold=True)
    draw.text((460, 108), f"● {decision}", fill=fg_col, font=f_dec)

    # Explanation box
    draw.rounded_rectangle([420, 225, 860, 495], radius=18,
                           fill=(*PALETTE["card"], 200))
    f_exp_h = _get_font(22, bold=True)
    draw.text((446, 244), "💡 AI EXPLANATION", fill=PALETTE["accent"], font=f_exp_h)
    draw.line([(446, 272), (838, 272)], fill=(*PALETTE["accent"], 40), width=1)

    f_exp = _get_font(20)
    # Word-wrap explanation
    words = explanation.split()
    lines_exp = []
    cur = ""
    for w in words:
        test = cur + " " + w if cur else w
        if len(test) > 52:
            lines_exp.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines_exp.append(cur)

    ey = 285
    for line in lines_exp[:8]:
        draw.text((446, ey), line, fill=PALETTE["text"], font=f_exp)
        ey += 26

    # Agentic pipeline steps (right column)
    steps = [
        ("1️⃣ SIGNAL DETECTED",    "Market indicators scanned"),
        ("2️⃣ CONTEXT ENRICHED",   "Portfolio + RSI + Trend"),
        ("3️⃣ ALERT GENERATED",    "Personalised recommendation"),
    ]
    f_step_h = _get_font(20, bold=True)
    f_step_b = _get_font(17)
    sx, sy = 900, 90
    for sh, sb in steps:
        draw.rounded_rectangle([sx, sy, W - 40, sy + 88], radius=14,
                               fill=(*PALETTE["card"], 200))
        draw.line([(sx, sy), (sx, sy + 88)], fill=PALETTE["accent"], width=3)
        draw.text((sx + 14, sy + 12), sh, fill=PALETTE["accent"], font=f_step_h)
        draw.text((sx + 14, sy + 44), sb,  fill=PALETTE["text"],  font=f_step_b)
        sy += 104

    # Footer
    draw.line([(36, H - 50), (W - 36, H - 50)], fill=(*PALETTE["accent"], 40), width=1)
    f_foot = _get_font(17)
    draw.text((36, H - 36),
              "AutoInvest AI · Agentic Architecture · A. SHANMUGANAADHAN",
              fill=PALETTE["muted"], font=f_foot)

    return img


def _frame_portfolio(portfolio: list[dict], stock: str,
                     decision: str, conf: int) -> Image.Image:
    """Frame 4 — Portfolio context & personalised signal."""
    img = Image.new("RGB", (W, H), PALETTE["bg"])
    draw = ImageDraw.Draw(img, "RGBA")
    _draw_gradient_bg(draw)
    _draw_grid(draw)
    _draw_accent_bar(draw)

    f_h = _get_font(30, bold=True)
    draw.text((36, 18), "📊 AUTOINVEST AI  ·  PORTFOLIO PERSONALISATION",
              fill=PALETTE["accent"], font=f_h)
    draw.line([(36, 58), (W - 36, 58)], fill=(*PALETTE["accent"], 50), width=1)

    f_th = _get_font(20, bold=True)
    f_td = _get_font(19)

    headers = ["STOCK", "QTY", "AVG COST (₹)", "SIGNAL", "WEIGHT"]
    col_x   = [60, 250, 380, 560, 730]
    row_y   = 90

    # Header row
    draw.rounded_rectangle([40, row_y, W - 40, row_y + 44], radius=10,
                           fill=(*PALETTE["card"], 240))
    for hx, ht in zip(col_x, headers):
        draw.text((hx, row_y + 10), ht, fill=PALETTE["accent"], font=f_th)

    row_y += 56
    for i, item in enumerate(portfolio[:7]):
        row_bg = (*PALETTE["card"], 180) if i % 2 == 0 else (*PALETTE["bg"], 120)
        draw.rounded_rectangle([40, row_y, W - 40, row_y + 52], radius=10, fill=row_bg)

        s_name = item.get("stock", "").replace(".NS", "")
        qty    = str(item.get("qty", 0))
        avg    = f"₹{item.get('avg_cost', 0):,.2f}"
        sig    = item.get("signal", "HOLD")
        wt     = f"{item.get('weight', 0):.1f}%"

        sig_col = PALETTE["green"] if "BUY" in sig else (
                  PALETTE["red"] if "SELL" in sig else PALETTE["yellow"])
        is_current = s_name in stock
        row_txt_col = PALETTE["accent"] if is_current else PALETTE["text"]

        draw.text((col_x[0], row_y + 14), s_name, fill=row_txt_col, font=f_td)
        draw.text((col_x[1], row_y + 14), qty,    fill=PALETTE["text"],   font=f_td)
        draw.text((col_x[2], row_y + 14), avg,    fill=PALETTE["text"],   font=f_td)
        draw.text((col_x[3], row_y + 14), sig,    fill=sig_col,           font=f_td)
        draw.text((col_x[4], row_y + 14), wt,     fill=PALETTE["muted"],  font=f_td)

        if is_current:
            draw.line([(40, row_y), (40, row_y + 52)], fill=PALETTE["accent"], width=3)

        row_y += 60

    # Personalised signal summary
    dec_key = "BUY" if "BUY" in decision else ("SELL" if "SELL" in decision else "HOLD")
    dc_map  = {
        "BUY":  ((6,78,59,230),   PALETTE["green"]),
        "SELL": ((69,10,10,230),  PALETTE["red"]),
        "HOLD": ((28,25,23,230),  PALETTE["yellow"]),
    }
    bg_col, fg_col = dc_map.get(dec_key, dc_map["HOLD"])
    bx = 900
    draw.rounded_rectangle([bx, 90, W - 40, 340], radius=20, fill=bg_col)
    f_sig = _get_font(52, bold=True)
    f_sig_s = _get_font(22)
    draw.text((bx + 20, 106), "SIGNAL", fill=fg_col, font=f_sig_s)
    draw.text((bx + 20, 140), decision, fill=fg_col, font=f_sig)
    draw.text((bx + 20, 222), f"Confidence", fill=PALETTE["muted"], font=f_sig_s)
    draw.text((bx + 20, 250), f"{conf}%", fill=fg_col, font=_get_font(42, bold=True))

    # Footer
    draw.line([(36, H - 50), (W - 36, H - 50)], fill=(*PALETTE["accent"], 40), width=1)
    draw.text((36, H - 36), "Personalised for your portfolio  ·  AutoInvest AI",
              fill=PALETTE["muted"], font=_get_font(17))

    return img


def _frame_alert(stock_name: str, decision: str, explanation: str,
                 conf: int, email: str = "") -> Image.Image:
    """Frame 5 — Alert / CTA frame."""
    img = Image.new("RGB", (W, H), PALETTE["bg"])
    draw = ImageDraw.Draw(img, "RGBA")
    _draw_gradient_bg(draw)
    _draw_grid(draw)
    _draw_accent_bar(draw)

    dec_key = "BUY" if "BUY" in decision else ("SELL" if "SELL" in decision else "HOLD")
    dc_map = {
        "BUY":  ((6,78,59,220),   PALETTE["green"],  "🟢"),
        "SELL": ((69,10,10,220),  PALETTE["red"],    "🔴"),
        "HOLD": ((28,25,23,220),  PALETTE["yellow"], "🟡"),
    }
    bg_col, fg_col, emj = dc_map.get(dec_key, dc_map["HOLD"])

    # Big alert box
    draw.rounded_rectangle([60, 60, W - 60, 280], radius=28, fill=bg_col)
    f_big = _get_font(36, bold=True)
    f_med = _get_font(26)
    draw.text((100, 82),  "🚨 AUTOINVEST AI ALERT", fill=fg_col,       font=f_big)
    draw.text((100, 132), f"{emj}  {decision}  —  {stock_name}",        fill=fg_col, font=_get_font(52, bold=True))
    draw.text((100, 208), f"Confidence: {conf}%   ·   {time.strftime('%d %b %Y  %H:%M IST')}",
              fill=PALETTE["muted"], font=f_med)

    # Explanation
    draw.rounded_rectangle([60, 300, W - 60, 520], radius=20,
                           fill=(*PALETTE["card"], 210))
    draw.text((90, 318), "💡 Analysis", fill=PALETTE["accent"], font=_get_font(24, bold=True))
    words = explanation.split()
    lines_e, cur = [], ""
    for w in words:
        test = cur + " " + w if cur else w
        if len(test) > 76:
            lines_e.append(cur); cur = w
        else:
            cur = test
    if cur: lines_e.append(cur)
    ey = 354
    for line in lines_e[:5]:
        draw.text((90, ey), line, fill=PALETTE["text"], font=_get_font(21))
        ey += 30

    # Agentic badge
    draw.rounded_rectangle([60, 540, 620, 610], radius=14,
                           fill=(*PALETTE["purple"], 180))
    draw.text((80, 558),
              "⚡ Agentic AI  ·  3-Step Pipeline  ·  Portfolio-Aware",
              fill=PALETTE["text"], font=_get_font(20))

    # Email sent badge
    if email:
        draw.rounded_rectangle([640, 540, W - 60, 610], radius=14,
                               fill=(*PALETTE["green"], 180))
        draw.text((660, 558), f"📧 Alert sent to: {email}",
                  fill=(10, 14, 26), font=_get_font(20, bold=True))

    # Footer
    draw.line([(36, H - 50), (W - 36, H - 50)], fill=(*PALETTE["accent"], 40), width=1)
    draw.text((36, H - 36),
              "AutoInvest AI · Developed by A. SHANMUGANAADHAN · Not financial advice",
              fill=PALETTE["muted"], font=_get_font(17))

    return img


def _frame_placeholder(msg: str) -> Image.Image:
    img = Image.new("RGB", (W, H), PALETTE["bg"])
    draw = ImageDraw.Draw(img)
    draw.text((80, H // 2 - 20), msg, fill=PALETTE["muted"], font=_get_font(28))
    return img


# ─────────────────────────────────────────────────────────────
#  MAIN PUBLIC FUNCTION
# ─────────────────────────────────────────────────────────────

def generate_market_video(
    stock: str,
    stock_name: str,
    price: float,
    change_pct: float,
    trend: str,
    rsi: float,
    decision: str,
    explanation: str,
    conf: int,
    risk: str,
    data: pd.DataFrame,
    portfolio: list[dict] | None = None,
    email: str = "",
    lang: str = "en",
    fps: int = 24,
    seconds_per_frame: int = 4,
) -> tuple[bytes | None, bytes | None]:
    """
    Agentic 3-step video generation pipeline:
      Step 1 — Detect signal (title frame)
      Step 2 — Enrich with context (chart + analysis frames)
      Step 3 — Generate actionable alert (portfolio + alert frames)

    Returns:
        (video_bytes_or_None, audio_bytes_or_None)
        video is GIF (widely supported); audio is MP3 via gTTS.
    """

    # ── STEP 1: Detect signal ──────────────────────────────
    frames_pil: list[Image.Image] = []
    frames_pil.append(_frame_title(stock_name, decision, price, change_pct, conf))

    # ── STEP 2: Enrich with context ────────────────────────
    frames_pil.append(_frame_chart(data, stock_name, decision))
    frames_pil.append(_frame_analysis(trend, rsi, decision, explanation, risk))

    # ── STEP 3: Generate actionable alert ─────────────────
    if portfolio:
        frames_pil.append(_frame_portfolio(portfolio, stock, decision, conf))
    frames_pil.append(_frame_alert(stock_name, decision, explanation, conf, email))

    # ── Build GIF ─────────────────────────────────────────
    video_bytes = None
    gif_buf = io.BytesIO()
    try:
        # Duplicate each frame for duration effect
        dup = seconds_per_frame * fps // 10   # GIF uses centiseconds
        duration_ms = seconds_per_frame * 1000

        frames_pil[0].save(
            gif_buf,
            format="GIF",
            save_all=True,
            append_images=frames_pil[1:],
            duration=duration_ms,
            loop=0,
            optimize=False,
        )
        gif_buf.seek(0)
        video_bytes = gif_buf.read()
    except Exception as e:
        video_bytes = None

    # ── Build Audio (gTTS) ────────────────────────────────
    audio_bytes = None
    if GTTS_OK:
        try:
            script = _build_script(stock_name, price, change_pct, trend,
                                   rsi, decision, conf, explanation, risk)
            tts = gTTS(text=script, lang=lang, slow=False)
            abuf = io.BytesIO()
            tts.write_to_fp(abuf)
            abuf.seek(0)
            audio_bytes = abuf.read()
        except Exception:
            audio_bytes = None

    return video_bytes, audio_bytes


def _build_script(stock_name, price, change_pct, trend,
                  rsi, decision, conf, explanation, risk) -> str:
    chg_word = "up" if change_pct >= 0 else "down"
    return (
        f"AutoInvest AI — Market Intelligence Update. "
        f"Stock under analysis: {stock_name}. "
        f"Current price: Rupees {price:,.0f}, {chg_word} {abs(change_pct):.1f} percent today. "
        f"Step one — Signal detected. Market trend is {trend}. "
        f"Relative Strength Index stands at {rsi:.0f}. "
        f"Step two — Context enriched. Risk level is {risk}. "
        f"Step three — Actionable alert generated. "
        f"AI Decision: {decision}. Confidence: {conf} percent. "
        f"{explanation} "
        f"Always consult a SEBI registered advisor before making investment decisions. "
        f"This analysis was generated by AutoInvest AI, developed by A Shanmuganaadhan."
    )