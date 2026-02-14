# Risk Management & Position Sizing

This document details the **Dynamic Risk Engine** used by PolyBot. The engine determines the optimal bet size for every signal using a combination of the **Fractional Kelly Criterion** and a specialized **Yield Mode** for arbitrage-like opportunities.

---

## 1. The Core Philosophy: "De-Biased Kelly"

The [Kelly Criterion](https://en.wikipedia.org/wiki/Kelly_criterion) is the mathematical formula for maximizing geometric growth of a bankroll.

$$ f^* = \frac{bp - q}{b} $$

Where:
*   $f^*$: Fraction of bankroll to bet
*   $b$: Net odds received (Decimal Odds - 1)
*   $p$: Probability of winning
*   $q$: Probability of losing ($1-p$)

### The Problem with Naive Kelly
In prediction markets, the market price $p_{market}$ is often biased. If the market says Trump has a 60% chance, but the real probability is 55%, a naive Kelly bettor would bet too big and go broke.

### The Solution: Calibration
We do not use the market price as $p$. We calculate a **calibrated probability** ($p_{real}$) based on micro-structure research (Wolfers 2004, Becker 2025).

---

## 2. Risk Engine Logic (`risk_engine.py`)

Every time a signal is generated, the Risk Engine runs it through this decision tree:

### Step 1: Mode Selection
Is this a "Yield Play"?
*   **Condition**: Price $\ge$ 0.85 (85% implied probability) AND at least 3 separate whales occupy the position.
*   **Logic**: If multiple smart whales are holding a position priced at 85c+, it is likely a "free money" arbitrage or a nearly resolved event (e.g. "Will sun rise tomorrow?").
*   **Action**: **YIELD MODE** (See Section 4).
*   **Else**: **SPECULATION MODE** (Proceed to Step 2).

### Step 2: FLB Calibration (Wolfers-Zitzewitz J-Curve)
We adjust for the **Favorite-Longshot Bias**.

*   **Lottery Zone** (Price < 0.05):
    *   Retail loves to overpay for "longshots" (e.g. buying 1c bets that are worth 0c).
    *   **Adjustment**: $p_{real} = p_{market} \times 0.7$ (-30% penalty).
*   **Hope Zone** (0.05 < Price < 0.15):
    *   **Adjustment**: $p_{real} = p_{market} \times 0.9$ (-10% penalty).
*   **Favorite Zone** (Price > 0.90):
    *   Retail hates picking up pennies in front of steamrollers. They underprice high-certainty events.
    *   **Adjustment**: $p_{real} = p_{market} + 0.01$ (+1% bonus).
*   **Efficient Zone** (0.15 - 0.90):
    *   No adjustment.

### Step 3: Alpha Boost
Does the signal imply insider knowledge?
*   If **Alpha Score** $\ge$ 70 (Strong Consensus):
    *   **Adjustment**: $p_{real} = p_{real} + 0.05$ (Add 5% win probability).
    *   *Why?* Proven smart money piling into a bet suggests the market price is lagging the true probability.

### Step 4: Confidence Dampener
We calculate the Kelly fraction using $p_{real}$, then multiply it by a safety factor based on **Whale Quality**.

| Consensus Tier | Avg Whale Score | Dampener ($D$) |
| :--- | :--- | :--- |
| **ELITE** | > 80 | **1.0x** (Full Size) |
| **PRO** | 60 - 79 | **0.5x - 1.0x** (Linear match) |
| **MIXED** | 50 - 59 | **0.25x - 0.5x** (Linear match) |
| **WEAK** | < 50 | **0.25x** (Safety floor) |

$$ FinalSize = Kelly(p_{real}) \times D \times KellyMultiplier $$

*(Note: `KellyMultiplier` is a global user setting, default 0.25).*

---

## 3. Example Calculation

**Scenario**:
*   Market: "Will TikTok be banned in 2024?"
*   Price: **0.10** (10c) -> Odds = 9:1 ($b=9$)
*   Whale Consensus: 3 Whales, Avg Score = **85** (ELITE)
*   Alpha Score: **72** (High)

**1. FLB Calibration**:
Price is in "Hope Zone" (0.10).
$$ p_{real} = 0.10 \times 0.9 = 0.09 $$
*(The real odds are worse than market implies)*

**2. Alpha Boost**:
Alpha Score > 70.
$$ p_{real} = 0.09 + 0.05 = 0.14 $$
*(But our whales know something!)*

**3. Kelly Formula**:
$$ f^* = \frac{9(0.14) - 0.86}{9} = \frac{1.26 - 0.86}{9} = \frac{0.40}{9} \approx 4.4\% $$

**4. Dampener**:
Elite Consensus -> $D = 1.0$.
Global Setting -> $M = 0.25$.

$$ FinalBet = 4.4\% \times 1.0 \times 0.25 = 1.1\% \text{ of Bankroll} $$

---

## 4. Yield Mode (The "Savings Account")

Yield Mode is a safety override for high-probability bets where Kelly would suggest consistently massive sizes (e.g. 40%+ of bankroll).

*   **Goal**: Steady, low-risk compounding without "Gambler's Ruin" risk from one black swan event.
*   **Mechanic**: Replaces dynamic calculation with a **Fixed Percentage**.
*   **Default Config**:
    *   Trigger Price: 0.85
    *   Min Whales: 3
    *   Bet Size: 10% of Bankroll (Hard Cap)
