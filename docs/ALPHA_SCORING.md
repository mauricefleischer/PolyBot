# Alpha Score 2.0

The **Alpha Score** (0-100) is the primary metric PolyBot uses to grade a market signal. It replaces the original volume-based scoring with a multi-factor model grounded in behavioral finance research.

It answers the question: **"Does this price movement have characteristics of smart money or retail noise?"**

---

## 1. The Master Formula

The Alpha Score is a composite of a fixed base and 4 distinct sub-factors.

$$ Alpha = \text{Clamp}(0, 100, \text{Base} + \text{FLB} + \text{Momentum} + \text{SmartShort} + \text{Freshness}) $$

### Base Score
*   **Value**: **50**
*   The system assumes a "Neutral" state by default. Evidence adds to or subtracts from this midpoint.

---

## 2. The 4 Sub-Factors

### Factor 1: Favorite-Longshot Bias (FLB) Score
**Source**: Wolfers & Zitzewitz (2004).

We adjust for the proven retail tendency to overpay for longshots (lottery tickets) and underpay for favorites (risk aversion). We divide the current price ($p$) into 4 zones:

| Zone | Price Range | Score Impact | Behavior |
| :--- | :--- | :--- | :--- |
| **Lottery Zone** | $p < 0.05$ | **-40** | Massive retail overpricing. Buying here is negative EV. |
| **Hope Zone** | $0.05 \le p < 0.15$ | **-20** | Moderate overpricing. |
| **Confusion Zone** | $0.15 \le p \le 0.85$ | **0** | Efficiently priced. No edge from FLB. |
| **Favorite Value** | $p > 0.85$ | **+15** | Underpriced. Whales buying here are capturing free value. |

*Note: The negative penalties are scaled by the `longshot_tolerance` setting (default 1.0).*

### Factor 2: Momentum (Anchoring)
**Source**: Technical Analysis / Behavioral Anchoring.

We compare the current price ($p$) to the **7-Day Moving Average** ($MA_{7d}$) fetched from the CLOB API.

$$ Ratio = p / MA_{7d} $$

| Ratio | Condition | Score Impact | Meaning |
| :--- | :--- | :--- | :--- |
| $> 1.05$ | Price > 5% above avg | **+10** | **Breakout**. Price is trending up with conviction. |
| $< 0.95$ | Price > 5% below avg | **-10** | **Falling Knife**. Sentiment is collapsing. |
| $0.95 - 1.05$ | Price roughly equal | **0** | Ranging / No momentum signal. |

*Note: If price history is unavailable, this factor is 0.*

### Factor 3: Smart Short
**Source**: Contrarian Betting Strategy.

Retail bettors suffer from **Desirability Bias** (betting on what they *want* to happen) and **Long Bias** (focusing on "YES" shares). Whales who bet "NO" are often exploiting this inefficiency.

We award a bonus for **"NO"** bets (Shorts), weighted by the sector's retail density:

| Sector | Direction | Score Impact | Rationale |
| :--- | :--- | :--- | :--- |
| **Politics** | NO | **+20** | Highest sentiment bias (e.g., "My candidate will win"). |
| **Sports** | NO | **+20** | Fan loyalty bias. |
| **Entertainment** | NO | **+15** | Pop culture bias. |
| **Finance/Other** | NO | **+10** | More efficient, but still some long bias. |
| **Any** | YES | **0** | No penalty, but no bonus. |

### Factor 4: Freshness (Information Decay)
**Source**: Efficient Market Hypothesis.

Market information decays rapidly. A whale entering *right now* is valuable. A whale who entered 5 days ago has already been priced in.

$$ Freshness = \max(0, 10 - 2 \times \text{DaysSinceEntry}) $$

| Age | Score Impact | Label |
| :--- | :--- | :--- |
| < 24 Hours | **+10** | Fresh Signal |
| 1 Day | **+8** | Recent |
| 2 Days | **+6** | Recent |
| 3 Days | **+4** | Aging |
| > 5 Days | **0** | Stale (No Value) |

---

## 3. Score Interpretation

| Total Score | Rating | Action |
| :--- | :--- | :--- |
| **70 - 100** | **ALPHA** | **Prioritize**. Strong confluence of logic, value, and timing. |
| **40 - 69** | **NEUTRAL** | **Verify**. Likely a standard trade or conflicting signals. |
| **0 - 39** | **LOTTERY** | **Ignore/Filter**. High risk, likely retail bait or falling knife. |

---

## 4. Example Calculation

**Scenario**: "Will Trump win?" (Politics)
*   Current Price: **$0.92**
*   7d Avg Price: **$0.85**
*   Whale Activity: Selling "NO" (which is buying YES) - *Wait, simple YES bet.*
*   Timing: Entered 12 hours ago.

**Calculation**:
1.  **Base**: 50
2.  **FLB**: Price $0.92 > 0.85$ (Favorite Value) → **+15**
3.  **Momentum**: $0.92 / 0.85 = 1.08$ (> 1.05) → **+10** (Breakout)
4.  **Smart Short**: Betting YES → **0**
5.  **Freshness**: 0.5 days old → **+10**

**Total Alpha Score**: $50 + 15 + 10 + 0 + 10 = \mathbf{85}$ (**GOD MODE**)

This signal would trigger a **+5% Alpha Boost** in the Risk Engine's probability estimation.
