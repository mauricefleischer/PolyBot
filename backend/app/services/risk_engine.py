"""
De-Biased Kelly Engine — Microstructure-Adjusted Position Sizing.

Replaces naive Kelly (P_market = true probability) with:
  1. FLB-corrected probability calibration (Wolfers 2004)
  2. Optimism Tax adjustment for sentiment-heavy markets (Becker 2025)
  3. Confidence Dampener based on whale quality scores

Usage:
    engine = RiskEngine()
    size, breakdown = engine.calculate_position_size(
        price=0.65,
        alpha_score=75,
        wallet_count=3,
        category="Politics",
        whale_scores=[85, 72, 90],
        user_balance=10000,
        settings=RiskSettings(...)
    )
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class RiskSettings:
    """User-configurable risk parameters."""
    kelly_multiplier: float = 0.25       # Fraction of full Kelly (0.1–1.0)
    max_risk_cap: float = 0.05           # Hard cap per trade (1%–20%)
    max_risk_cap: float = 0.05           # Hard cap per trade (1%–20%)
    yield_trigger_price: float = 0.85    # Price above which "Yield Mode" triggers
    yield_fixed_pct: float = 0.10        # Fixed size % for Yield Mode
    yield_min_whales: int = 3            # Min whales for Yield Mode


# ============================================================================
# The Risk Engine
# ============================================================================

class RiskEngine:
    """
    Microstructure-adjusted Kelly Criterion engine.
    """

    # =========================================================================
    # FLB Probability Calibration
    # =========================================================================

    @staticmethod
    def calibrate_probability(
        p_market: float,
    ) -> Tuple[float, List[str]]:
        """
        Adjust market price using FLB correction (Wolfers 2004 J-Curve).
        Hardcoded to STANDARD mode.

        Zones:
          - Lottery    (p < 0.05): Retail massively overpays (-30%)
          - Hope       (0.05 ≤ p < 0.15): Moderate overpricing (-10%)
          - Efficient  (0.15 ≤ p ≤ 0.90): No adjustment
          - Favorite   (p > 0.90): Retail underpays for certainty (+1pp)

        Returns: (calibrated_probability, list_of_adjustments)
        """
        adjustments: List[str] = []
        p_real = p_market

        # FLB J-Curve (Standard Mode Logic)
        if p_market < 0.05:
            p_real = p_market * 0.7
            adjustments.append(f"FLB_LOTTERY -30% ({p_market:.3f}→{p_real:.3f})")
        elif p_market < 0.15:
            p_real = p_market * 0.9
            adjustments.append(f"FLB_HOPE -10% ({p_market:.3f}→{p_real:.3f})")
        elif p_market > 0.90:
            p_real = min(0.99, p_market + 0.01)
            adjustments.append(f"FLB_FAVORITE +1pp ({p_market:.3f}→{p_real:.3f})")
        
        # Safety clamp
        p_real = max(0.001, min(0.99, p_real))

        return p_real, adjustments

    # =========================================================================
    # Confidence Dampener
    # =========================================================================

    @staticmethod
    def compute_dampener(whale_scores: List[int]) -> Tuple[float, str]:
        """
        Scale bet size based on consensus quality.

        avg_score > 80:  D = 1.0  (Full size — Elite consensus)
        avg_score 60-80: D = 0.5–1.0 (Linear interpolation)
        avg_score < 50:  D = 0.25 (Quarter size — retail-quality signal)
        """
        if not whale_scores:
            return 0.5, "NO_SCORES"

        avg = sum(whale_scores) / len(whale_scores)

        if avg >= 80:
            dampener = 1.0
            detail = f"ELITE_CONSENSUS (avg={avg:.0f})"
        elif avg >= 60:
            # Linear: 60→0.5, 80→1.0
            dampener = 0.5 + (avg - 60) / 20 * 0.5
            detail = f"PRO_CONSENSUS (avg={avg:.0f})"
        elif avg >= 50:
            # Linear: 50→0.25, 60→0.5
            dampener = 0.25 + (avg - 50) / 10 * 0.25
            detail = f"MIXED_CONSENSUS (avg={avg:.0f})"
        else:
            dampener = 0.25
            detail = f"WEAK_CONSENSUS (avg={avg:.0f})"

        return round(dampener, 3), detail

    # =========================================================================
    # Full Position Sizing
    # =========================================================================

    def calculate_position_size(
        self,
        current_price: float,
        alpha_score: int,
        wallet_count: int,
        category: str = "Other",
        whale_scores: Optional[List[int]] = None,
        user_balance: float = 1000.0,
        kelly_multiplier: float = 0.25,
        max_risk_cap: float = 0.05,
        yield_trigger_price: float = 0.85,
        yield_fixed_pct: float = 0.10,
        yield_min_whales: int = 3,
        max_concentration: float = 0.20,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Dynamic Position Sizing: Yield Mode vs. Speculation Mode.

        Logic:
          IF price >= yield_trigger_price AND wallet_count >= yield_min_whales:
             Active "Yield Mode" (Fixed %)
          ELSE:
             Active "Speculation Mode" (De-Biased Kelly)
        """
        # Handle invalid prices
        if current_price <= 0 or current_price >= 1:
            return 0.0, {"error": "Invalid price", "reason": "Price must be 0 < p < 1"}

        # =========================================================================
        # BRANCH 1: Yield Mode (Arbitrage / Safe Parking)
        # =========================================================================
        if current_price >= yield_trigger_price and wallet_count >= yield_min_whales:
            raw_size_pct = yield_fixed_pct
            final_pct = min(raw_size_pct, max_concentration)
            recommended_size = round(user_balance * final_pct, 2)
            
            return recommended_size, {
                "strategy": "YIELD_MODE",
                "market_price": round(current_price, 4),
                "yield_trigger": yield_trigger_price,
                "fixed_pct": yield_fixed_pct,
                "final_pct": round(final_pct, 4),
                "reason": f"Price {current_price:.2f} >= Trigger {yield_trigger_price:.2f}",
                # Fill Kelly fields with nulls/defaults to satisfy schema if needed
                "net_odds": 0,
                "real_prob": 0,
                "kelly_raw": 0,
            }

        # =========================================================================
        # BRANCH 2: Speculation Mode (De-Biased Kelly)
        # =========================================================================
        
        # Step 1: FLB Calibration (Standard)
        p_calibrated, adjustments = self.calibrate_probability(current_price)

        # Step 2: Consensus boosts
        real_prob = p_calibrated
        boosts: List[str] = []

        if alpha_score >= 70:
            real_prob += 0.05
            boosts.append("+5% Alpha (≥70)")

        # Cap at 0.85
        real_prob = min(real_prob, 0.85)

        # Step 3: Kelly formula
        net_odds = (1 - current_price) / current_price
        q = 1 - real_prob
        kelly_raw = (real_prob * net_odds - q) / net_odds

        if kelly_raw <= 0:
            return 0.0, {
                "market_price": round(current_price, 4),
                "p_calibrated": round(p_calibrated, 4),
                "real_prob": round(real_prob, 4),
                "net_odds": round(net_odds, 3),
                "kelly_raw": round(kelly_raw, 4),
                "adjustments": adjustments,
                "prob_boosts": boosts,
                "reason": "Negative EV",
            }

        # Step 4: Confidence Dampener
        dampener, dampener_detail = self.compute_dampener(whale_scores or [])

        # Step 5: Final sizing
        stake_pct = kelly_raw * kelly_multiplier * dampener
        final_pct = min(stake_pct, max_risk_cap)
        recommended_size = round(user_balance * final_pct, 2)

        breakdown = {
            "market_price": round(current_price, 4),
            "p_calibrated": round(p_calibrated, 4),
            "real_prob": round(real_prob, 4),
            "net_odds": round(net_odds, 3),
            "prob_boosts": boosts,
            "adjustments": adjustments,
            "kelly_raw": round(kelly_raw, 4),
            "kelly_multiplier": kelly_multiplier,
            "dampener": dampener,
            "dampener_detail": dampener_detail,
            "stake_percent": round(stake_pct, 4),
            "capped_percent": round(final_pct, 4),
            "max_risk_cap": max_risk_cap,
            "strategy": "KELLY_SPECULATION",
        }

        return recommended_size, breakdown


# Singleton
risk_engine = RiskEngine()
