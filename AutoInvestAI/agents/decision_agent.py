# ============================================================
#  agents/decision_agent.py
#  AI Decision Engine for AutoInvest AI
#  Developer: A. SHANMUGANAADHAN
# ============================================================


def make_decision(trend: str, rsi: float, risk_level: str = "Medium") -> str:
    """
    Generate a BUY / SELL / HOLD decision based on trend, RSI and risk level.

    Args:
        trend      : One of 'UPTREND', 'DOWNTREND', 'SIDEWAYS'.
        rsi        : Current RSI value (0–100).
        risk_level : 'Low', 'Medium', or 'High'.

    Returns:
        Decision string: 'STRONG BUY', 'BUY', 'HOLD', 'SELL', 'STRONG SELL'.
    """
    try:
        rsi = float(rsi)

        # ---- Low Risk (conservative) ----
        if risk_level == "Low":
            if trend == "UPTREND" and rsi < 55:
                return "BUY"
            elif trend == "DOWNTREND" or rsi > 72:
                return "SELL"
            else:
                return "HOLD"

        # ---- Medium Risk (balanced) ----
        elif risk_level == "Medium":
            if trend == "UPTREND" and rsi < 65:
                return "BUY" if rsi < 50 else "STRONG BUY" if rsi < 40 else "BUY"
            elif trend == "DOWNTREND" and rsi > 35:
                return "SELL" if rsi > 50 else "STRONG SELL" if rsi > 70 else "SELL"
            elif trend == "SIDEWAYS":
                if rsi < 35:
                    return "BUY"
                elif rsi > 65:
                    return "SELL"
                else:
                    return "HOLD"
            else:
                return "HOLD"

        # ---- High Risk (aggressive) ----
        else:
            if rsi < 30:
                return "STRONG BUY"
            elif rsi < 45 and trend != "DOWNTREND":
                return "BUY"
            elif rsi > 70:
                return "STRONG SELL"
            elif rsi > 60 and trend == "DOWNTREND":
                return "SELL"
            elif trend == "UPTREND":
                return "BUY"
            else:
                return "HOLD"

    except Exception:
        return "HOLD"


def confidence_score(rsi: float) -> int:
    """
    Calculate confidence percentage based on RSI distance from neutral (50).

    Strong signals (RSI far from 50) → higher confidence.
    Neutral RSI → lower confidence.

    Args:
        rsi: Current RSI value.

    Returns:
        Confidence integer (35–95).
    """
    try:
        rsi = float(rsi)
        distance = abs(rsi - 50)

        # Scale: 0 distance → 35%, 50 distance (extreme) → 95%
        raw = 35 + (distance / 50) * 60
        raw = max(35, min(95, raw))
        return int(round(raw))
    except Exception:
        return 50


def explain_decision(decision: str, trend: str, rsi: float) -> str:
    """
    Generate a human-readable explanation for the AI decision.

    Args:
        decision : BUY / SELL / HOLD variant string.
        trend    : UPTREND / DOWNTREND / SIDEWAYS.
        rsi      : Current RSI value.

    Returns:
        Plain-English explanation string.
    """
    try:
        rsi = float(rsi)
        rsi_desc = (
            "overbought territory (RSI > 70), suggesting a potential price reversal or pullback"
            if rsi > 70 else
            "oversold territory (RSI < 30), indicating potential undervaluation and a possible bounce"
            if rsi < 30 else
            f"a neutral zone (RSI ≈ {rsi:.0f}), showing balanced market momentum"
        )

        if "BUY" in decision:
            if rsi < 30:
                return (f"The stock is deeply oversold with RSI at {rsi:.1f}. "
                        f"Combined with the {trend} price action, this presents a high-probability buying opportunity. "
                        f"Consider entering positions with a defined stop-loss below recent support levels.")
            elif rsi < 50:
                return (f"The market is in an {trend} with RSI at {rsi:.1f} — in {rsi_desc}. "
                        f"Momentum indicators support a buying opportunity. "
                        f"Risk is moderate; ensure position sizing aligns with your portfolio allocation.")
            else:
                return (f"Despite slightly elevated RSI at {rsi:.1f}, the {trend} is strong enough to justify entry. "
                        f"Monitor closely for any trend reversal signals and set trailing stop-losses.")

        elif "SELL" in decision:
            if rsi > 70:
                return (f"The stock is in {rsi_desc}. "
                        f"With {trend} price action, profit-taking or reducing exposure is advisable. "
                        f"Wait for RSI to cool below 60 before considering re-entry.")
            else:
                return (f"The {trend} combined with RSI at {rsi:.1f} suggests deteriorating momentum. "
                        f"Consider reducing your position size or setting tight stop-losses to protect capital.")

        else:  # HOLD
            return (f"Mixed signals: {trend} with RSI at {rsi:.1f} ({rsi_desc}). "
                    f"No clear directional edge at this time. "
                    f"It is prudent to hold current positions and wait for a stronger, more decisive signal before acting.")

    except Exception:
        return "Analysis unavailable. Please check the data and try again."