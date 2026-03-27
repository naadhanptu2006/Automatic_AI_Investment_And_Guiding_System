# AutoInvest AI - Autonomous Investment Intelligence System



Overview
AutoInvest AI is an **Agentic AI-powered investment assistant** designed for retail investors.  
It transforms raw stock market data into **actionable insights (BUY / SELL / HOLD)** using a multi-step autonomous pipeline.

---

Problem Statement
Retail investors often rely on:
- Tips and social media  
- Lack of technical knowledge  

This leads to:
- ❌ Poor decision making  
- ❌ Missed opportunities  
- ❌ High risk exposure  

---

Solution:
AutoInvest AI builds an **autonomous AI agent** that:

✔ Detects market signals  
✔ Enriches them with context  
✔ Generates actionable decisions  

---

Agentic Architecture:

The system follows a **3-step pipeline**:

1️.Signal Detection
- Fetch stock data using `yfinance`
- Calculate:
  - RSI (Relative Strength Index)
  - Moving Average
  - Trend Detection  

---

2️.Context Enrichment
- Combines multiple indicators  
- Determines market condition:
  - Bullish   
  - Bearish  
  - Neutral  

---

3.Decision Generation
- Generates:
  - BUY  
  - SELL   
  - HOLD   

- Provides:
  - Confidence Score  
  - Explanation  

=> This process runs **without human intervention**

---

Features:

-  **Market Opportunity Radar**  
  Scans multiple stocks and finds best opportunity  

-  **Technical Analysis Engine**  
  RSI, trend detection, moving averages  

-  **AI Assistant (Market ChatGPT)**  
  Explains decisions in simple language  

-  **AI Video Summary**  
  Converts analysis into voice-based explanation  

-  **Confidence Scoring**  
  Shows reliability of decisions  

---

##  Tech Stack

- Python  
- Streamlit  
- yfinance  
- Plotly  
- Google Gemini API  
- gTTS  
- Pillow  

---

