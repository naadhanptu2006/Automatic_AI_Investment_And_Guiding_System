# ============================================================
#  agents/radar_agent.py
#  Market Opportunity Radar Agent for AutoInvest AI
#  Developer: A. SHANMUGANAADHAN
# ============================================================

import yfinance as yf
import pandas as pd
import numpy as np
from utils.indicators import calculate_rsi, detect_trend


def find_best_stock(stocks_list: list[str]) -> dict | None:
    """
    Scan multiple stocks and identify the highest-opportunity stock.

    Scoring logic:
        - RSI in 30–50 range (buy zone approach) → maximum score
        - UPTREND with moderate RSI → bonus
        - Penalty for overbought (RSI > 70) or downtrend

    Args:
        stocks_list: List of Yahoo Finance ticker symbols.

    Returns:
        Dict with keys: 'stock', 'confidence', 'trend', 'rsi'
        or None if all scans fail.
    """
    best = None
    best_score = -999

    for symbol in stocks_list:
        try:
            data = yf.Ticker(symbol).history(period="1mo")
            if data is None or data.empty or len(data) < 10:
                continue

            data = data.dropna().reset_index()
            rsi   = calculate_rsi(data)
            trend = detect_trend(data)

            if rsi.empty:
                continue

            latest_rsi = float(rsi.iloc[-1])

            # ---- Scoring ----
            score = 0

            # RSI scoring: sweet spot is 35–55 (approaching buy zone from neutral)
            if latest_rsi < 30:
                score += 80   # Oversold — strong buy signal
            elif latest_rsi < 40:
                score += 70   # Near oversold
            elif latest_rsi < 50:
                score += 55   # Below neutral — bullish lean
            elif latest_rsi < 60:
                score += 30   # Neutral
            elif latest_rsi < 70:
                score += 10   # Approaching overbought
            else:
                score -= 20   # Overbought — penalise

            # Trend scoring
            if trend == "UPTREND":
                score += 25
            elif trend == "SIDEWAYS":
                score += 5
            else:
                score -= 15   # Downtrend penalty

            # Volume check (optional bonus)
            try:
                avg_vol = data['Volume'].mean()
                last_vol = data['Volume'].iloc[-1]
                if last_vol > avg_vol * 1.2:
                    score += 10  # Above-average volume supports the move
            except Exception:
                pass

            if score > best_score:
                best_score = score
                # Map raw score to confidence percentage (clamp 40–95)
                conf = max(40, min(95, int(40 + (score / 120) * 55)))
                best = {
                    'stock':      symbol,
                    'confidence': conf,
                    'trend':      trend,
                    'rsi':        round(latest_rsi, 1),
                    'score':      score
                }

        except Exception:
            continue

    return best


def scan_all_stocks(stocks_list: list[str]) -> list[dict]:
    """
    Scan all stocks and return a ranked list of opportunities.

    Returns:
        List of dicts, sorted by opportunity score (descending).
        Each dict: {'stock', 'confidence', 'trend', 'rsi', 'score'}
    """
    results = []

    for symbol in stocks_list:
        try:
            data = yf.Ticker(symbol).history(period="1mo")
            if data is None or data.empty or len(data) < 10:
                continue

            data = data.dropna().reset_index()
            rsi_series = calculate_rsi(data)
            trend      = detect_trend(data)

            if rsi_series.empty:
                continue

            latest_rsi  = float(rsi_series.iloc[-1])
            latest_price = float(data['Close'].iloc[-1])
            prev_price   = float(data['Close'].iloc[-2]) if len(data) > 1 else latest_price
            change_pct   = ((latest_price - prev_price) / prev_price) * 100 if prev_price > 0 else 0

            # Same scoring as find_best_stock
            score = 0
            if latest_rsi < 30:    score += 80
            elif latest_rsi < 40:  score += 70
            elif latest_rsi < 50:  score += 55
            elif latest_rsi < 60:  score += 30
            elif latest_rsi < 70:  score += 10
            else:                  score -= 20

            if trend == "UPTREND":      score += 25
            elif trend == "SIDEWAYS":   score += 5
            else:                       score -= 15

            conf = max(40, min(95, int(40 + (score / 120) * 55)))

            results.append({
                'stock':      symbol,
                'confidence': conf,
                'trend':      trend,
                'rsi':        round(latest_rsi, 1),
                'price':      round(latest_price, 2),
                'change_pct': round(change_pct, 2),
                'score':      score
            })

        except Exception:
            continue

    return sorted(results, key=lambda x: x['score'], reverse=True)