# ============================================================
#  agents/portfolio_agent.py
#  Portfolio Learning & Signal Personalisation Agent
#  Developer: A. SHANMUGANAADHAN
#
#  The agent:
#    - Stores and learns from user's portfolio
#    - Weights signals based on portfolio exposure
#    - Personalises BUY/SELL/HOLD based on portfolio context
#    - Identifies concentration risk, sector overlap
# ============================================================

import json
import pandas as pd
import numpy as np
from typing import Optional
import streamlit as st


# ─────────────────────────────────────────────────────────────
#  PORTFOLIO STORAGE (Streamlit session-based, persists per session)
# ─────────────────────────────────────────────────────────────

PORTFOLIO_KEY = "user_portfolio_v2"
HISTORY_KEY   = "signal_history_v2"

SECTOR_MAP = {
    "TCS.NS":        "IT",
    "INFY.NS":       "IT",
    "WIPRO.NS":      "IT",
    "HCLTECH.NS":    "IT",
    "TECHM.NS":      "IT",
    "RELIANCE.NS":   "Energy",
    "ADANIPORTS.NS": "Infrastructure",
    "HDFCBANK.NS":   "Finance",
    "ICICIBANK.NS":  "Finance",
    "SBIN.NS":       "Finance",
    "BAJFINANCE.NS": "Finance",
    "HINDUNILVR.NS": "FMCG",
    "ITC.NS":        "FMCG",
    "SUNPHARMA.NS":  "Pharma",
    "DRREDDY.NS":    "Pharma",
    "TATAMOTORS.NS": "Auto",
    "MARUTI.NS":     "Auto",
    "TATASTEEL.NS":  "Metal",
    "JSWSTEEL.NS":   "Metal",
    "ONGC.NS":       "Energy",
    "NTPC.NS":       "Energy",
    "POWERGRID.NS":  "Energy",
    "BHARTIARTL.NS": "Telecom",
    "NESTLEIND.NS":  "FMCG",
    "ASIANPAINT.NS": "Consumer",
    "TITAN.NS":      "Consumer",
    "ULTRACEMCO.NS": "Cement",
    "GRASIM.NS":     "Cement",
    "M&M.NS":        "Auto",
    "EICHERMOT.NS":  "Auto",
}


def _get_portfolio() -> list[dict]:
    return st.session_state.get(PORTFOLIO_KEY, [])


def _save_portfolio(portfolio: list[dict]):
    st.session_state[PORTFOLIO_KEY] = portfolio


def get_portfolio() -> list[dict]:
    return _get_portfolio()


def add_to_portfolio(stock: str, qty: int, avg_cost: float) -> str:
    """Add or update a stock in the user's portfolio."""
    portfolio = _get_portfolio()
    for item in portfolio:
        if item["stock"] == stock:
            # Update: recalculate average cost
            total_qty  = item["qty"] + qty
            total_cost = (item["qty"] * item["avg_cost"]) + (qty * avg_cost)
            item["qty"]      = total_qty
            item["avg_cost"] = round(total_cost / total_qty, 2)
            _save_portfolio(portfolio)
            return f"Updated {stock}: {total_qty} shares @ ₹{item['avg_cost']}"

    portfolio.append({
        "stock":    stock,
        "qty":      qty,
        "avg_cost": round(avg_cost, 2),
        "sector":   SECTOR_MAP.get(stock, "Other"),
        "signal":   "HOLD",
        "weight":   0.0,
    })
    _save_portfolio(portfolio)
    return f"Added {stock}: {qty} shares @ ₹{avg_cost}"


def remove_from_portfolio(stock: str) -> str:
    portfolio = _get_portfolio()
    portfolio = [p for p in portfolio if p["stock"] != stock]
    _save_portfolio(portfolio)
    return f"Removed {stock} from portfolio."


def update_portfolio_signals(live_prices: dict[str, float],
                              signals: dict[str, str]) -> list[dict]:
    """
    Update each portfolio item with latest price, P&L, and AI signal.
    Also recalculates portfolio weights.
    """
    portfolio = _get_portfolio()
    if not portfolio:
        return []

    total_value = 0.0
    for item in portfolio:
        s = item["stock"]
        lp = live_prices.get(s, item["avg_cost"])
        item["live_price"]  = round(lp, 2)
        item["pnl"]         = round((lp - item["avg_cost"]) * item["qty"], 2)
        item["pnl_pct"]     = round(((lp - item["avg_cost"]) / item["avg_cost"]) * 100, 2)
        item["signal"]      = signals.get(s, "HOLD")
        item["market_value"]= round(lp * item["qty"], 2)
        total_value += item["market_value"]

    for item in portfolio:
        item["weight"] = round((item["market_value"] / total_value) * 100, 2) if total_value > 0 else 0

    _save_portfolio(portfolio)
    return portfolio


# ─────────────────────────────────────────────────────────────
#  PERSONALISED SIGNAL
# ─────────────────────────────────────────────────────────────

def personalise_signal(
    stock: str,
    base_decision: str,
    base_conf: int,
    rsi: float,
    trend: str,
    risk_level: str,
) -> tuple[str, int, str]:
    """
    Adjust the base AI decision using portfolio context.

    Logic:
    - If the user already holds heavy position → reduce BUY urgency
    - If user has no position and signal is BUY → strengthen signal
    - If user is at a loss on this stock → add caution note
    - Sector concentration risk → add warning

    Returns:
        (personalised_decision, adjusted_confidence, personalisation_note)
    """
    portfolio = _get_portfolio()
    if not portfolio:
        return base_decision, base_conf, "No portfolio data. Signal is based on market indicators only."

    # Find if user holds this stock
    holding = next((p for p in portfolio if p["stock"] == stock), None)
    total_val = sum(p.get("market_value", p["avg_cost"] * p["qty"]) for p in portfolio)
    sector = SECTOR_MAP.get(stock, "Other")
    sector_weight = sum(
        p.get("weight", 0) for p in portfolio
        if SECTOR_MAP.get(p["stock"], "Other") == sector
    )

    notes = []
    adjusted_conf = base_conf
    adjusted_dec  = base_decision

    dec_key = "BUY" if "BUY" in base_decision else ("SELL" if "SELL" in base_decision else "HOLD")

    if holding:
        weight    = holding.get("weight", 0)
        pnl_pct   = holding.get("pnl_pct", 0)
        live_price = holding.get("live_price", holding["avg_cost"])
        avg_cost   = holding["avg_cost"]

        # Already heavy holder → soften BUY
        if dec_key == "BUY" and weight > 20:
            adjusted_dec  = "HOLD"
            adjusted_conf = max(40, adjusted_conf - 15)
            notes.append(f"You already hold {weight:.1f}% of your portfolio in this stock. Adding more increases concentration risk.")

        # At a profit → can afford to hold or take partial profit on SELL
        elif dec_key == "SELL" and pnl_pct > 15:
            notes.append(f"You are up {pnl_pct:.1f}% on this position (avg ₹{avg_cost:,.2f}). Consider taking partial profits.")
            adjusted_conf = min(95, adjusted_conf + 5)

        # At a loss → add caution on further buying
        elif dec_key == "BUY" and pnl_pct < -10:
            notes.append(f"⚠️ You are currently at a loss of {abs(pnl_pct):.1f}% on this position. Averaging down carries risk.")
            adjusted_conf = max(40, adjusted_conf - 10)

        else:
            notes.append(f"You hold {holding['qty']} shares at avg ₹{avg_cost:,.2f} (P&L: {'+' if pnl_pct>=0 else ''}{pnl_pct:.1f}%).")

    else:
        # No existing position
        if dec_key == "BUY":
            notes.append(f"You do not currently hold {stock.replace('.NS','')}. This could be a new entry opportunity.")
            adjusted_conf = min(95, adjusted_conf + 5)
        else:
            notes.append(f"You do not hold {stock.replace('.NS','')} in your portfolio.")

    # Sector concentration
    if sector_weight > 40:
        notes.append(f"⚠️ Sector alert: Your {sector} exposure is {sector_weight:.1f}% of portfolio — consider diversification.")

    # Risk-level adjustment
    if risk_level == "Low" and dec_key in ["BUY", "STRONG BUY"] and rsi > 60:
        adjusted_dec  = "HOLD"
        adjusted_conf = max(40, adjusted_conf - 12)
        notes.append("For your Low risk profile, RSI above 60 is too elevated for a new entry.")

    personalisation_note = " ".join(notes) if notes else "Signal aligns with your portfolio profile."

    return adjusted_dec, adjusted_conf, personalisation_note


# ─────────────────────────────────────────────────────────────
#  PORTFOLIO ANALYTICS
# ─────────────────────────────────────────────────────────────

def get_portfolio_summary_text(portfolio: list[dict]) -> str:
    """Build a human-readable portfolio summary for email alerts."""
    if not portfolio:
        return "No portfolio holdings configured."

    lines = []
    for p in portfolio:
        pnl  = p.get("pnl", 0)
        pnl_pct = p.get("pnl_pct", 0)
        sig  = p.get("signal", "HOLD")
        lines.append(
            f"• {p['stock'].replace('.NS','')} — "
            f"{p['qty']} shares @ avg ₹{p['avg_cost']:,.2f} | "
            f"Signal: {sig} | P&L: {'+' if pnl>=0 else ''}₹{pnl:,.0f} ({'+' if pnl_pct>=0 else ''}{pnl_pct:.1f}%)"
        )
    return "\n".join(lines)


def get_portfolio_stats(portfolio: list[dict]) -> dict:
    """Compute aggregate portfolio statistics."""
    if not portfolio:
        return {}

    total_invested = sum(p["avg_cost"] * p["qty"] for p in portfolio)
    total_current  = sum(p.get("market_value", p["avg_cost"] * p["qty"]) for p in portfolio)
    total_pnl      = total_current - total_invested
    total_pnl_pct  = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    buy_count  = sum(1 for p in portfolio if "BUY"  in p.get("signal", ""))
    sell_count = sum(1 for p in portfolio if "SELL" in p.get("signal", ""))
    hold_count = len(portfolio) - buy_count - sell_count

    sectors = {}
    for p in portfolio:
        sec = SECTOR_MAP.get(p["stock"], "Other")
        sectors[sec] = sectors.get(sec, 0) + p.get("weight", 0)

    top_sector = max(sectors, key=sectors.get) if sectors else "N/A"

    return {
        "total_invested":  round(total_invested, 2),
        "total_current":   round(total_current,  2),
        "total_pnl":       round(total_pnl,       2),
        "total_pnl_pct":   round(total_pnl_pct,   2),
        "holdings":        len(portfolio),
        "buy_signals":     buy_count,
        "sell_signals":    sell_count,
        "hold_signals":    hold_count,
        "top_sector":      top_sector,
        "sector_weights":  sectors,
    }


def record_signal(stock: str, decision: str, conf: int, price: float):
    """Record signal history for learning / backtesting."""
    history = st.session_state.get(HISTORY_KEY, [])
    history.append({
        "timestamp": pd.Timestamp.now().isoformat(),
        "stock":     stock,
        "decision":  decision,
        "conf":      conf,
        "price":     price,
    })
    # Keep last 100 signals
    st.session_state[HISTORY_KEY] = history[-100:]


def get_signal_history() -> list[dict]:
    return st.session_state.get(HISTORY_KEY, [])