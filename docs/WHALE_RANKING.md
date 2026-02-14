# Whale Scoring & Ranking Engine

The **Whale Score** (0-100) rates the skill of an individual wallet. It is the foundation of the entire system—if we track bad whales, our signals will be bad.

The engine uses behavioral finance metrics to separate "Lucky Gamblers" from "Skilled Operators".

---

## 1. The 4 Scoring Pillars (`whale_scoring.py`)

Every wallet is graded on 4 pillars, which are weighted to produce the final score.

### Pillar 1: ROI Performance (35% Weight)
Measures raw profitability, but adjusted for luck.
*   **Metric**: Modified Information Ratio.
*   **Formula**: `Score = (Win_Rate * 1) + (ROI % * 0.5)`
*   **Luck Filter**: If a wallet has < 40% Win Rate, their ROI score is capped at 50, even if they hit one massive jackpot. We want consistency, not lottery winners.
*   **Bonus**: +10 points if `Total Profit > $50,000`.

### Pillar 2: Discipline (25% Weight)
Measures the **Disposition Effect** (Odean, 1998) — the tendency of retail traders to sell winners too early (to lock in gains) and hold losers too long (hoping for a rebound).

*   **Ratio**: `Average_Gain_Per_Win / Average_Loss_Per_Loss`.
*   **Grading**:
    *   **Ratio > 1.5**: **Score 100**. This trader lets winners run 1.5x further than their losers. Elite discipline.
    *   **Ratio 1.0**: **Score 50**. Neutral.
    *   **Ratio < 0.5**: **Score 0**. This trader "eats like a bird and poops like an elephant." They take 5% profits but hold 50% bags.

### Pillar 3: Precision (20% Weight)
Measures the "Sharpshooter" quality.
*   **Churn Penalty**: We penalize over-trading. -1 point for every 10 trades over 100 (in the sample window).
*   **Concept**: A whale who makes 5 trades and wins 4 is infinitely more valuable to copy than an algorithmic bot that makes 1,000 trades to net the same profit. We want **clean signals**.

### Pillar 4: Timing (20% Weight)
Measures simple alpha: Does this wallet move *before* the market moves?
*   **Metric**: Average entry timestamp vs. Crowd entry timestamp.
*   **Pioneer Bonus**: Entering >24h before the crowd average = **High Score**.
*   **FOMO Penalty**: Entering during price spikes or <1h before resolution = **Low Score**.

---

## 2. Whale Tiers

Based on the final weighted score, whales are assigned a Tier Tag.

| Tier | Score Range | Description | System Treatment |
| :--- | :--- | :--- | :--- |
| **ELITE** | **80 - 100** | Perfect track record. High discipline. | 100% Weight in Risk Engine. |
| **PRO** | **60 - 79** | Consistent winner. | 75% Weight in Risk Engine. |
| **STD** | **40 - 59** | Average / Noise. | 50% Weight. Signals ignored unless mass consensus. |
| **WEAK** | **< 40** | "Jim Cramer" Tier. | **Counter-Trade Candidates.** |

---

## 3. Performance Tags

The system also assigns behavioral tags to help you understand *how* a whale trades:

*   **PROF**: Highly profitable (> 20% ROI).
*   **PRC** (Precision): High win rate (> 65%).
*   **HLD** (Diamond Hands): Average hold time > 7 days.
*   **DUMP**: Fast dumper / Paper hands (Avg hold < 24h).
*   **CHRN**: High churn (Over-trader).
*   **PNIR** (Pioneer): Early entries.
