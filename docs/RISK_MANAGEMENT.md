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
In prediction markets, the market price $p_{market}$ is often biased. If the market says a candidate has a 60% chance, but the real probability is 55%, a naive Kelly bettor would bet too big and bleed value.

### The Solution: Calibration
We do not use likelihood derived from price directly. We calculate a **calibrated probability** ($p_{real}$) based on micro-structure research (Wolfers 2004) and our own Alpha consensus.

---

## 2. Risk Engine Logic (`risk_engine.py`)

Every time a signal is generated, the Risk Engine runs it through this decision tree:

### Step 1: Mode Selection
Is this a "Yield Play" (Safe Parking)?
*   **Trigger**: Price $\ge$ `YieldTriggerPrice` (Default 0.85) AND at least `YieldMinWhales` (Default 3) separate whales occupy the position.
*   **Logic**: High-priced positions backed by multiple smart whales are often mispriced arbitrage opportunities or nearly resolved events.
*   **Action**: **YIELD MODE** (See Section 4).
*   **Else**: **SPECULATION MODE** (Proceed to Step 2).

---

### Step 2: Speculation Mode (The Kelly Path)

If we are speculating, we must rigorously calculate our edge.

#### A. FLB Probability Calibration
We adjust the market probability ($p_{market}$) based on the **Favorite-Longshot Bias** (Wolfers-Zitzewitz J-Curve).

| Zone | Price Range | Adjustment | Rationale |
| :--- | :--- | :--- | :--- |
| **Lottery** | $p < 0.05$ | $p_{real} = p \times 0.7$ | Retail overpays 30% for "lottery tickets". |
| **Hope** | $0.05 \le p < 0.15$ | $p_{real} = p \times 0.9$ | Moderate overpricing (-10%). |
| **Efficient** | $0.15 \le p \le 0.90$ | No Change | Market is generally efficient here. |
| **Favorite** | $p > 0.90$ | $p_{real} = p + 0.01$ | Retail under-bets sure things (+1% edge). |

#### B. Alpha Boost
If our proprietary **Alpha Score** is $\ge$ 70 (Strong Consensus), we credit the signal with insider knowledge.
*   **Bonus**: $p_{real} = p_{real} + 0.05$ (Add 5% probability).
*   **Safety Cap**: $p_{real}$ is capped at **0.85**. We never assume >85% certainty in speculation mode.

#### C. Confidence Dampener ($D$)
We calculate the raw Kelly fraction, then scale it down based on the **Average Whale Score** of the participants.

| Consensus Tier | Avg Whale Score | Dampener ($D$) |
| :--- | :--- | :--- |
| **ELITE** | $\ge 80$ | **1.0x** (Full Size) |
| **PRO** | $60 - 79$ | **0.5x - 1.0x** (Linear Interpolation) |
| **MIXED** | $50 - 59$ | **0.25x - 0.5x** (Linear Interpolation) |
| **WEAK** | $< 50$ | **0.25x** (Floor) |

#### D. Final Sizing Formula

$$ \text{Stake} \% = \text{Kelly}(p_{real}) \times D \times \text{KellyMultiplier} $$

*   **KellyMultiplier**: User setting (Default 0.25x for "Quarter Kelly").
*   **Max Risk Cap**: Hard limit per trade (Default 5%).

---

## 3. Example Calculation

**Scenario**:
*   Market: "Will TikTok be banned?"
*   Price: **0.10** (10¢) → Odds = 9:1 ($b=9$)
*   Whale Consensus: 3 Whales, Avg Score = **85** (ELITE)
*   Alpha Score: **72** (High)

**1. Calibration**: Price is in "Hope Zone" (0.10).
$$ p_{real} = 0.10 \times 0.9 = 0.09 $$

**2. Alpha Boost**: Score > 70.
$$ p_{real} = 0.09 + 0.05 = 0.14 $$

**3. Kelly Formula**:
$$ f^* = \frac{9(0.14) - 0.86}{9} = \frac{1.26 - 0.86}{9} = \frac{0.40}{9} \approx 4.4\% $$

**4. Sizing**:
*   Dampener ($D$) = 1.0 (Elite).
*   Multiplier ($M$) = 0.25.
$$ \text{Bet} = 4.4\% \times 1.0 \times 0.25 = \mathbf{1.1\%} \text{ of Bankroll} $$

---

## 4. Yield Mode (The "Savings Account")

Yield Mode overrides Kelly for high-probability "yield farming" bets.

*   **Logic**: When `Price >= 0.85` and `Whales >= 3`, we assume the event is concluding.
*   **Sizing**: Fixed percentage allocation.
*   **Formula**:
    $$ \text{Size} = \min(\text{YieldFixedPct}, \text{MaxConcentration}) $$
*   **Defaults** (User Configurable):
    *   `YieldFixedPct`: 10%
    *   `MaxConcentration`: 20%
    *   `YieldMinWhales`: 3

*Why?* Kelly is too volatile for 90% probability bets (it would suggest betting 50%+ of bankroll). Yield Mode keeps size consistent and safe.
