# Whale Scoring & Ranking Engine

The **Whale Score** (0-100) rates the skill of an individual wallet. It is the foundation of the entire system—if we track bad whales, our signals will be bad.

The engine uses behavioral finance metrics to separate "Lucky Gamblers" from "Skilled Operators".

---

## 1. The 4 Scoring Pillars (`whale_scoring.py`)

Every wallet is graded on 4 pillars, which are weighted to produce the final score.

### Pillar 1: ROI Performance (35% Weight)
Measures raw profitability, but adjusted for luck.
*   **Metric**: Modified Information Ratio.
*   **Formula**: `Score = Min(100, (Win_Rate * 1) + (ROI % * 0.5))`
*   **Luck Filter**: If `Win_Rate < 40%`, the score is limited. Even if a gambler hits a 100x winner, they don't get a perfect score if they lose 90% of their trades.
*   **Bonus**: **+10 points** if `Total Profit > $50,000` (Proven Scalability).

### Pillar 2: Discipline (25% Weight)
Measures the **Disposition Effect** (Odean, 1998) — the tendency of retail traders to sell winners too early (to lock in gains) and hold losers too long (hoping for a rebound).

*   **Metric**: `Ratio = Avg_Hold_Time_Losers / Avg_Hold_Time_Winners`
*   **Grading**:
    *   **Ratio $\le$ 0.5**: **Score 100**. This trader cuts losers 2x faster than winners. Elite discipline.
    *   **Ratio $\approx$ 1.0**: **Score 50**. Neutral.
    *   **Ratio $\ge$ 2.0**: **Score 0**. This trader is a "Bagholder" (holds losers 2x longer).

### Pillar 3: Precision (20% Weight)
Measures "Sniper" quality vs. "Spray and Pray".
*   **Metric**: **Turnover Index** ($T$) = `Total_Trades / (Active_Positions + 1)`
*   **Logic**:
    *   **$T < 2.0$**: **Score 100** ("Sniper"). Few trades per position. High conviction.
    *   **$T > 10.0$**: **Score 0** ("Churner"). Constantly flipping in and out.
    *   *Exception*: If **ROI Score > 80**, this penalty is bypassed (Profitable HFT is allowed).

### Pillar 4: Timing (20% Weight)
Measures Alpha: Does this wallet move *before* the price moves?
*   **Proxy Metric**: **Price Percentile Entry**.
    *   Since exact market start times are noisy, we use the entry price as a proxy for timing.
*   **Grading**:
    *   **Entry Price < 0.20**: **Score 100** ("Pioneer"). Buying at 10-20 cents implies contrarian early insight.
    *   **Entry Price 0.30 - 0.70**: **Score 50** ("Crowd"). Buying when the outcome is uncertain but popular.
    *   **Entry Price > 0.80**: **Score 0** ("FOMO/Exit Liquidity"). Buying at 90 cents is chasing.

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

The system assigns behavioral tags based on specific sub-scores:

| Tag | Code | Requirement | Meaning |
| :--- | :--- | :--- | :--- |
| **Diamond Hands** | `HLD` | Discipline Score > 90 | Holds winners, cuts losers fast. |
| **Paper Hands** | `DUMP` | Discipline Score < 20 | Panic sells or holds bags. |
| **Sniper** | `PRC` | Precision Score > 90 | Very few trades, high conviction. |
| **Churner** | `CHRN` | Precision Score < 20 | Over-trading / Indecisive. |
| **Pioneer** | `PNIR` | Timing Score > 80 | Enters early (Low price). |
| **Profitable** | `PROF` | ROI Score > 80 | Elite profitability. |
