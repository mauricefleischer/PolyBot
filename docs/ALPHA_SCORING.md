# Alpha Score 2.0

The **Alpha Score** (0-100) is the primary metric PolyBot uses to grade a market signal. Unlike the "Whale Score" (which rates a *user*), the Alpha Score rates a *specific position* (e.g., "YES on Trump").

It answers the question: **"How strong is the smart money conviction on this specific outcome?"**

---

## 1. The Formula

The Alpha Score is a weighted sum of four components:

$$ Alpha = Base + Quality + Freshness + SmartShort $$

### Component 1: Base Conviction (Log-Volume)
We look at the total USD volume wagered by tracked whales on this outcome.
*   **Formula**: $10 \times \log_{10}(\text{Volume})$
*   **Scale**:
    *   $1,000 Volume → 30 points
    *   $10,000 Volume → 40 points
    *   $100,000 Volume → 50 points
*   *Why Log Scale?* The difference between $1k and $10k matters more than $100k vs $110k.

### Component 2: Quality Multiplier
Volume is useless if it comes from bad traders ("dumb money"). We adjust the effective volume based on the **Trade-Weighted Average Whale Score** of the participants.

*   **Formula**: $\text{Multiplier} = \frac{\text{AvgWhaleScore}}{50}$
*   **Impact**:
    *   **ELITE Whales (Score 90)**: Multiplier = 1.8x. Their $10k counts as $18k.
    *   **WEAK Whales (Score 30)**: Multiplier = 0.6x. Their $10k counts as $6k.

### Component 3: Freshness Decay
Information has a half-life. A signal generated 2 weeks ago is "stale" because the market has likely already priced it in.

*   **Decay Rate**: -0.5 points for every hour since the *last* whale entry.
*   **Floor**: Max penalty is -20 points.
*   **Actionable Window**: The score is highest immediately after a new whale enters.

### Component 4: Smart Short Bonus
This is a contrarian indicator. If we see whales taking a position against a massive retail "bagholder" crowd.

*   **Condition**:
    1.  Market Price < 0.10 (Retail thinks it's a "lottery ticket")
    2.  Whales are betting "NO" (Selling) or holding "NO".
    3.  Whale Volume > $5,000.
*   **Bonus**: **+15 points**.
*   *Why?* Betting against retail delusions is historically the most profitable strategy in prediction markets.

---

## 2. Score Interpretation

| Alpha Score | Rating | Meaning | Action |
| :--- | :--- | :--- | :--- |
| **80 - 100** | **GOD MODE** | Massive volume from Elite whales + Fresh. | **Max Bet Size** |
| **70 - 79** | **HIGH** | Strong consensus. | **Standard Size** |
| **50 - 69** | **MEDIUM** | Good signal, but maybe stale or low volume. | **Half Size** |
| **< 50** | **LOW** | Insufficient conviction or stale. | **Pass / Watch** |

---

## 3. Consensus Strength

The Alpha Score is calculated entirely in `aggregator.py`. It is re-calculated every time the bot polls for new positions (default: 30s). This means the score is dynamic—it will rise if a new whale enters, and fall slowly over time as the "Freshness" decays.
