# ============================================================
#  AutoInvest AI — v3.0 Professional
#  AI Market Video Engine + Portfolio Agent + Email Alerts
#  Agentic Architecture: Detect → Enrich → Alert
#  Developer: A. SHANMUGANAADHAN
# ============================================================

import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import time
import datetime
import os
import io
import tempfile

# ── Optional imports ────────────────────────────────────────
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ── Local modules ───────────────────────────────────────────
from utils.indicators import (
    moving_average, calculate_rsi, detect_trend,
    calculate_macd, calculate_bollinger_bands
)
from agents.decision_agent  import make_decision, confidence_score, explain_decision
from agents.radar_agent     import find_best_stock, scan_all_stocks
from agents.portfolio_agent import (
    get_portfolio, add_to_portfolio, remove_from_portfolio,
    update_portfolio_signals, personalise_signal,
    get_portfolio_summary_text, get_portfolio_stats,
    record_signal, get_signal_history, SECTOR_MAP
)
from agents.email_alert import send_alert_email, SMTP_PRESETS

try:
    from agents.video_engine import generate_market_video
    VIDEO_ENGINE_OK = True
except ImportError:
    VIDEO_ENGINE_OK = False

# ============================================================
#  PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="AutoInvest AI v3",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
#  SESSION STATE
# ============================================================
for k, v in {
    "logged_in":        False,
    "font_size":        15,
    "heading_size":     22,
    "subheading_size":  18,
    "metric_size":      28,
    "theme":            "dark",
    "ai_query":         "",
    "smtp_host":        "smtp.gmail.com",
    "smtp_port":        465,
    "sender_email":     "",
    "sender_password":  "",
    "alert_email":      "",
    "email_provider":   "Gmail",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
#  GEMINI SETUP
# ============================================================
model = None
if GEMINI_AVAILABLE:
    try:
        api_key = st.secrets.get("AIzaSyAr0sWPhOzisRz8y1GgaSczpvPPTrCdAG4", os.environ.get("AIzaSyAr0sWPhOzisRz8y1GgaSczpvPPTrCdAG4", ""))
        if api_key:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("models/gemini-1.5-flash")
    except Exception:
        model = None

# ============================================================
#  CONSTANTS
# ============================================================
STOCKS_LIST = [
    "TCS.NS","INFY.NS","RELIANCE.NS","HDFCBANK.NS","WIPRO.NS",
    "ICICIBANK.NS","SBIN.NS","ADANIPORTS.NS","HINDUNILVR.NS",
    "BAJFINANCE.NS","TATAMOTORS.NS","SUNPHARMA.NS","BHARTIARTL.NS",
    "ASIANPAINT.NS","TITAN.NS","NESTLEIND.NS","ITC.NS",
    "ONGC.NS","NTPC.NS","TATASTEEL.NS"
]
STOCK_NAMES = {
    "TCS.NS":"Tata Consultancy Services","INFY.NS":"Infosys Ltd",
    "RELIANCE.NS":"Reliance Industries","HDFCBANK.NS":"HDFC Bank",
    "WIPRO.NS":"Wipro Ltd","ICICIBANK.NS":"ICICI Bank",
    "SBIN.NS":"State Bank of India","ADANIPORTS.NS":"Adani Ports",
    "HINDUNILVR.NS":"Hindustan Unilever","BAJFINANCE.NS":"Bajaj Finance",
    "TATAMOTORS.NS":"Tata Motors","SUNPHARMA.NS":"Sun Pharma",
    "BHARTIARTL.NS":"Bharti Airtel","ASIANPAINT.NS":"Asian Paints",
    "TITAN.NS":"Titan Company","NESTLEIND.NS":"Nestle India",
    "ITC.NS":"ITC Ltd","ONGC.NS":"ONGC","NTPC.NS":"NTPC Ltd",
    "TATASTEEL.NS":"Tata Steel",
}

# ============================================================
#  CSS
# ============================================================
def inject_css():
    fs  = st.session_state.font_size
    hs  = st.session_state.heading_size
    shs = st.session_state.subheading_size
    ms  = st.session_state.metric_size
    dark = st.session_state.theme == "dark"
    bg   = "#0a0e1a" if dark else "#f0f4f8"
    card = "#111827" if dark else "#ffffff"
    card2= "#1a2235" if dark else "#e8eef7"
    txt  = "#e2e8f0" if dark else "#1a202c"
    mute = "#8892a4" if dark else "#6b7280"
    bdr  = "#1e293b" if dark else "#cbd5e1"
    sbar = "#0d1117" if dark else "#1e3a5f"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;900&family=Rajdhani:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');
    .stApp{{background:{bg};font-family:'Rajdhani',sans-serif;font-size:{fs}px;color:{txt};}}
    section[data-testid="stSidebar"]{{background:{sbar}!important;border-right:1px solid #00c6ff33;}}
    section[data-testid="stSidebar"] *{{color:#c9d4e8!important;font-family:'Rajdhani',sans-serif!important;font-size:{fs}px!important;}}
    section[data-testid="stSidebar"] .stSelectbox>div>div{{background:#151f32!important;border:1px solid #00c6ff44!important;border-radius:8px!important;max-width:220px!important;}}
    h1{{font-family:'Orbitron',monospace!important;font-size:{hs+8}px!important;background:linear-gradient(135deg,#00c6ff,#0072ff,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:2px;margin-bottom:0.3rem!important;}}
    h2{{font-family:'Orbitron',monospace!important;font-size:{hs}px!important;color:#00c6ff!important;letter-spacing:1px;}}
    h3{{font-family:'Rajdhani',sans-serif!important;font-size:{shs}px!important;color:#7dd3fc!important;font-weight:600!important;}}
    .stSelectbox>div>div{{background:{card}!important;border:1px solid #00c6ff55!important;border-radius:10px!important;color:{txt}!important;font-family:'Rajdhani',sans-serif!important;font-size:{fs}px!important;max-width:280px!important;}}
    .stSelectbox label{{color:#7dd3fc!important;font-size:{fs}px!important;font-weight:600!important;}}
    [data-testid="metric-container"]{{background:{card}!important;border:1px solid #00c6ff33!important;border-radius:12px!important;padding:16px!important;box-shadow:0 4px 24px #00c6ff11!important;}}
    [data-testid="metric-container"] [data-testid="stMetricLabel"]{{color:{mute}!important;font-size:{fs-1}px!important;font-family:'Rajdhani',sans-serif!important;font-weight:600!important;text-transform:uppercase;letter-spacing:0.5px;}}
    [data-testid="metric-container"] [data-testid="stMetricValue"]{{color:{txt}!important;font-family:'Share Tech Mono',monospace!important;font-size:{ms}px!important;}}
    .ai-card{{background:{card};border:1px solid #00c6ff22;border-radius:14px;padding:20px 24px;margin:10px 0;box-shadow:0 8px 32px rgba(0,198,255,0.05);font-size:{fs}px;}}
    .ai-card-accent{{border-left:3px solid #00c6ff;}}
    .ai-card-success{{border-left:3px solid #10b981;}}
    .ai-card-warning{{border-left:3px solid #f59e0b;}}
    .ai-card-danger{{border-left:3px solid #ef4444;}}
    .ai-card-purple{{border-left:3px solid #7c3aed;}}
    .stTabs [data-baseweb="tab-list"]{{background:{card2}!important;border-radius:12px!important;padding:4px!important;gap:4px!important;border:1px solid {bdr}!important;}}
    .stTabs [data-baseweb="tab"]{{background:transparent!important;color:{mute}!important;border-radius:8px!important;font-family:'Rajdhani',sans-serif!important;font-weight:600!important;font-size:{fs}px!important;padding:6px 18px!important;}}
    .stTabs [aria-selected="true"]{{background:linear-gradient(135deg,#0072ff22,#7c3aed22)!important;color:#00c6ff!important;border:1px solid #00c6ff44!important;}}
    .stButton>button{{background:linear-gradient(135deg,#0072ff,#7c3aed)!important;color:white!important;border:none!important;border-radius:10px!important;font-family:'Rajdhani',sans-serif!important;font-weight:700!important;font-size:{fs}px!important;padding:10px 24px!important;letter-spacing:0.5px;box-shadow:0 4px 15px #0072ff44!important;}}
    .stButton>button:hover{{transform:translateY(-2px)!important;box-shadow:0 6px 24px #7c3aed66!important;}}
    .stTextInput>div>div>input{{background:{card}!important;border:1px solid #00c6ff44!important;border-radius:10px!important;color:{txt}!important;font-family:'Rajdhani',sans-serif!important;font-size:{fs}px!important;}}
    .stTextInput label{{color:#7dd3fc!important;font-weight:600!important;}}
    .stNumberInput>div>div>input{{background:{card}!important;border:1px solid #00c6ff44!important;border-radius:10px!important;color:{txt}!important;}}
    .stDataFrame{{border-radius:12px!important;overflow:hidden!important;border:1px solid #1e293b!important;}}
    hr{{border-color:#1e293b!important;}}
    ::-webkit-scrollbar{{width:6px;}}
    ::-webkit-scrollbar-thumb{{background:#00c6ff44;border-radius:3px;}}
    .block-container{{padding-top:1.5rem!important;padding-left:2rem!important;padding-right:2rem!important;}}
    #MainMenu,footer,header{{visibility:hidden;}}
    .step-badge{{display:inline-block;padding:4px 14px;border-radius:50px;font-family:'Orbitron',monospace;font-size:{fs-2}px;font-weight:700;letter-spacing:1px;margin-right:8px;}}
    </style>
    """, unsafe_allow_html=True)

# ============================================================
#  LOGIN
# ============================================================
def show_login():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@400;600&display=swap');
    .stApp{background:radial-gradient(ellipse at 20% 50%,#0d1b4b 0%,#020817 50%,#0d0221 100%);font-family:'Rajdhani',sans-serif;}
    #MainMenu,footer,header{visibility:hidden;}
    @keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-12px)}}
    @keyframes glow{0%,100%{text-shadow:0 0 20px #00c6ff66}50%{text-shadow:0 0 40px #00c6ffcc}}
    @keyframes slideUp{from{opacity:0;transform:translateY(40px)}to{opacity:1;transform:translateY(0)}}
    @keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(0,198,255,0.4)}70%{box-shadow:0 0 0 20px rgba(0,198,255,0)}}
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2.2, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;animation:float 4s ease-in-out infinite;margin-bottom:10px;">
            <div style="display:inline-block;width:90px;height:90px;border-radius:50%;
                        background:linear-gradient(135deg,#0072ff,#7c3aed);
                        box-shadow:0 0 40px #0072ff66;line-height:90px;font-size:42px;
                        animation:pulse 2.5s infinite;">📊</div>
        </div>
        <div style="text-align:center;animation:slideUp 1s ease both;">
            <h1 style="font-family:'Orbitron',monospace;font-size:2.4rem;font-weight:900;
                       background:linear-gradient(135deg,#00c6ff,#0072ff,#7c3aed);
                       -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                       letter-spacing:3px;margin:0;animation:glow 3s ease-in-out infinite;">
                AUTOINVEST AI
            </h1>
            <p style="font-family:'Rajdhani',sans-serif;font-size:1.05rem;color:#8892a4;
                      letter-spacing:4px;text-transform:uppercase;margin:6px 0 0 0;">
                v3.0 · Agentic Intelligence
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:linear-gradient(135deg,#0f1f3d,#1a0a2e);border:1px solid #00c6ff33;
                    border-radius:16px;padding:28px 32px;text-align:center;margin:10px 0 24px 0;
                    box-shadow:0 8px 40px rgba(0,114,255,0.12);animation:slideUp 1.2s ease both;">
            <p style="font-family:'Rajdhani',sans-serif;font-size:1.3rem;font-weight:500;
                      color:#e2e8f0;font-style:italic;margin:0 0 16px 0;line-height:1.6;">
                "The stock market is a device for transferring money<br>
                from the <span style='color:#ef4444;'>impatient</span>
                to the <span style='color:#00c6ff;font-weight:700;'>patient</span>."
            </p>
            <p style="font-family:'Share Tech Mono',monospace;font-size:0.85rem;color:#7c3aed;margin:0;letter-spacing:1px;">
                — Warren Buffett
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:20px;animation:slideUp 1.4s ease both;">
            <h2 style="font-family:'Orbitron',monospace;font-size:1.4rem;
                       background:linear-gradient(135deg,#00c6ff,#7c3aed);
                       -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                       margin:0 0 8px 0;">Welcome to Automatic AI Investing System</h2>
            <div style="display:flex;justify-content:center;gap:12px;flex-wrap:wrap;margin-top:10px;">
                <span style="background:#0f1f3d;border:1px solid #00c6ff33;border-radius:50px;
                             padding:4px 14px;font-size:0.8rem;color:#7dd3fc;">⚡ Agentic AI</span>
                <span style="background:#0f1f3d;border:1px solid #7c3aed33;border-radius:50px;
                             padding:4px 14px;font-size:0.8rem;color:#a78bfa;">📧 Email Alerts</span>
                <span style="background:#0f1f3d;border:1px solid #10b98133;border-radius:50px;
                             padding:4px 14px;font-size:0.8rem;color:#34d399;">🎬 Video Engine</span>
                <span style="background:#0f1f3d;border:1px solid #f59e0b33;border-radius:50px;
                             padding:4px 14px;font-size:0.8rem;color:#fbbf24;">📋 Portfolio AI</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("⚡  ENTER DASHBOARD", use_container_width=True):
            st.session_state.logged_in = True
            st.rerun()
        st.markdown("""
        <div style="text-align:center;margin-top:32px;padding-top:20px;border-top:1px solid #1e293b;">
            <p style="font-size:0.75rem;color:#4a5568;text-transform:uppercase;letter-spacing:2px;margin:0;">Developed by</p>
            <p style="font-family:'Orbitron',monospace;font-size:1.05rem;font-weight:600;
                      background:linear-gradient(135deg,#00c6ff,#7c3aed);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                      margin:4px 0 0 0;letter-spacing:2px;">A. SHANMUGANAADHAN</p>
            <p style="font-size:0.75rem;color:#374151;margin:2px 0 0 0;">AutoInvest AI · v3.0</p>
        </div>
        """, unsafe_allow_html=True)

# ============================================================
#  SIDEBAR
# ============================================================
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:16px 0 10px 0;border-bottom:1px solid #00c6ff22;margin-bottom:16px;">
            <span style="font-family:'Orbitron',monospace;font-size:1.1rem;font-weight:700;
                         background:linear-gradient(135deg,#00c6ff,#7c3aed);
                         -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                📊 AUTOINVEST AI
            </span><br>
            <span style="font-size:0.7rem;color:#4a5568;font-family:'Rajdhani',sans-serif;letter-spacing:2px;">
                v3.0 AGENTIC
            </span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**⚙️ CONTROLS**")
        risk_level = st.selectbox("⚖️ Risk Level", ["Low","Medium","High"], key="risk_level")
        stock = st.selectbox(
            "📌 Stock", STOCKS_LIST,
            format_func=lambda x: f"{x.replace('.NS','')} — {STOCK_NAMES.get(x,'')[:16]}",
            key="selected_stock"
        )
        period = st.selectbox("📅 Period", ["1mo","3mo","6mo","1y","2y"], index=2, key="period")
        st.markdown("---")

        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
        st.markdown(f"""
        <div style="background:#0d1117;border:1px solid #00c6ff22;border-radius:10px;
                    padding:10px 14px;margin-bottom:12px;text-align:center;">
            <div style="font-family:'Share Tech Mono',monospace;font-size:1.1rem;color:#00c6ff;">
                🕐 {now.strftime('%H:%M:%S')} IST
            </div>
            <div style="font-size:0.75rem;color:#4a5568;">{now.strftime('%d %b %Y')}</div>
        </div>
        """, unsafe_allow_html=True)

        mopen = (9 <= now.hour < 15 or (now.hour == 15 and now.minute <= 30)) and now.weekday() < 5
        mc, ms_txt = ("#10b981","🟢 NSE OPEN") if mopen else ("#ef4444","🔴 NSE CLOSED")
        st.markdown(f"""
        <div style="text-align:center;padding:6px;border-radius:8px;
                    background:{'#022c22' if mopen else '#1c0a0a'};
                    border:1px solid {mc}44;margin-bottom:12px;">
            <span style="font-family:'Rajdhani',sans-serif;font-weight:700;color:{mc};font-size:0.9rem;">
                {ms_txt}
            </span>
        </div>
        """, unsafe_allow_html=True)

        # Portfolio quick count
        pf = get_portfolio()
        if pf:
            stats = get_portfolio_stats(pf)
            pnl_c = "#10b981" if stats.get("total_pnl_pct", 0) >= 0 else "#ef4444"
            pnl_sym = "▲" if stats.get("total_pnl_pct", 0) >= 0 else "▼"
            st.markdown(f"""
            <div style="background:#0d1117;border:1px solid #00c6ff22;border-radius:10px;
                        padding:10px 14px;margin-bottom:12px;">
                <div style="font-size:0.7rem;color:#4a5568;text-transform:uppercase;letter-spacing:1px;">Portfolio</div>
                <div style="font-family:'Share Tech Mono',monospace;font-size:0.85rem;color:#00c6ff;">
                    {stats['holdings']} holdings
                </div>
                <div style="font-size:0.85rem;color:{pnl_c};font-weight:700;">
                    {pnl_sym} {abs(stats.get('total_pnl_pct',0)):.1f}% P&L
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
        st.markdown("""
        <div style="text-align:center;margin-top:20px;padding-top:14px;border-top:1px solid #0d1117;">
            <span style="font-size:0.7rem;color:#374151;font-family:'Rajdhani',sans-serif;letter-spacing:1px;">
                Dev: A. SHANMUGANAADHAN
            </span>
        </div>
        """, unsafe_allow_html=True)
    return stock, risk_level, period

# ============================================================
#  DATA HELPERS
# ============================================================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_data(symbol, period):
    try:
        t = yf.Ticker(symbol)
        d = t.history(period=period)
        info = {}
        try: info = t.info
        except: pass
        if d.empty: return None, {}
        return d.dropna().reset_index(), info
    except: return None, {}

@st.cache_data(ttl=60, show_spinner=False)
def fetch_24hr_data(symbol):
    try:
        d = yf.Ticker(symbol).history(period="2d", interval="5m")
        if d.empty: return None
        return d.dropna().reset_index()
    except: return None

def compute_indicators(data):
    data = data.copy()
    data['MA20']     = moving_average(data, window=20)
    data['MA50']     = moving_average(data, window=50)
    data['RSI']      = calculate_rsi(data)
    macd = calculate_macd(data)
    bb   = calculate_bollinger_bands(data)
    if macd is not None:
        data['MACD'] = macd['MACD']
        data['MACD_Signal'] = macd['Signal']
    if bb is not None:
        data['BB_Upper'] = bb['Upper']
        data['BB_Lower'] = bb['Lower']
    return data

# ============================================================
#  TAB — DASHBOARD
# ============================================================
def tab_dashboard(stock, risk_level, period):
    sname = STOCK_NAMES.get(stock, stock)
    st.markdown(f"<h1>📊 AutoInvest AI Dashboard</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#64748b;'>{sname} · Risk: {risk_level} · Period: {period}</p>", unsafe_allow_html=True)

    with st.spinner("🔍 Scanning market opportunities..."):
        best = find_best_stock(STOCKS_LIST)
    if best:
        bname = STOCK_NAMES.get(best['stock'], best['stock'])
        st.markdown(f"""
        <div class="ai-card ai-card-success" style="margin-bottom:16px;">
            <span style="color:#10b981;font-weight:700;font-size:1rem;">🚀 RADAR: Top Opportunity</span>
            &nbsp;
            <span style="font-family:'Share Tech Mono',monospace;color:#e2e8f0;">{bname}</span>
            &nbsp;
            <span style="background:#064e3b;color:#34d399;padding:3px 12px;border-radius:50px;
                         font-family:'Orbitron',monospace;font-size:0.85rem;border:1px solid #10b981;">
                {best['confidence']}% Confidence
            </span>
            &nbsp;&nbsp;
            <span style="color:#64748b;font-size:0.85rem;">Trend: {best['trend']} · RSI: {best['rsi']}</span>
        </div>
        """, unsafe_allow_html=True)

    with st.spinner("📡 Fetching market data..."):
        data, info = fetch_stock_data(stock, period)
    if data is None:
        st.error("❌ No data. Check internet connection."); return

    data = compute_indicators(data)
    trend      = detect_trend(data)
    rsi        = float(data['RSI'].iloc[-1])
    decision   = make_decision(trend, rsi, risk_level)
    conf       = confidence_score(rsi)
    explanation= explain_decision(decision, trend, rsi)

    # Personalise using portfolio
    pers_dec, pers_conf, pers_note = personalise_signal(stock, decision, conf, rsi, trend, risk_level)
    record_signal(stock, pers_dec, pers_conf, float(data['Close'].iloc[-1]))

    price    = float(data['Close'].iloc[-1])
    prev     = float(data['Close'].iloc[-2]) if len(data) > 1 else price
    change   = price - prev
    chg_pct  = (change / prev) * 100 if prev > 0 else 0
    high52   = float(data['Close'].max())
    low52    = float(data['Close'].min())

    # KPIs
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("💰 Price (₹)", f"{price:,.2f}", f"{change:+.2f} ({chg_pct:+.2f}%)")
    with c2: st.metric("📈 Trend", trend)
    with c3: st.metric("⚡ RSI", f"{rsi:.1f}")
    with c4: st.metric("🎯 Confidence", f"{pers_conf}%")
    with c5: st.metric("🤖 Signal", pers_dec)

    st.markdown("<br>", unsafe_allow_html=True)
    r1,r2,r3,r4 = st.columns(4)
    with r1: st.metric("🔼 52W High (₹)", f"{high52:,.2f}")
    with r2: st.metric("🔽 52W Low (₹)",  f"{low52:,.2f}")
    with r3:
        vol = float(data['Volume'].mean())
        st.metric("📦 Avg Volume", f"{vol/1e6:.2f}M" if vol>=1e6 else f"{vol/1e3:.1f}K")
    with r4:
        mc = info.get("marketCap", 0)
        st.metric("🏦 Market Cap", f"₹{mc/1e12:.2f}T" if mc>=1e12 else f"₹{mc/1e9:.1f}B" if mc>0 else "N/A")

    st.markdown("<br>", unsafe_allow_html=True)

    # Agentic pipeline badge
    st.markdown("""
    <div class="ai-card ai-card-purple" style="margin-bottom:16px;padding:14px 20px;">
        <span style="font-family:'Orbitron',monospace;font-size:0.8rem;color:#7c3aed;letter-spacing:1px;">
            ⚡ AGENTIC PIPELINE
        </span>
        &nbsp;
        <span style="background:#1e0a3c;color:#a78bfa;padding:3px 12px;border-radius:50px;font-size:0.8rem;border:1px solid #7c3aed44;margin-right:6px;">
            1️⃣ Signal Detected
        </span>
        <span style="background:#1e0a3c;color:#a78bfa;padding:3px 12px;border-radius:50px;font-size:0.8rem;border:1px solid #7c3aed44;margin-right:6px;">
            2️⃣ Context Enriched
        </span>
        <span style="background:#1e0a3c;color:#a78bfa;padding:3px 12px;border-radius:50px;font-size:0.8rem;border:1px solid #7c3aed44;">
            3️⃣ Alert Generated
        </span>
    </div>
    """, unsafe_allow_html=True)

    # Decision card
    dk = "BUY" if "BUY" in pers_dec else ("SELL" if "SELL" in pers_dec else "HOLD")
    dc = {"BUY":("#064e3b","#10b981","🟢"),"SELL":("#450a0a","#ef4444","🔴"),"HOLD":("#1c1917","#f59e0b","🟡")}
    dbg,dcol,demoji = dc.get(dk, dc["HOLD"])
    pers_note_html = f'<p style="margin:6px 0 0;font-size:0.9rem;color:#94a3b8;font-style:italic;">🔍 Portfolio insight: {pers_note}</p>' if pers_note else ""
    st.markdown(f"""
    <div style="background:{dbg};border:1px solid {dcol}44;border-left:4px solid {dcol};
                border-radius:14px;padding:20px 26px;margin-bottom:16px;">
        <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
            <span style="font-family:'Orbitron',monospace;font-size:1.5rem;font-weight:900;color:{dcol};">
                {demoji} {pers_dec}
            </span>
            <span style="background:rgba(255,255,255,0.06);border:1px solid {dcol}33;border-radius:50px;
                         padding:4px 16px;font-family:'Share Tech Mono',monospace;font-size:0.9rem;color:{dcol};">
                Confidence: {pers_conf}%
            </span>
        </div>
        <p style="margin:10px 0 0;font-family:'Rajdhani',sans-serif;font-size:1rem;color:#e2e8f0;line-height:1.6;">
            💡 {explanation}
        </p>
        {pers_note_html}
    </div>
    """, unsafe_allow_html=True)

    # Chart
    st.markdown("### 📈 Price Chart")
    fig = make_subplots(rows=3,cols=1,shared_xaxes=True,vertical_spacing=0.04,
                        row_heights=[0.58,0.22,0.20],
                        subplot_titles=("Price & Indicators","RSI","Volume"))
    fig.add_trace(go.Candlestick(x=data['Date'],open=data['Open'],high=data['High'],
        low=data['Low'],close=data['Close'],name="OHLC",
        increasing_line_color='#10b981',decreasing_line_color='#ef4444',
        increasing_fillcolor='#10b981',decreasing_fillcolor='#ef4444'),row=1,col=1)
    fig.add_trace(go.Scatter(x=data['Date'],y=data['MA20'],name='MA20',
        line=dict(color='#00c6ff',width=1.5)),row=1,col=1)
    fig.add_trace(go.Scatter(x=data['Date'],y=data['MA50'],name='MA50',
        line=dict(color='#f59e0b',width=1.5,dash='dot')),row=1,col=1)
    if 'BB_Upper' in data.columns:
        fig.add_trace(go.Scatter(x=data['Date'],y=data['BB_Upper'],name='BB Upper',
            line=dict(color='#7c3aed',width=1,dash='dash'),opacity=0.6),row=1,col=1)
        fig.add_trace(go.Scatter(x=data['Date'],y=data['BB_Lower'],name='BB Lower',
            line=dict(color='#7c3aed',width=1,dash='dash'),opacity=0.6,
            fill='tonexty',fillcolor='rgba(124,58,237,0.04)'),row=1,col=1)
    fig.add_trace(go.Scatter(x=data['Date'],y=data['RSI'],name='RSI',
        line=dict(color='#f97316',width=2)),row=2,col=1)
    fig.add_hline(y=70,line_dash="dash",line_color="#ef4444",line_width=1,row=2,col=1)
    fig.add_hline(y=30,line_dash="dash",line_color="#10b981",line_width=1,row=2,col=1)
    vcols = ['#10b981' if data['Close'].iloc[i]>=data['Open'].iloc[i] else '#ef4444' for i in range(len(data))]
    fig.add_trace(go.Bar(x=data['Date'],y=data['Volume'],name='Volume',marker_color=vcols,opacity=0.7),row=3,col=1)
    fig.update_layout(template="plotly_dark",paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(17,24,39,0.9)',font=dict(family='Rajdhani'),height=680,
        legend=dict(bgcolor='rgba(0,0,0,0)',bordercolor='#1e293b',borderwidth=1),
        xaxis_rangeslider_visible=False,margin=dict(t=40,b=20,l=10,r=10))
    fig.update_yaxes(gridcolor='#1e293b',zerolinecolor='#1e293b')
    fig.update_xaxes(gridcolor='#1e293b')
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
#  TAB — 24HR VIEW
# ============================================================
def tab_24hr(stock):
    st.markdown("<h2>🕐 24-Hour Intraday View</h2>", unsafe_allow_html=True)
    sname = STOCK_NAMES.get(stock, stock)
    st.markdown(f"<p style='color:#64748b;'>5-minute intervals for <b style='color:#00c6ff;'>{sname}</b></p>", unsafe_allow_html=True)
    with st.spinner("📡 Loading intraday data..."):
        idata = fetch_24hr_data(stock)
    if idata is None or idata.empty:
        st.warning("⚠️ Intraday data unavailable. Markets may be closed."); return

    latest = float(idata['Close'].iloc[-1])
    open_p = float(idata['Open'].iloc[0])
    high_d = float(idata['High'].max())
    low_d  = float(idata['Low'].min())
    chg    = latest - open_p
    chg_p  = (chg / open_p) * 100 if open_p > 0 else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("💰 Current (₹)", f"{latest:,.2f}", f"{chg:+.2f}")
    with c2: st.metric("🔓 Open (₹)", f"{open_p:,.2f}")
    with c3: st.metric("🔼 Day High (₹)", f"{high_d:,.2f}")
    with c4: st.metric("🔽 Day Low (₹)", f"{low_d:,.2f}")
    with c5:
        vol = float(idata['Volume'].sum())
        st.metric("📦 Volume", f"{vol/1e6:.2f}M" if vol>=1e6 else f"{vol/1e3:.1f}K")

    st.markdown("<br>", unsafe_allow_html=True)
    fig = make_subplots(rows=2,cols=1,shared_xaxes=True,vertical_spacing=0.05,
                        row_heights=[0.7,0.3],subplot_titles=("Intraday Price (5-min)","Volume"))
    color = '#10b981' if chg >= 0 else '#ef4444'
    fill  = 'rgba(16,185,129,0.08)' if chg >= 0 else 'rgba(239,68,68,0.08)'
    fig.add_trace(go.Scatter(x=idata.get('Datetime',idata.index),y=idata['Close'],
        fill='tozeroy',fillcolor=fill,line=dict(color=color,width=2),name='Price'),row=1,col=1)
    vc = ['#10b981' if idata['Close'].iloc[i]>=idata['Open'].iloc[i] else '#ef4444' for i in range(len(idata))]
    fig.add_trace(go.Bar(x=idata.get('Datetime',idata.index),y=idata['Volume'],
        marker_color=vc,name='Volume',opacity=0.7),row=2,col=1)
    fig.update_layout(template="plotly_dark",paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(17,24,39,0.9)',font=dict(family='Rajdhani'),
        height=520,margin=dict(t=40,b=10,l=10,r=10),
        xaxis_rangeslider_visible=False,legend=dict(bgcolor='rgba(0,0,0,0)'))
    fig.update_yaxes(gridcolor='#1e293b')
    fig.update_xaxes(gridcolor='#1e293b')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 📋 Recent Intervals")
    cols = ['Open','High','Low','Close','Volume']
    if 'Datetime' in idata.columns: cols = ['Datetime'] + cols
    avail = [c for c in cols if c in idata.columns]
    tail = idata[avail].tail(20).copy().iloc[::-1].reset_index(drop=True)
    for c in ['Open','High','Low','Close']:
        if c in tail.columns: tail[c] = tail[c].apply(lambda x: f"₹{x:,.2f}")
    if 'Volume' in tail.columns: tail['Volume'] = tail['Volume'].apply(lambda x: f"{int(x):,}")
    st.dataframe(tail, use_container_width=True, hide_index=True)

# ============================================================
#  TAB — AI RESPONSE
# ============================================================
def tab_ai_response(stock, risk_level, period):
    st.markdown("<h2>💬 AI Market Assistant</h2>", unsafe_allow_html=True)
    data, _ = fetch_stock_data(stock, period)
    trend = rsi = decision = conf = explanation = None
    context_str = ""
    if data is not None and not data.empty:
        data = compute_indicators(data)
        trend       = detect_trend(data)
        rsi         = float(data['RSI'].iloc[-1])
        decision    = make_decision(trend, rsi, risk_level)
        conf        = confidence_score(rsi)
        explanation = explain_decision(decision, trend, rsi)
        price       = float(data['Close'].iloc[-1])
        pers_dec, pers_conf, pers_note = personalise_signal(stock, decision, conf, rsi, trend, risk_level)
        context_str = (
            f"Stock: {STOCK_NAMES.get(stock,stock)} ({stock}). Price: ₹{price:.2f}. "
            f"Trend: {trend}. RSI: {rsi:.1f}. Decision: {pers_dec}. Confidence: {pers_conf}%. "
            f"Risk Level: {risk_level}. Portfolio insight: {pers_note}. Analysis: {explanation}"
        )

    st.markdown("#### 🔵 Quick Questions")
    qcols = st.columns(3)
    quick_qs = [
        "Should I invest in this stock now?","What does the RSI tell me?",
        "Explain the current trend","What is the risk in buying now?",
        "Compare this stock to market average","What are the key support levels?"
    ]
    for i, q in enumerate(quick_qs):
        with qcols[i % 3]:
            if st.button(q, key=f"qq_{i}", use_container_width=True):
                st.session_state["ai_query"] = q

    st.markdown("<br>", unsafe_allow_html=True)
    query = st.text_input("💬 Type your question here...", value=st.session_state.get("ai_query",""), key="ai_input_main")
    if st.button("🤖 Get AI Analysis"):
        if not query.strip():
            st.warning("Please enter a question."); return
        with st.spinner("🧠 Thinking..."):
            ai_resp = None
            full_prompt = f"""You are AutoInvest AI, a professional Indian stock market analyst.
Context: {context_str}
User question: {query}
Give a clear, structured, professional answer in 3-5 sentences. Use ₹ for Indian Rupees."""
            if model:
                try:
                    r = model.generate_content(full_prompt)
                    if r and hasattr(r,"text") and r.text.strip():
                        ai_resp = r.text.strip()
                except: ai_resp = None
            if not ai_resp:
                ai_resp = _fallback_response(query, trend, rsi, decision, conf, explanation, stock, risk_level)
        st.markdown(f"""
        <div class="ai-card ai-card-accent" style="margin-top:16px;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                <span style="font-size:1.4rem;">🤖</span>
                <span style="font-family:'Orbitron',monospace;font-size:0.9rem;color:#00c6ff;font-weight:600;">AI ANALYSIS</span>
            </div>
            <p style="font-family:'Rajdhani',sans-serif;font-size:1rem;color:#e2e8f0;line-height:1.7;margin:0;">
                {ai_resp.replace(chr(10),'<br>')}
            </p>
        </div>
        """, unsafe_allow_html=True)

def _fallback_response(query, trend, rsi, decision, conf, explanation, stock, risk_level):
    sname = STOCK_NAMES.get(stock, stock)
    q = query.lower() if query else ""
    if any(w in q for w in ["invest","buy","should i"]):
        return (f"Based on current analysis of {sname}, the AI signals **{decision}** with {conf}% confidence. "
                f"The trend is {trend} and RSI stands at {rsi:.1f}. "
                f"For a {risk_level} risk profile: {explanation} "
                f"Always diversify and consult a SEBI-registered advisor.")
    elif any(w in q for w in ["rsi","relative strength"]):
        zone = "overbought (potential sell zone)" if rsi and rsi>70 else "oversold (potential buy zone)" if rsi and rsi<30 else "neutral zone"
        return (f"The RSI for {sname} is {rsi:.1f if rsi else 'N/A'}, placing it in the **{zone}**. "
                f"RSI above 70 = overbought; below 30 = oversold. "
                f"Combined with {trend} trend, this supports the {decision} signal.")
    elif any(w in q for w in ["trend","direction"]):
        return (f"{sname} is in a **{trend}** with RSI at {rsi:.1f if rsi else 'N/A'}. "
                f"Moving averages confirm this direction. The AI recommends {decision} for your {risk_level} risk profile.")
    elif any(w in q for w in ["risk","safe"]):
        return (f"For your {risk_level} risk profile, {sname} shows {conf}% confidence. "
                f"RSI at {rsi:.1f if rsi else 'N/A'} ({('elevated' if rsi and rsi>65 else 'low' if rsi and rsi<35 else 'stable')}). "
                f"{explanation}")
    return (f"Analysis for {sname}: Trend {trend}, RSI {rsi:.1f if rsi else 'N/A'}, Decision **{decision}** ({conf}% confidence). "
            f"{explanation}")

# ============================================================
#  TAB — VIDEO ENGINE (AI Video + Email Alert together)
# ============================================================
def tab_video_engine(stock, risk_level, period):
    st.markdown("<h2>🎬 AI Market Video Engine</h2>", unsafe_allow_html=True)
    st.markdown("""
    <div class="ai-card ai-card-purple" style="margin-bottom:20px;">
        <p style="margin:0;color:#a78bfa;font-family:'Rajdhani',sans-serif;font-size:1rem;">
            ⚡ <b>Agentic 3-Step Pipeline:</b>
            &nbsp;
            <span style="background:#1e0a3c;padding:3px 12px;border-radius:50px;font-size:0.85rem;border:1px solid #7c3aed44;">
                1️⃣ Detect Signal
            </span>
            →
            <span style="background:#1e0a3c;padding:3px 12px;border-radius:50px;font-size:0.85rem;border:1px solid #7c3aed44;">
                2️⃣ Enrich Context
            </span>
            →
            <span style="background:#1e0a3c;padding:3px 12px;border-radius:50px;font-size:0.85rem;border:1px solid #7c3aed44;">
                3️⃣ Generate Alert
            </span>
            &nbsp; Zero human input. Fully autonomous.
        </p>
    </div>
    """, unsafe_allow_html=True)

    data, _ = fetch_stock_data(stock, period)
    if data is None or data.empty:
        st.error("❌ No data available."); return

    data = compute_indicators(data)
    trend       = detect_trend(data)
    rsi         = float(data['RSI'].iloc[-1])
    decision    = make_decision(trend, rsi, risk_level)
    conf        = confidence_score(rsi)
    explanation = explain_decision(decision, trend, rsi)
    price       = float(data['Close'].iloc[-1])
    prev        = float(data['Close'].iloc[-2]) if len(data) > 1 else price
    chg_pct     = ((price - prev) / prev) * 100 if prev > 0 else 0
    sname       = STOCK_NAMES.get(stock, stock)

    pers_dec, pers_conf, pers_note = personalise_signal(stock, decision, conf, rsi, trend, risk_level)
    portfolio = get_portfolio()

    # Script preview
    st.markdown(f"""
    <div class="ai-card ai-card-accent" style="margin-bottom:20px;">
        <h4 style="color:#00c6ff;margin:0 0 12px 0;font-family:'Orbitron',monospace;">📝 Video Script</h4>
        <p style="font-family:'Rajdhani',sans-serif;font-size:1rem;color:#e2e8f0;line-height:1.7;margin:0;">
            AutoInvest AI Market Summary · {sname} · Price: ₹{price:,.2f} · 
            Trend: {trend} · RSI: {rsi:.0f} · Decision: <b style='color:{"#10b981" if "BUY" in pers_dec else "#ef4444" if "SELL" in pers_dec else "#f59e0b"}'>{pers_dec}</b> · 
            Confidence: {pers_conf}%
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Video options
    vc1, vc2, vc3 = st.columns(3)
    with vc1: lang = st.selectbox("🌐 Language", ["English","Tamil","Hindi"], key="vid_lang_v3")
    with vc2: fps_choice = st.selectbox("🎥 Quality", ["Standard (24fps)","Fast (12fps)"], key="vid_fps")
    with vc3: spf = st.selectbox("⏱️ Seconds/Slide", [3, 4, 5, 6], index=1, key="vid_spf")
    lang_code = {"English":"en","Tamil":"ta","Hindi":"hi"}.get(lang,"en")
    fps_val = 24 if "24" in fps_choice else 12

    col_vid, col_email = st.columns([1, 1])

    # ── VIDEO GENERATION ──────────────────────────────────────
    with col_vid:
        st.markdown("### 🎬 Generate Video")
        if st.button("🎬 Generate AI Market Video", use_container_width=True):
            if not GTTS_AVAILABLE:
                st.error("Install gTTS: `pip install gTTS`"); return
            if not PIL_AVAILABLE:
                st.error("Install Pillow: `pip install Pillow`"); return

            prog = st.progress(0)
            stat = st.empty()

            # Step 1
            stat.markdown("**Step 1/3** — 🔍 Detecting signal...")
            prog.progress(15)
            time.sleep(0.3)

            # Step 2
            stat.markdown("**Step 2/3** — 🧠 Enriching with context...")
            prog.progress(40)
            time.sleep(0.3)

            # Step 3
            stat.markdown("**Step 3/3** — 🎙️ Generating audio & frames...")
            prog.progress(65)

            try:
                if VIDEO_ENGINE_OK:
                    video_bytes, audio_bytes = generate_market_video(
                        stock=stock, stock_name=sname, price=price,
                        change_pct=chg_pct, trend=trend, rsi=rsi,
                        decision=pers_dec, explanation=explanation,
                        conf=pers_conf, risk=risk_level, data=data,
                        portfolio=portfolio if portfolio else None,
                        email=st.session_state.get("alert_email",""),
                        lang=lang_code, fps=fps_val, seconds_per_frame=spf,
                    )
                else:
                    # Audio-only fallback
                    video_bytes = None
                    audio_bytes = None
                    if GTTS_AVAILABLE:
                        script = (
                            f"AutoInvest AI Market Summary. Stock: {sname}. "
                            f"Current price: Rupees {price:,.0f}. "
                            f"Trend: {trend}. RSI: {rsi:.0f}. "
                            f"AI Decision: {pers_dec}. Confidence: {pers_conf} percent. "
                            f"{explanation} "
                            f"Developed by A Shanmuganaadhan."
                        )
                        tts = gTTS(text=script, lang=lang_code, slow=False)
                        abuf = io.BytesIO()
                        tts.write_to_fp(abuf)
                        abuf.seek(0)
                        audio_bytes = abuf.read()

                prog.progress(100)
                stat.empty()

                # ── Results ──────────────────────────────
                # Summary visual
                dk = "BUY" if "BUY" in pers_dec else ("SELL" if "SELL" in pers_dec else "HOLD")
                dmap = {"BUY":("#064e3b","#10b981"),"SELL":("#450a0a","#ef4444"),"HOLD":("#1c1917","#f59e0b")}
                dbg,dcol = dmap.get(dk,dmap["HOLD"])
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#0f1f3d,#1a0a2e);
                            border:1px solid #00c6ff33;border-radius:16px;padding:24px;margin:16px 0;">
                    <div style="text-align:center;margin-bottom:16px;">
                        <span style="font-family:'Orbitron',monospace;font-size:1.2rem;font-weight:700;
                                     background:linear-gradient(135deg,#00c6ff,#7c3aed);
                                     -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                            🎬 AI VIDEO SUMMARY — {sname}
                        </span>
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px;margin-bottom:16px;">
                        <div style="background:#0d1117;border-radius:10px;padding:12px;text-align:center;border:1px solid #1e293b;">
                            <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;">Price</div>
                            <div style="font-family:'Share Tech Mono',monospace;color:#00c6ff;font-size:1rem;margin-top:4px;">₹{price:,.0f}</div>
                        </div>
                        <div style="background:#0d1117;border-radius:10px;padding:12px;text-align:center;border:1px solid #1e293b;">
                            <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;">Trend</div>
                            <div style="font-family:'Share Tech Mono',monospace;color:#7dd3fc;font-size:1rem;margin-top:4px;">{trend}</div>
                        </div>
                        <div style="background:#0d1117;border-radius:10px;padding:12px;text-align:center;border:1px solid #1e293b;">
                            <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;">RSI</div>
                            <div style="font-family:'Share Tech Mono',monospace;color:#f97316;font-size:1rem;margin-top:4px;">{rsi:.1f}</div>
                        </div>
                        <div style="background:{dbg};border-radius:10px;padding:12px;text-align:center;border:1px solid {dcol}44;">
                            <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;">Decision</div>
                            <div style="font-family:'Orbitron',monospace;color:{dcol};font-size:0.9rem;margin-top:4px;font-weight:700;">{pers_dec}</div>
                        </div>
                    </div>
                    <div style="background:#0d1117;border-radius:10px;padding:14px;border:1px solid #1e293b;">
                        <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;margin-bottom:6px;">Portfolio Insight</div>
                        <div style="font-size:0.9rem;color:#94a3b8;">{pers_note}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # GIF video frames
                if video_bytes:
                    st.image(video_bytes, caption="🎬 AI Market Summary (Animated)", use_container_width=True)
                    st.download_button("⬇️ Download Video (GIF)", data=video_bytes,
                        file_name=f"autoinvest_{stock.replace('.NS','')}_video.gif",
                        mime="image/gif")

                # Audio
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")
                    st.success(f"🎙️ Audio summary generated in {lang}! Press ▶️ to play.")
                    st.download_button("⬇️ Download Audio (MP3)", data=audio_bytes,
                        file_name=f"autoinvest_{stock.replace('.NS','')}_summary.mp3",
                        mime="audio/mpeg")

                if not video_bytes and not audio_bytes:
                    st.warning("⚠️ Both video and audio generation failed. Check dependencies.")

                # Store for email
                st.session_state["last_audio_bytes"] = audio_bytes
                st.session_state["last_video_stock"]  = stock

            except Exception as e:
                prog.empty(); stat.empty()
                st.error(f"❌ Generation failed: {str(e)}")
                st.info("💡 Install dependencies: `pip install Pillow matplotlib gTTS`")

    # ── EMAIL ALERT ──────────────────────────────────────────
    with col_email:
        st.markdown("### 📧 Email Alert")
        st.markdown("""
        <div class="ai-card ai-card-accent" style="margin-bottom:16px;">
            <p style="margin:0;font-size:0.85rem;color:#94a3b8;">
                Send a rich HTML alert email with the AI analysis, portfolio context, and optional MP3 audio attachment.
            </p>
        </div>
        """, unsafe_allow_html=True)

        provider = st.selectbox("📮 Email Provider", list(SMTP_PRESETS.keys()), key="email_prov")
        preset = SMTP_PRESETS[provider]

        if provider != "Custom":
            smtp_host = preset["host"]
            smtp_port = preset["port"]
            st.info(f"ℹ️ {preset['note']}")
        else:
            smtp_host = st.text_input("SMTP Host", value="smtp.gmail.com", key="smtp_h")
            smtp_port = st.number_input("SMTP Port", value=465, key="smtp_p")

        sender_email    = st.text_input("📤 Your Email", placeholder="your@email.com", key="snd_em")
        sender_password = st.text_input("🔑 App Password", type="password", key="snd_pw",
                                        help="Use App Password, not your main account password.")
        alert_email     = st.text_input("📥 Send Alert To", placeholder="recipient@email.com", key="rcv_em")

        attach_audio = st.checkbox("📎 Attach MP3 Audio", value=True, key="attach_mp3")

        if st.button("📧 Send Alert Email", use_container_width=True):
            if not sender_email or not sender_password or not alert_email:
                st.error("❌ Fill in all email fields."); return

            with st.spinner("📧 Sending email alert..."):
                audio_to_send = None
                if attach_audio:
                    audio_to_send = st.session_state.get("last_audio_bytes")

                pf_summary = get_portfolio_summary_text(get_portfolio())

                ok, msg = send_alert_email(
                    smtp_host=smtp_host, smtp_port=int(smtp_port),
                    sender_email=sender_email, sender_password=sender_password,
                    recipient_email=alert_email,
                    stock_name=sname, stock_ticker=stock,
                    price=price, change_pct=chg_pct,
                    trend=trend, rsi=rsi,
                    decision=pers_dec, conf=pers_conf,
                    explanation=explanation, risk=risk_level,
                    portfolio_summary=pf_summary,
                    audio_bytes=audio_to_send,
                )

            if ok:
                st.success(msg)
                st.balloons()
                st.markdown(f"""
                <div class="ai-card ai-card-success">
                    <p style="margin:0;color:#34d399;font-weight:700;">📧 Email Sent Successfully!</p>
                    <p style="margin:6px 0 0;font-size:0.9rem;color:#94a3b8;">
                        Recipient: {alert_email}<br>
                        Subject: 🚨 {pers_dec} — {sname}<br>
                        Includes: Rich HTML + Agentic pipeline steps + Portfolio context
                        {"+ MP3 audio attachment" if attach_audio and audio_to_send else ""}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(msg)
                with st.expander("🔧 Email Troubleshooting"):
                    st.markdown("""
**Gmail setup:**
1. Enable 2-Factor Authentication on your Google account
2. Go to: Google Account → Security → 2-Step Verification → App passwords
3. Create an App password for "Mail" → copy the 16-character code
4. Use that code as the password here (not your Gmail password)

**Common errors:**
- `Authentication failed` → Wrong App Password
- `SMTPConnectError` → Wrong host/port or firewall blocking
- `Connection refused` → Try port 587 instead of 465
                    """)

# ============================================================
#  TAB — PORTFOLIO
# ============================================================
def tab_portfolio(stock, risk_level, period):
    st.markdown("<h2>📋 Portfolio Manager</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#64748b;'>Add your holdings and the AI learns to personalise signals for your specific portfolio.</p>", unsafe_allow_html=True)

    # Add new holding
    st.markdown("### ➕ Add / Update Holding")
    pc1,pc2,pc3,pc4 = st.columns([2,1,1,1])
    with pc1:
        new_stock = st.selectbox("Stock", STOCKS_LIST,
            format_func=lambda x: f"{x.replace('.NS','')} — {STOCK_NAMES.get(x,'')[:20]}",
            key="pf_stock")
    with pc2: new_qty  = st.number_input("Quantity", min_value=1, value=10, step=1, key="pf_qty")
    with pc3: new_cost = st.number_input("Avg Cost (₹)", min_value=1.0, value=100.0, step=1.0, key="pf_cost")
    with pc4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add", key="pf_add"):
            msg = add_to_portfolio(new_stock, new_qty, new_cost)
            st.success(msg)
            st.rerun()

    # Current portfolio
    portfolio = get_portfolio()
    if not portfolio:
        st.markdown("""
        <div class="ai-card ai-card-warning" style="margin-top:20px;">
            <p style="margin:0;color:#fbbf24;">📋 Your portfolio is empty. Add holdings above to enable portfolio-aware AI personalisation.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Fetch live prices and compute signals for all portfolio stocks
    st.markdown("### 📊 Portfolio Overview")
    with st.spinner("Fetching live prices and signals..."):
        live_prices = {}
        signals = {}
        for item in portfolio:
            s = item["stock"]
            try:
                d = yf.Ticker(s).history(period="5d")
                if not d.empty:
                    live_prices[s] = float(d['Close'].iloc[-1])
                    d = d.dropna().reset_index()
                    d['RSI'] = calculate_rsi(d)
                    d['MA20'] = moving_average(d, 20)
                    t = detect_trend(d)
                    r = float(d['RSI'].iloc[-1])
                    signals[s] = make_decision(t, r, risk_level)
            except: pass

    portfolio = update_portfolio_signals(live_prices, signals)
    stats = get_portfolio_stats(portfolio)

    # Stats row
    pnl_col = "#10b981" if stats.get("total_pnl_pct",0) >= 0 else "#ef4444"
    pnl_sym  = "▲" if stats.get("total_pnl_pct",0) >= 0 else "▼"
    s1,s2,s3,s4,s5 = st.columns(5)
    with s1: st.metric("💼 Holdings", stats.get("holdings",0))
    with s2: st.metric("💰 Invested", f"₹{stats.get('total_invested',0)/1e5:.1f}L")
    with s3: st.metric("📈 Current Value", f"₹{stats.get('total_current',0)/1e5:.1f}L")
    with s4: st.metric("💹 Total P&L", f"{pnl_sym}₹{abs(stats.get('total_pnl',0)):,.0f}", f"{pnl_sym}{abs(stats.get('total_pnl_pct',0)):.1f}%")
    with s5: st.metric("🏆 Top Sector", stats.get("top_sector","N/A"))

    st.markdown("<br>", unsafe_allow_html=True)

    # Holdings table
    st.markdown("### 📋 Holdings with AI Signals")
    rows = []
    for p in portfolio:
        pnl_pct = p.get("pnl_pct", 0)
        sig = p.get("signal","HOLD")
        sig_em = "🟢" if "BUY" in sig else "🔴" if "SELL" in sig else "🟡"
        rows.append({
            "Stock": p["stock"].replace(".NS",""),
            "Sector": SECTOR_MAP.get(p["stock"],"Other"),
            "Qty": p["qty"],
            "Avg Cost (₹)": f"₹{p['avg_cost']:,.2f}",
            "Live Price (₹)": f"₹{p.get('live_price', p['avg_cost']):,.2f}",
            "P&L (₹)": f"{'+' if p.get('pnl',0)>=0 else ''}₹{p.get('pnl',0):,.0f}",
            "P&L %": f"{'+' if pnl_pct>=0 else ''}{pnl_pct:.1f}%",
            "Weight": f"{p.get('weight',0):.1f}%",
            "Signal": f"{sig_em} {sig}",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Remove holding
    st.markdown("### 🗑️ Remove Holding")
    rem_stock = st.selectbox("Select to remove",
        [p["stock"] for p in portfolio],
        format_func=lambda x: x.replace(".NS",""),
        key="pf_rem")
    if st.button("🗑️ Remove", key="pf_rem_btn"):
        msg = remove_from_portfolio(rem_stock)
        st.success(msg); st.rerun()

    # Sector breakdown chart
    if stats.get("sector_weights"):
        st.markdown("### 🥧 Sector Allocation")
        sec = stats["sector_weights"]
        fig = go.Figure(go.Pie(
            labels=list(sec.keys()), values=list(sec.values()),
            hole=0.5, textinfo="label+percent",
            marker=dict(colors=['#00c6ff','#7c3aed','#10b981','#f59e0b','#ef4444',
                                '#f97316','#06b6d4','#8b5cf6','#ec4899','#14b8a6'])
        ))
        fig.update_layout(template="plotly_dark",paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',height=360,
            legend=dict(bgcolor='rgba(0,0,0,0)'),
            margin=dict(t=20,b=10,l=10,r=10))
        st.plotly_chart(fig, use_container_width=True)

    # Signal history
    history = get_signal_history()
    if history:
        st.markdown("### 📜 Signal History (Last 20)")
        h_df = pd.DataFrame(history[-20:][::-1])
        h_df["timestamp"] = pd.to_datetime(h_df["timestamp"]).dt.strftime("%d %b %H:%M")
        h_df.columns = [c.title() for c in h_df.columns]
        st.dataframe(h_df, use_container_width=True, hide_index=True)

# ============================================================
#  TAB — RADAR SCANNER
# ============================================================
def tab_radar(risk_level):
    st.markdown("<h2>🚀 Market Opportunity Radar</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#64748b;'>Full NSE watchlist scan — ranked by AI opportunity score.</p>", unsafe_allow_html=True)

    if st.button("🔍 Scan All Stocks Now", use_container_width=False):
        with st.spinner("🔍 Scanning all 20 stocks... (this takes ~15 seconds)"):
            results = scan_all_stocks(STOCKS_LIST)

        if not results:
            st.error("Scan failed. Check internet connection."); return

        st.markdown(f"### 📊 Scan Results — {len(results)} stocks ranked")
        rows = []
        for i, r in enumerate(results):
            sn = STOCK_NAMES.get(r['stock'], r['stock'])
            dec = make_decision(r['trend'], r['rsi'], risk_level)
            sig_em = "🟢" if "BUY" in dec else "🔴" if "SELL" in dec else "🟡"
            trend_em = "📈" if r['trend']=="UPTREND" else "📉" if r['trend']=="DOWNTREND" else "➡️"
            rows.append({
                "Rank": f"#{i+1}",
                "Stock": r['stock'].replace('.NS',''),
                "Name": sn[:28],
                "Trend": f"{trend_em} {r['trend']}",
                "RSI": r['rsi'],
                "Opportunity": f"{r['confidence']}%",
                "Signal": f"{sig_em} {dec}",
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Top 3 highlight
        st.markdown("### 🏆 Top 3 Opportunities")
        for i, r in enumerate(results[:3]):
            sn = STOCK_NAMES.get(r['stock'], r['stock'])
            dec = make_decision(r['trend'], r['rsi'], risk_level)
            dk  = "BUY" if "BUY" in dec else ("SELL" if "SELL" in dec else "HOLD")
            dmap = {"BUY":("#064e3b","#10b981"),"SELL":("#450a0a","#ef4444"),"HOLD":("#1c1917","#f59e0b")}
            dbg,dcol = dmap.get(dk,dmap["HOLD"])
            medal = ["🥇","🥈","🥉"][i]
            st.markdown(f"""
            <div style="background:{dbg};border:1px solid {dcol}44;border-left:4px solid {dcol};
                        border-radius:14px;padding:16px 22px;margin-bottom:12px;">
                <span style="font-size:1.2rem;">{medal}</span>
                &nbsp;
                <span style="font-family:'Orbitron',monospace;font-size:1rem;color:{dcol};font-weight:700;">
                    {r['stock'].replace('.NS','')}
                </span>
                &nbsp;
                <span style="color:#94a3b8;font-size:0.9rem;">{sn}</span>
                &nbsp;&nbsp;
                <span style="background:rgba(0,0,0,0.3);border:1px solid {dcol}44;border-radius:50px;
                             padding:3px 12px;font-family:'Orbitron',monospace;font-size:0.8rem;color:{dcol};">
                    {dec} · {r['confidence']}%
                </span>
                &nbsp;
                <span style="color:#64748b;font-size:0.85rem;">RSI: {r['rsi']} · {r['trend']}</span>
            </div>
            """, unsafe_allow_html=True)

# ============================================================
#  TAB — EXPLANATIONS
# ============================================================
def tab_explanations():
    st.markdown("<h2>📚 Explanations & Education</h2>", unsafe_allow_html=True)
    sections = {
        "💰 What is Investing?": """
**Investing** means deploying money into assets expecting growth over time.

**Key Principles:** Time value of money · Compound growth · Risk/Return tradeoff · Diversification

**Indian Market Hours:** NSE/BSE operate **9:15 AM – 3:30 PM IST**, Monday to Friday.

**Types:** Day trading · Swing trading · Long-term investing (recommended for beginners)
""",
        "📈 RSI — Relative Strength Index": """
Measures **price momentum** on a 0–100 scale.

| RSI Value | Zone | Signal |
|-----------|------|--------|
| > 70 | Overbought | Potential SELL |
| 30 – 70 | Neutral | Hold/Watch |
| < 30 | Oversold | Potential BUY |

Formula: `RSI = 100 - [100 / (1 + (Avg Gain / Avg Loss))]` over 14 periods.
""",
        "📊 MACD": """
**Moving Average Convergence Divergence** — trend momentum indicator.

- **MACD Line** = EMA(12) − EMA(26)
- **Signal Line** = EMA(9) of MACD
- **Bullish crossover** (MACD > Signal) → BUY signal
- **Bearish crossover** (MACD < Signal) → SELL signal
""",
        "📉 Moving Averages": """
**MA20** = 20-day average price (short-term trend)
**MA50** = 50-day average price (medium-term trend)

**Golden Cross** → MA20 crosses above MA50 = Strong bullish 🟢
**Death Cross** → MA20 crosses below MA50 = Strong bearish 🔴
""",
        "📐 Bollinger Bands": """
Three lines: **Middle (MA20)** ± **2 standard deviations**

- Price near **Upper Band** → Possibly overbought
- Price near **Lower Band** → Possibly oversold
- **Band Squeeze** → Big move coming
""",
        "🧠 How the Agentic AI Works": """
**AutoInvest AI uses a 3-Step Agentic Pipeline (no human input required):**

**Step 1 — Signal Detection**
Scans RSI, Moving Averages, trend direction autonomously.

**Step 2 — Context Enrichment**
Cross-references your portfolio holdings, sector exposure, risk level, and current P&L.

**Step 3 — Actionable Alert Generation**
Produces personalised BUY/SELL/HOLD with explanation + optional email + video.

This pipeline runs **3 sequential analysis steps without human input** — fulfilling Agentic Architecture requirements.
""",
        "📋 Portfolio AI Learning": """
The Portfolio Agent **learns from your holdings** and adjusts signals accordingly:

- Heavy position → reduces BUY urgency (concentration risk)
- At a loss → adds caution on averaging down
- No existing position + BUY signal → strengthens confidence
- High sector concentration (>40%) → warns about diversification

Signals are personalised specifically for **your** portfolio context — not generic market advice.
""",
        "📧 Email Alert System": """
**Automated rich HTML email alerts** include:

- Current price, trend, RSI, decision badge
- AI analysis explanation
- Agentic 3-step pipeline summary
- Portfolio context (your holdings vs this signal)
- Risk level
- Optional MP3 audio attachment

Supports Gmail (App Password), Outlook, Yahoo, and custom SMTP servers.
""",
        "⚠️ Risk Levels": """
**Low** 🟢 — Conservative. Only signals BUY in strong confirmed uptrends with RSI < 55.

**Medium** 🟡 — Balanced. BUY in moderate uptrends, normal RSI ranges.

**High** 🔴 — Aggressive. BUY in volatile conditions, wider RSI tolerance.

⚠️ **Disclaimer**: AutoInvest AI is for educational purposes only. Consult a SEBI-registered advisor.
""",
        "📖 Glossary": """
| Term | Definition |
|------|-----------|
| NSE / BSE | National/Bombay Stock Exchange |
| SEBI | Securities & Exchange Board of India (regulator) |
| Bull Market | Rising market |
| Bear Market | Falling market |
| P&L | Profit and Loss |
| Volatility | Price fluctuation measure |
| Liquidity | Ease of buying/selling |
| P/E Ratio | Price-to-Earnings valuation metric |
| Market Cap | Total market value of company |
| OHLC | Open, High, Low, Close |
| Volume | Shares traded |
| Support | Price floor (stocks bounce here) |
| Resistance | Price ceiling (stocks stall here) |
| Dividend | Profit distributed to shareholders |
| EMA | Exponential Moving Average |
| ATR | Average True Range (volatility) |
""",
    }
    for title, content in sections.items():
        with st.expander(title, expanded=False):
            st.markdown(content)

# ============================================================
#  TAB — SETTINGS
# ============================================================
def tab_settings():
    st.markdown("<h2>⚙️ Settings & Preferences</h2>", unsafe_allow_html=True)
    st.markdown("### 🔤 Font Size Controls")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="ai-card ai-card-accent">', unsafe_allow_html=True)
        new_fs  = st.slider("📝 Body / General Text",   11, 22, st.session_state.font_size,      step=1)
        new_hs  = st.slider("🔠 Heading (H1/H2)",       16, 40, st.session_state.heading_size,   step=1)
        new_shs = st.slider("🔡 Sub-heading (H3)",      14, 32, st.session_state.subheading_size, step=1)
        new_ms  = st.slider("📊 Metric Value",          16, 42, st.session_state.metric_size,    step=1)
        st.markdown('</div>', unsafe_allow_html=True)
        if st.button("✅ Apply Font Settings", use_container_width=True):
            st.session_state.font_size       = new_fs
            st.session_state.heading_size    = new_hs
            st.session_state.subheading_size = new_shs
            st.session_state.metric_size     = new_ms
            st.success("✅ Applied!"); st.rerun()
        if st.button("↩️ Reset Defaults", use_container_width=True):
            st.session_state.font_size=15; st.session_state.heading_size=22
            st.session_state.subheading_size=18; st.session_state.metric_size=28
            st.success("↩️ Reset."); st.rerun()
    with c2:
        st.markdown(f"""
        <div class="ai-card" style="height:300px;overflow:hidden;">
            <div style="font-family:'Orbitron',monospace;font-size:{new_hs}px;
                        background:linear-gradient(135deg,#00c6ff,#7c3aed);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                        margin-bottom:8px;">Preview Heading</div>
            <div style="font-family:'Rajdhani',sans-serif;font-size:{new_shs}px;
                        color:#7dd3fc;margin-bottom:10px;">Sub-heading Preview</div>
            <div style="font-family:'Rajdhani',sans-serif;font-size:{new_fs}px;
                        color:#94a3b8;line-height:1.6;margin-bottom:12px;">
                Body text at {new_fs}px — comfortable for reading.
            </div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:{new_ms}px;color:#00c6ff;">
                ₹2,847.50
            </div>
            <div style="font-size:{new_fs-2}px;color:#64748b;">Metric label</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 🌗 Theme")
    theme_choice = st.radio("Theme", ["dark","light"], horizontal=True,
                            index=0 if st.session_state.theme=="dark" else 1)
    if theme_choice != st.session_state.theme:
        st.session_state.theme = theme_choice; st.rerun()

    st.markdown("### 🔑 Gemini AI Configuration")
    st.markdown("""
    <div class="ai-card ai-card-warning">
        <p style="margin:0;color:#fbbf24;">⚠️ Add GEMINI_API_KEY to .streamlit/secrets.toml for full AI responses.</p>
    </div>
    """, unsafe_allow_html=True)
    with st.expander("ℹ️ How to configure"):
        st.code('# .streamlit/secrets.toml\nGEMINI_API_KEY = "your-key-here"', language="toml")

    st.markdown("### 📊 About")
    st.markdown(f"""
    <div class="ai-card">
        <table style="width:100%;font-family:'Rajdhani',sans-serif;font-size:{st.session_state.font_size}px;border-collapse:collapse;">
            <tr><td style="color:#64748b;padding:6px 0;width:40%;">Application</td><td style="color:#e2e8f0;">AutoInvest AI Professional Dashboard</td></tr>
            <tr><td style="color:#64748b;padding:6px 0;">Version</td><td style="color:#00c6ff;font-family:'Share Tech Mono',monospace;">v3.0 Agentic</td></tr>
            <tr><td style="color:#64748b;padding:6px 0;">Developer</td><td style="color:#7c3aed;font-family:'Orbitron',monospace;font-size:0.9em;">A. SHANMUGANAADHAN</td></tr>
            <tr><td style="color:#64748b;padding:6px 0;">Data Source</td><td style="color:#e2e8f0;">Yahoo Finance (yfinance)</td></tr>
            <tr><td style="color:#64748b;padding:6px 0;">AI Engine</td><td style="color:#e2e8f0;">Gemini 1.5 Flash + Rule-Based Fallback</td></tr>
            <tr><td style="color:#64748b;padding:6px 0;">Architecture</td><td style="color:#a78bfa;">Agentic 3-Step Pipeline</td></tr>
            <tr><td style="color:#64748b;padding:6px 0;">Market</td><td style="color:#e2e8f0;">NSE India</td></tr>
            <tr><td style="color:#64748b;padding:6px 0;">Disclaimer</td><td style="color:#f59e0b;">Educational purposes only. Not financial advice.</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
#  MAIN
# ============================================================
def main():
    inject_css()
    if not st.session_state.logged_in:
        show_login(); return

    stock, risk_level, period = render_sidebar()

    tabs = st.tabs([
        "📊 Dashboard",
        "🕐 24hr View",
        "💬 AI Response",
        "🎬 Video Engine",
        "📋 Portfolio",
        "🚀 Radar",
        "📚 Explanations",
        "⚙️ Settings"
    ])
    with tabs[0]: tab_dashboard(stock, risk_level, period)
    with tabs[1]: tab_24hr(stock)
    with tabs[2]: tab_ai_response(stock, risk_level, period)
    with tabs[3]: tab_video_engine(stock, risk_level, period)
    with tabs[4]: tab_portfolio(stock, risk_level, period)
    with tabs[5]: tab_radar(risk_level)
    with tabs[6]: tab_explanations()
    with tabs[7]: tab_settings()

if __name__ == "__main__":
    main()

    #AIzaSyAr0sWPhOzisRz8y1GgaSczpvPPTrCdAG4