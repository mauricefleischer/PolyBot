"""
Whale Quality Score — Smart Money Scoring Engine.

Rates every tracked wallet on a 0–100 scale using 4 behavioral pillars:
  1. ROI Performance   (35%) — Modified Information Ratio
  2. Discipline        (25%) — Anti-Disposition Effect (Odean 1998)
  3. Precision         (20%) — Anti-Overconfidence (Glaser/Weber)
  4. Timing            (20%) — Anti-Herding / Pioneer detection

Based on:
  - Odean 1998 / Weber 2007 (Disposition Effect)
  - Glaser & Weber (Overconfidence / Overtrading)
  - Wolfers & Zitzewitz 2004 (FLB)
  - Becker 2025 (Optimism Tax)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel


# ============================================================================
# Data Structures
# ============================================================================

class Trade(BaseModel):
    """A single trade from the Data API /activity endpoint."""
    asset: str = ""                # Token ID
    condition_id: str = ""         # Market condition ID
    side: str = ""                 # "BUY" or "SELL"
    price: float = 0.0
    size: float = 0.0              # USDC notional
    timestamp: int = 0             # Unix seconds
    market_slug: str = ""


class WhaleScoreBreakdown(BaseModel):
    """Complete scoring breakdown for a wallet."""
    roi_score: int = 50
    discipline_score: int = 50
    precision_score: int = 50
    timing_score: int = 50
    total_score: int = 50
    tags: List[str] = []
    tier: str = "STD"
    trade_count: int = 0
    details: Dict[str, str] = {}

    def to_dict(self) -> dict:
        return {
            "roi_score": self.roi_score,
            "discipline_score": self.discipline_score,
            "precision_score": self.precision_score,
            "timing_score": self.timing_score,
            "total_score": self.total_score,
            "tags": self.tags,
            "tier": self.tier,
            "trade_count": self.trade_count,
            "details": self.details,
        }


@dataclass
class WhaleScoringConfig:
    """Weights and thresholds for the scoring model."""
    # Pillar weights (must sum to 1.0)
    w_roi: float = 0.35
    w_discipline: float = 0.25
    w_precision: float = 0.20
    w_timing: float = 0.20
    # Thresholds
    min_trades_for_valid_score: int = 5
    whale_bonus_threshold: float = 50_000.0   # $50K total profit for bonus
    bagholder_ratio_threshold: float = 2.0
    precision_high_roi_bypass: int = 80        # Skip precision penalty if ROI > 80


# ============================================================================
# Internal: Matched Trade (Buy→Sell pair)
# ============================================================================

@dataclass
class MatchedTrade:
    """A resolved buy→sell trade pair for P&L analysis."""
    asset: str
    entry_price: float
    exit_price: float
    size: float
    entry_time: int       # Unix seconds
    exit_time: int        # Unix seconds
    pnl_usdc: float = 0.0

    @property
    def duration_hours(self) -> float:
        return max(0, (self.exit_time - self.entry_time)) / 3600.0

    @property
    def is_winner(self) -> bool:
        return self.pnl_usdc > 0


# ============================================================================
# The Whale Evaluator
# ============================================================================

class WhaleEvaluator:
    """
    Computes the Smart Money Score (0–100) for a tracked wallet
    based on its complete trade history.
    """

    def __init__(self, config: WhaleScoringConfig | None = None):
        self.config = config or WhaleScoringConfig()

    # =========================================================================
    # Trade Matching: pair BUYs with SELLs to compute P&L
    # =========================================================================

    def _match_trades(self, trades: List[Trade]) -> List[MatchedTrade]:
        """
        Match BUY trades with subsequent SELL trades on the same asset
        using FIFO to compute realized P&L.
        """
        # Group trades by asset, sorted by timestamp
        by_asset: Dict[str, List[Trade]] = {}
        for t in trades:
            by_asset.setdefault(t.asset, []).append(t)

        matched: List[MatchedTrade] = []

        for asset, asset_trades in by_asset.items():
            asset_trades.sort(key=lambda t: t.timestamp)

            # FIFO queue of buys
            buy_queue: List[Tuple[float, float, int]] = []  # (price, remaining_size, ts)

            for trade in asset_trades:
                if trade.side.upper() == "BUY":
                    buy_queue.append((trade.price, trade.size, trade.timestamp))
                elif trade.side.upper() == "SELL" and buy_queue:
                    sell_remaining = trade.size
                    sell_price = trade.price
                    sell_ts = trade.timestamp

                    while sell_remaining > 0 and buy_queue:
                        buy_price, buy_size, buy_ts = buy_queue[0]
                        fill = min(sell_remaining, buy_size)

                        # P&L = (sell_price - buy_price) × fill
                        pnl = (sell_price - buy_price) * fill

                        matched.append(MatchedTrade(
                            asset=asset,
                            entry_price=buy_price,
                            exit_price=sell_price,
                            size=fill,
                            entry_time=buy_ts,
                            exit_time=sell_ts,
                            pnl_usdc=pnl,
                        ))

                        sell_remaining -= fill
                        remaining_buy = buy_size - fill
                        buy_queue.pop(0)
                        if remaining_buy > 0:
                            buy_queue.insert(0, (buy_price, remaining_buy, buy_ts))

        return matched

    # =========================================================================
    # Pillar 1: ROI Performance (35%)
    # =========================================================================

    def _calc_roi_score(self, matched: List[MatchedTrade]) -> Tuple[int, str]:
        """
        Modified Information Ratio.

        Formula:
          Raw_ROI = Total_Profit / Total_Entry_Cost
          Win_Rate = Winners / Total
          S_ROI = min(100, WinRate×100 + RawROI×50)
          Bonus: +10 if total profit > $50K
        """
        if not matched:
            return 50, "NO_DATA"

        total_entry_cost = sum(m.entry_price * m.size for m in matched)
        total_profit = sum(m.pnl_usdc for m in matched)
        winners = sum(1 for m in matched if m.is_winner)
        total = len(matched)
        win_rate = winners / total if total > 0 else 0.0

        if total_entry_cost > 0:
            raw_roi = total_profit / total_entry_cost
        else:
            raw_roi = 0.0

        if raw_roi < 0:
            # Losing trader — score proportional to how negative
            score = max(0, int(50 + raw_roi * 100))  # -0.5 ROI → score 0
            detail = f"NEGATIVE (ROI {raw_roi:.1%})"
        else:
            score = min(100, int(win_rate * 100 + raw_roi * 50))
            detail = f"WR {win_rate:.0%} / ROI {raw_roi:.1%}"

        # Whale bonus: +10 if total profit > threshold
        if total_profit > self.config.whale_bonus_threshold:
            score = min(100, score + 10)
            detail += " +WHALE"

        return max(0, min(100, score)), detail

    # =========================================================================
    # Pillar 2: Discipline — Anti-Disposition Effect (25%)
    # =========================================================================

    def _calc_discipline_score(self, matched: List[MatchedTrade]) -> Tuple[int, str]:
        """
        'Diamond Hands' metric.

        Detect Disposition Effect: selling winners too early, holding losers too long.

        Ratio = Avg_Hold_Time_Losers / Avg_Hold_Time_Winners
          - Ratio <= 0.5: Score = 100 (cuts losses 2x faster)
          - Ratio ~= 1.0: Score = 50 (neutral)
          - Ratio >= 2.0: Score = 0  (bagholder)

        Formula: S = clamp(0, 100, 100 - (Ratio - 0.5) × 66)
        """
        winners = [m for m in matched if m.is_winner]
        losers = [m for m in matched if not m.is_winner]

        if not winners or not losers:
            return 50, "INSUFFICIENT"

        avg_winner_hours = sum(m.duration_hours for m in winners) / len(winners)
        avg_loser_hours = sum(m.duration_hours for m in losers) / len(losers)

        if avg_winner_hours == 0:
            return 50, "NEUTRAL"

        ratio = avg_loser_hours / avg_winner_hours

        # Linear scoring: 0.5 → 100, 2.0 → 0
        score = int(100 - (ratio - 0.5) * 66)
        score = max(0, min(100, score))

        if ratio <= 0.5:
            detail = f"EXCEPTIONAL (R={ratio:.2f})"
        elif ratio <= 1.0:
            detail = f"GOOD (R={ratio:.2f})"
        elif ratio <= 1.5:
            detail = f"MODERATE (R={ratio:.2f})"
        else:
            detail = f"POOR (R={ratio:.2f})"

        return score, detail

    # =========================================================================
    # Pillar 3: Precision — Anti-Overconfidence (20%)
    # =========================================================================

    def _calc_precision_score(
        self, trades: List[Trade], active_positions: int, roi_score: int
    ) -> Tuple[int, str]:
        """
        'Sniper' metric — penalize churning / overtrading.

        Turnover_Index = Trade_Count / (Active_Positions + 1)

        Exception: If ROI_Score > 80, bypass penalty (profitable HFT is fine).

        Scoring:
          Turnover < 2.0 → 100 (Sniper)
          Turnover > 10.0 → 0 (Degen)
          In between: logarithmic decay
        """
        # Profitability exception
        if roi_score > self.config.precision_high_roi_bypass:
            return 100, "BYPASS (HIGH_ROI)"

        trade_count = len(trades)
        turnover = trade_count / (active_positions + 1)

        if turnover < 2.0:
            score = 100
            detail = f"PRECISE (T={turnover:.1f})"
        elif turnover > 10.0:
            score = max(0, int(10 - (turnover - 10) * 0.5))
            detail = f"CHURNING (T={turnover:.1f})"
        else:
            # Logarithmic decay from 100 to 10 over turnover 2–10
            score = int(100 - 90 * math.log(turnover / 2) / math.log(5))
            score = max(0, min(100, score))
            detail = f"ACTIVE (T={turnover:.1f})"

        return score, detail

    # =========================================================================
    # Pillar 4: Timing — Anti-Herding / Pioneer Score (20%)
    # =========================================================================

    def _calc_timing_score(self, trades: List[Trade]) -> Tuple[int, str]:
        """
        'Pioneer' metric — reward early movers, penalize FOMO entries.

        Since we don't have market_start_time, we use entry PRICE as a proxy:
          - BUY at price 0.10 → entering when market is uncertain (early)
          - BUY at price 0.90 → entering when outcome is near-certain (late/FOMO)

        For BUY trades:
          entry_percentile = price  (lower price = earlier entry)
        For SELL trades:
          entry_percentile = 1 - price  (higher sell price = better exit)

        Average percentile across all trades:
          < 0.2 → Score = 100 (Pioneer)
          0.3–0.7 → Score = 50 (Crowd)
          > 0.8 → Score = 0 (Exit Liquidity)
        """
        if not trades:
            return 50, "NO_DATA"

        percentiles: List[float] = []
        for t in trades:
            if t.side.upper() == "BUY":
                # Lower entry price = earlier / more contrarian
                percentiles.append(t.price)
            elif t.side.upper() == "SELL":
                # Higher sell price = better timing
                percentiles.append(1.0 - t.price)

        if not percentiles:
            return 50, "NO_DATA"

        avg_percentile = sum(percentiles) / len(percentiles)

        # Linear scoring: 0.0 → 100, 1.0 → 0
        if avg_percentile < 0.2:
            score = 100
            detail = f"PIONEER (P={avg_percentile:.2f})"
        elif avg_percentile < 0.3:
            score = int(100 - (avg_percentile - 0.2) * 500)
            detail = f"EARLY (P={avg_percentile:.2f})"
        elif avg_percentile <= 0.7:
            score = int(75 - (avg_percentile - 0.3) * 62.5)
            detail = f"CROWD (P={avg_percentile:.2f})"
        elif avg_percentile <= 0.8:
            score = int(50 - (avg_percentile - 0.7) * 500)
            detail = f"LATE (P={avg_percentile:.2f})"
        else:
            score = max(0, int(10 - (avg_percentile - 0.8) * 50))
            detail = f"FOMO (P={avg_percentile:.2f})"

        return max(0, min(100, score)), detail

    # =========================================================================
    # Master Scorer
    # =========================================================================

    def compute_score(
        self,
        trades: List[Trade],
        active_positions: int = 0,
    ) -> WhaleScoreBreakdown:
        """
        Compute the full Smart Money Score for a wallet.

        Steps:
        1. Match trades (BUY→SELL pairs) for P&L
        2. Calculate each pillar
        3. Weighted sum → total score
        4. Assign tier and tags
        """
        # Default for wallets with too few trades
        if len(trades) < self.config.min_trades_for_valid_score:
            return WhaleScoreBreakdown(
                roi_score=50,
                discipline_score=50,
                precision_score=50,
                timing_score=50,
                total_score=50,
                tags=[],
                tier="UNRATED",
                trade_count=len(trades),
                details={"status": f"UNRATED ({len(trades)} trades < {self.config.min_trades_for_valid_score} min)"},
            )

        # Step 1: Match trades for P&L
        matched = self._match_trades(trades)

        # Step 2: Calculate pillars
        roi_score, roi_detail = self._calc_roi_score(matched)
        disc_score, disc_detail = self._calc_discipline_score(matched)
        prec_score, prec_detail = self._calc_precision_score(
            trades, active_positions, roi_score
        )
        time_score, time_detail = self._calc_timing_score(trades)

        # Step 3: Weighted sum
        total_raw = (
            self.config.w_roi * roi_score
            + self.config.w_discipline * disc_score
            + self.config.w_precision * prec_score
            + self.config.w_timing * time_score
        )
        total_score = max(0, min(100, int(total_raw)))

        # Step 4: Tags (ISO-style codes, no emojis)
        tags: List[str] = []
        if disc_score > 90:
            tags.append("HLD")      # Holder / Diamond Hands
        elif disc_score < 20:
            tags.append("DUMP")     # Paper Hands / Dumper
        if prec_score > 90:
            tags.append("PRC")      # Precision
        elif prec_score < 20:
            tags.append("CHRN")     # Churner
        if time_score > 80:
            tags.append("PNIR")     # Pioneer
        if roi_score > 80:
            tags.append("PROF")     # Profitable

        # Step 5: Tier assignment
        if total_score >= 80:
            tier = "ELITE"
        elif total_score >= 60:
            tier = "PRO"
        elif total_score >= 40:
            tier = "STD"
        else:
            tier = "WEAK"

        return WhaleScoreBreakdown(
            roi_score=roi_score,
            discipline_score=disc_score,
            precision_score=prec_score,
            timing_score=time_score,
            total_score=total_score,
            tags=tags,
            tier=tier,
            trade_count=len(trades),
            details={
                "roi": roi_detail,
                "discipline": disc_detail,
                "precision": prec_detail,
                "timing": time_detail,
            },
        )


# Singleton evaluator with default config
whale_evaluator = WhaleEvaluator()
