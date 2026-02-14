# PolyBot – Consensus Terminal

**PolyBot** is a high-performance market intelligence terminal for [Polymarket](https://polymarket.com). It tracks "Whale" wallets (smart money), aggregates their positions into actionable signals, and calculates optimal bet sizes using a de-biased Kelly Criterion.

![PolyBot Terminal](frontend/public/placeholder_screenshot.png)

---

## 🚀 Key Features

### 1. Whale Tracking & Scoring
We don't just follow big money; we grade it. Every tracked wallet is rated **0–100** based on 4 factors:
*   **Performance**: Are they profitable?
*   **Discipline**: Do they cut losers fast?
*   **Precision**: Do they snipe or spray?
*   **Timing**: Do they enter before the crowd?

👉 **[Deep Dive: Whale Ranking Logic](docs/WHALE_RANKING.md)**

### 2. Alpha Score 2.0
We score every market signal (0-100) using a multi-factor model grounded in behavioral finance:
*   **FLB**: Adjusts for retail "Lottery Ticket" bias (Wolfers 2004).
*   **Momentum**: Detects breakouts vs. 7-day moving average.
*   **Smart Short**: Bonus for betting against popular sentiment (e.g. Politics/Sports).
*   **Freshness**: Time-decay (New signals > Old signals).

👉 **[Deep Dive: Alpha Scoring Math](docs/ALPHA_SCORING.md)**

### 3. Dynamic Risk Engine
We use a **De-Biased Fractional Kelly Criterion** to determine bet size.
*   **Speculation Mode**: Calibrates probability and dampens size based on **Whale Consensus Quality**.
*   **Yield Mode**: Automatically switches to fixed-income style sizing for high-probability arbitrage (>85% odds).

👉 **[Deep Dive: Risk Management & Kelly](docs/RISK_MANAGEMENT.md)**

---

## 🛠️ Installation

### Prerequisites
*   Python 3.9+
*   Node.js 18+
*   Git

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start the API
python -m uvicorn app.main:app --reload --port 8000
```
*API docs available at: http://localhost:8000/docs*

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
*Terminal running at: http://localhost:5173*

---

## ⚙️ Configuration

Create a `.env` file in `backend/` (optional, defaults provided):

```env
# Polygon RPC for ensuring you have USDC balance
POLYGON_RPC_URL="https://polygon-rpc.com"

# Risk Defaults
DEFAULT_KELLY_MULTIPLIER=0.25
DEFAULT_RISK_CAP=0.05
```

---

## 🖥️ Usage Guide

### The Terminal
*   **Signal Table**: Shows live aggregated positions. Sort by **Alpha Score** to find the best trades.
*   **Consensus Bar**: Visualizes the crowd size.
    *   🟪 **Purple**: One or more **ELITE** whales are in this trade.
    *   **Scale**: Larger bar = More wallets.

### Whale Manager
*   Add/Remove wallets to track.
*   View their **Tier** (Elite, Pro, Std, Weak) and **Tags** (e.g., `HLD` = Diamond Hands, `PNIR` = Pioneer).

### Settings
*   **Kelly Multiplier**: Adjust aggression (0.1 = Safe, 1.0 = Degen).
*   **Yield Mode**: Configure trigger price (default 0.85) for safe parking.

---

## 📚 Documentation Index

*   [**Whale Ranking**](docs/WHALE_RANKING.md) - How we grade wallets.
*   [**Alpha Scoring**](docs/ALPHA_SCORING.md) - How we grade signals.
*   [**Risk Management**](docs/RISK_MANAGEMENT.md) - How we size bets.

---

**Disclaimer**: *This software is for educational purposes only. Prediction markets carry financial risk. Never bet money you cannot afford to lose.*
