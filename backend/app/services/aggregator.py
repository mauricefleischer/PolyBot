"""
Consensus Engine - The Logic Core.
Aggregates wallet positions and calculates Becker Alpha Score 2.0.

Alpha Score 2.0 is a multi-factor model based on:
- Favorite-Longshot Bias (FLB) from Wolfers & Zitzewitz 2004
- Anchoring / Momentum breakout signals
- Sector-weighted Smart Short scoring
- Position freshness / time decay
"""
from __future__ import annotations
import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.core.config import settings
from app.models.schemas import (
    RawSignal, SignalSchema, PortfolioSchema,
    PortfolioPositionSchema,
    ScoringConfig, ScoreBreakdown, SignalConsensus, ConsensusContributor
)
from app.services.polymarket import gamma_client
from app.services.chain_data import web3_client
from app.services.whale_scoring import whale_evaluator, Trade as WhaleTrade
from app.services.risk_engine import risk_engine


@dataclass
class AggregatedSignal:
    """Intermediate aggregate before final scoring."""
    group_key: str
    market_id: str
    market_name: str
    outcome_label: str
    direction: str
    category: str
    wallet_addresses: set = field(default_factory=set)
    total_conviction: float = 0.0
    weighted_entry_sum: float = 0.0
    current_price: float = 0.0
    market_slug: str = ""
    token_id: str = ""  # CLOB token ID for price history
    earliest_timestamp: Optional[datetime] = None
    
    @property
    def wallet_count(self) -> int:
        return len(self.wallet_addresses)
    
    @property
    def avg_entry_price(self) -> float:
        if self.total_conviction > 0:
            return self.weighted_entry_sum / self.total_conviction
        return 0.0


class ConsensusEngine:
    """
    Master class for aggregating whale positions and scoring trades.
    Implements the Becker Alpha Score 2.0 algorithm.
    """
    
    def __init__(self):
        self._wallets_file = Path(settings.wallets_file_path)
        self._tracked_wallets: list[str] = []
        self._load_wallets()
    
    def _load_wallets(self):
        """Load tracked wallets from persistent storage."""
        if self._wallets_file.exists():
            try:
                with open(self._wallets_file, "r") as f:
                    data = json.load(f)
                    self._tracked_wallets = data.get("wallets", [])
            except (json.JSONDecodeError, IOError):
                self._tracked_wallets = []
        
        # Always include test wallet for validation
        test_wallet = "0x7523cafcee7bcf2db9a79d80e0d79b88a9a54c4c"
        if test_wallet.lower() not in [w.lower() for w in self._tracked_wallets]:
            self._tracked_wallets.append(test_wallet)
            self._save_wallets()
    
    def _save_wallets(self):
        """Persist wallets to file."""
        self._wallets_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._wallets_file, "w") as f:
            json.dump({"wallets": self._tracked_wallets}, f, indent=2)
    
    def add_wallet(self, address: str) -> bool:
        """Add a wallet to tracking."""
        address_lower = address.lower()
        if address_lower not in [w.lower() for w in self._tracked_wallets]:
            self._tracked_wallets.append(address)
            self._save_wallets()
            return True
        return False
    
    def remove_wallet(self, address: str) -> bool:
        """Remove a wallet from tracking."""
        address_lower = address.lower()
        for i, w in enumerate(self._tracked_wallets):
            if w.lower() == address_lower:
                del self._tracked_wallets[i]
                self._save_wallets()
                return True
        return False
    
    def get_wallets(self) -> list[str]:
        """Get list of tracked wallets."""
        return self._tracked_wallets.copy()
    
    # =========================================================================
    # Position Fetching & Netting
    # =========================================================================
    
    async def _fetch_wallet_positions(self, wallet_address: str) -> list[RawSignal]:
        """
        Fetch and normalize positions for a single wallet.
        Implements Universal Netting: If wallet holds YES and NO, subtract min.
        Also fetches trade activity timestamps for Freshness scoring.
        """
        raw_signals = []
        
        try:
            # Fetch positions and trade activity concurrently
            positions_task = gamma_client.fetch_positions(wallet_address)
            activity_task = gamma_client.fetch_earliest_trades(wallet_address)
            positions, earliest_trades = await asyncio.gather(
                positions_task, activity_task
            )
            
            if not positions:
                return []
            
            # Group by market for netting
            market_positions: dict[str, dict] = defaultdict(lambda: {
                "yes_size": 0.0,
                "no_size": 0.0,
                "yes_entry": 0.0,
                "no_entry": 0.0,
                "market_name": "",
                "outcome_label": "",
                "category": "Other",
                "yes_token_id": "",
                "no_token_id": "",
                "yes_timestamp": None,
                "no_timestamp": None,
            })
            
            for pos in positions:
                # Extract position data (data-api format)
                market_id = pos.get("conditionId", pos.get("condition_id", ""))
                outcome = pos.get("outcome", "Yes")
                size = float(pos.get("size", 0))
                avg_price = float(pos.get("avgPrice", pos.get("avg_price", 0.5)))
                current_price_raw = float(pos.get("curPrice", pos.get("current_price", 0.5)))
                
                # Get market metadata
                market_name = pos.get("title", pos.get("question", "Unknown Market"))
                market_slug = pos.get("slug", gamma_client.get_market_slug(market_id))
                
                if not market_name:
                    market_name = gamma_client.get_market_name(market_id)
                
                category = gamma_client.get_market_category(market_id)
                outcome_label = pos.get("title", outcome)
                
                # The data-api uses 'asset' for token ID
                token_id = pos.get("asset", pos.get("tokenId", pos.get("token_id", "")))
                
                # Get earliest trade timestamp from activity data
                timestamp = None
                earliest_ts = earliest_trades.get(token_id)
                if earliest_ts:
                    try:
                        timestamp = datetime.fromtimestamp(earliest_ts, tz=timezone.utc)
                    except (ValueError, OSError):
                        pass
                
                market_key = f"{market_id}_{outcome}"
                mp = market_positions[market_key]
                mp["market_name"] = market_name
                mp["market_slug"] = market_slug
                mp["outcome_label"] = outcome_label
                mp["category"] = category
                
                if outcome.upper() == "YES":
                    mp["yes_size"] += size
                    mp["yes_entry"] = avg_price
                    mp["yes_token_id"] = token_id
                    mp["yes_cur_price"] = current_price_raw
                    mp["yes_timestamp"] = timestamp
                else:
                    mp["no_size"] += size
                    mp["no_entry"] = avg_price
                    mp["no_token_id"] = token_id
                    mp["no_cur_price"] = current_price_raw
                    mp["no_timestamp"] = timestamp
            
            # Apply Universal Netting and create RawSignals
            for market_key, mp in market_positions.items():
                market_id = market_key.rsplit("_", 1)[0]
                
                yes_size = mp["yes_size"]
                no_size = mp["no_size"]
                
                # Net the positions
                if yes_size > 0 and no_size > 0:
                    min_size = min(yes_size, no_size)
                    yes_size -= min_size
                    no_size -= min_size
                
                if yes_size > 0:
                    current_price = mp.get("yes_cur_price", 0.5)
                    raw_signals.append(RawSignal(
                        wallet_address=wallet_address,
                        market_id=market_id,
                        outcome_label=mp["outcome_label"],
                        direction="YES",
                        entry_price=mp["yes_entry"],
                        current_price=current_price,
                        size_usdc=yes_size * mp["yes_entry"],
                        category=mp["category"],
                        market_name=mp["market_name"],
                        market_slug=mp.get("market_slug", ""),
                        token_id=mp.get("yes_token_id", ""),
                        timestamp=mp.get("yes_timestamp"),
                    ))
                
                if no_size > 0:
                    current_price = mp.get("no_cur_price", 0.5)
                    raw_signals.append(RawSignal(
                        wallet_address=wallet_address,
                        market_id=market_id,
                        outcome_label=mp["outcome_label"],
                        direction="NO",
                        entry_price=mp["no_entry"],
                        current_price=current_price,
                        size_usdc=no_size * mp["no_entry"],
                        category=mp["category"],
                        market_name=mp["market_name"],
                        market_slug=mp.get("market_slug", ""),
                        token_id=mp.get("no_token_id", ""),
                        timestamp=mp.get("no_timestamp"),
                    ))

        except Exception as e:
            print(f"Error fetching positions for {wallet_address}: {e}")
        
        return raw_signals

    # =========================================================================
    # Alpha Score 2.0 – Multi-Factor Scoring Engine
    # =========================================================================
    
    def calculate_alpha_score_v2(
        self,
        signal: AggregatedSignal,
        market_7d_avg: Optional[float] = None,
        config: Optional[ScoringConfig] = None,
    ) -> ScoreBreakdown:
        """
        Calculate Becker Alpha Score 2.0 (0-100) with structured breakdown.
        
        Sub-Factors:
          1. FLB Score: Non-linear price zone penalties/boosts (Wolfers 2004)
          2. Momentum: Price vs 7d moving average (Anchoring breakout)
          3. Smart Short: Direction × Sector sentiment multiplier
          4. Time Decay: Position freshness bonus
        
        Returns: ScoreBreakdown with total score and per-factor details.
        """
        if config is None:
            config = ScoringConfig()
        
        breakdown = ScoreBreakdown()
        breakdown.details.append("Base: 50")
        
        # -------------------------------------------------------------------
        # Sub-Factor 1: FLB Score (Favorite-Longshot Bias)
        # Non-linear price zones based on Wolfers & Zitzewitz (2004)
        # -------------------------------------------------------------------
        p = signal.current_price
        lt = config.longshot_tolerance  # User-tunable scaling (0.5–1.5)
        
        if p < 0.05:
            # Lottery Zone: massively overpriced by retail
            raw_flb = -40
            breakdown.flb = int(raw_flb * lt)
            breakdown.details.append(
                f"{'⛔' if lt >= 1.0 else '⚠️'} Lottery Zone ({breakdown.flb:+d}): "
                f"Price ${p:.2f} < $0.05 — massive retail overpricing"
            )
        elif p < 0.15:
            # Hope Zone: moderately overpriced
            raw_flb = -20
            breakdown.flb = int(raw_flb * lt)
            breakdown.details.append(
                f"⚠️ Hope Zone ({breakdown.flb:+d}): "
                f"Price ${p:.2f} — moderate overpricing"
            )
        elif p > 0.85:
            # Favorite Value: underpriced due to risk-aversion discount
            breakdown.flb = 15
            breakdown.details.append(
                f"✅ Favorite Value (+15): "
                f"Price ${p:.2f} > $0.85 — risk-aversion discount"
            )
        else:
            # Confusion Zone: efficiently priced
            breakdown.flb = 0
            breakdown.details.append(
                f"➖ Neutral Price (0): No FLB edge at ${p:.2f}"
            )
        
        # -------------------------------------------------------------------
        # Sub-Factor 2: Momentum Score (Anchoring / Breakout)
        # Compare current price vs 7-day moving average
        # -------------------------------------------------------------------
        if config.trend_mode and market_7d_avg is not None and market_7d_avg > 0:
            ratio = p / market_7d_avg
            pct_diff = (ratio - 1.0) * 100
            
            if ratio > 1.05:
                # Bullish breakout: price is 5%+ above 7d avg
                breakdown.momentum = 10
                breakdown.details.append(
                    f"✅ Breakout (+10): Price {pct_diff:+.1f}% above weekly average"
                )
            elif ratio < 0.95:
                # Falling knife: price is 5%+ below 7d avg
                breakdown.momentum = -10
                breakdown.details.append(
                    f"⚠️ Falling Knife (-10): Price {pct_diff:+.1f}% below weekly average"
                )
            else:
                breakdown.momentum = 0
                breakdown.details.append(
                    f"➖ No Momentum (0): Price near weekly average ({pct_diff:+.1f}%)"
                )
        elif not config.trend_mode:
            breakdown.momentum = 0
            breakdown.details.append("➖ Momentum (0): Trend mode disabled")
        else:
            breakdown.momentum = 0
            breakdown.details.append("➖ Momentum (0): Insufficient price history")
        
        # -------------------------------------------------------------------
        # Sub-Factor 3: Smart Short Score (Direction × Sector Sentiment)
        # Sector-weighted bonus for contrarian NO bets
        # -------------------------------------------------------------------
        if signal.direction == "NO":
            if signal.category in ("Sports", "Politics"):
                # High optimism tax: strong desirability bias
                breakdown.smart_short = 20
                breakdown.details.append(
                    f"✅ Smart Short (+20): Against public sentiment in {signal.category}"
                )
            elif signal.category == "Entertainment":
                breakdown.smart_short = 15
                breakdown.details.append(
                    f"✅ Smart Short (+15): Against sentiment in {signal.category}"
                )
            else:
                # Finance/Other: efficient markets, smaller edge
                breakdown.smart_short = 10
                breakdown.details.append(
                    f"✅ Smart Short (+10): NO bet in {signal.category}"
                )
        else:
            breakdown.smart_short = 0
            # No detail line for YES (not a penalty)
        
        # -------------------------------------------------------------------
        # Sub-Factor 4: Time Decay / Freshness
        # Fresh signals have higher predictive power
        # Formula: max(0, 10 - 2 × days_since_entry)
        # -------------------------------------------------------------------
        if signal.earliest_timestamp:
            now = datetime.now(timezone.utc)
            days_since = (now - signal.earliest_timestamp).total_seconds() / 86400
            freshness = max(0, int(10 - 2 * days_since))
            breakdown.freshness = freshness
            
            if days_since < 1:
                breakdown.details.append(
                    f"✅ Fresh Signal (+{freshness}): Detected < 24h ago"
                )
            elif freshness > 0:
                breakdown.details.append(
                    f"✅ Recent Signal (+{freshness}): {days_since:.0f} days old"
                )
            else:
                breakdown.details.append(
                    "➖ Stale Signal (0): > 5 days old"
                )
        else:
            breakdown.freshness = 0
            breakdown.details.append("➖ Freshness (0): No timestamp data")
        
        # -------------------------------------------------------------------
        # Final Score: Clamp to [0, 100]
        # -------------------------------------------------------------------
        raw_total = (
            breakdown.base
            + breakdown.flb
            + breakdown.momentum
            + breakdown.smart_short
            + breakdown.freshness
        )
        breakdown.total = max(0, min(100, raw_total))
        
        return breakdown
    
    # =========================================================================
    # Kelly Criterion Position Sizing
    # =========================================================================
    
    def calculate_kelly_size(
        self,
        current_price: float,
        alpha_score: int,
        wallet_count: int,
        user_balance: float = None,
        kelly_multiplier: float = 0.25,
        max_risk_cap: float = 0.05,
    ) -> tuple[float, Dict[str, Any]]:
        """
        Calculate recommended position size using Fractional Kelly Criterion.
        
        Formula:
        - Step A: Net Odds (b) = (1 - Price) / Price
        - Step B: Real Probability (p) = Price + boosts (capped 0.85)
        - Step C: Kelly (f) = (p * b - (1-p)) / b
        - Step D: Final = min(f * KellyMultiplier, MaxRiskCap)
        
        Returns: (recommended_size, calculation_breakdown)
        """
        if user_balance is None:
            user_balance = settings.default_user_balance
        
        # Handle edge cases
        if current_price <= 0 or current_price >= 1:
            return 0.0, {"error": "Invalid price"}
        
        # Step A: Calculate Net Odds
        net_odds = (1 - current_price) / current_price
        
        # Step B: Estimate Real Probability with boosts
        real_prob = current_price
        boosts = []
        
        if wallet_count >= 3:
            real_prob += 0.05
            boosts.append("+5% Consensus")
        
        if alpha_score >= 70:
            real_prob += 0.05
            boosts.append("+5% Alpha")
        
        # Cap at 0.85
        real_prob = min(real_prob, 0.85)
        
        # Step C: Kelly Formula
        q = 1 - real_prob
        kelly_fraction = (real_prob * net_odds - q) / net_odds
        
        # If Kelly is negative, don't bet
        if kelly_fraction <= 0:
            return 0.0, {
                "net_odds": round(net_odds, 2),
                "real_prob": round(real_prob, 2),
                "kelly_raw": round(kelly_fraction, 4),
                "reason": "Negative EV"
            }
        
        # Step D: Fractional scaling and hard cap
        stake_percent = kelly_fraction * kelly_multiplier
        final_percent = min(stake_percent, max_risk_cap)
        
        # Calculate final size
        recommended_size = user_balance * final_percent
        
        breakdown = {
            "net_odds": round(net_odds, 2),
            "real_prob": round(real_prob, 2),
            "prob_boosts": boosts,
            "kelly_raw": round(kelly_fraction, 4),
            "kelly_multiplier": kelly_multiplier,
            "stake_percent": round(stake_percent, 4),
            "capped_percent": round(final_percent, 4),
            "max_risk_cap": max_risk_cap
        }
        
        return round(recommended_size, 2), breakdown

    # =========================================================================
    # Signal Aggregation & Ranking
    # =========================================================================

    async def aggregate_signals(self) -> list[AggregatedSignal]:
        """
        Aggregate all positions from tracked wallets.
        Groups by: market_id + outcome_label + direction
        """
        all_signals: list[RawSignal] = []
        
        # Fetch positions from all tracked wallets
        for wallet in self._tracked_wallets:
            signals = await self._fetch_wallet_positions(wallet)
            all_signals.extend(signals)
        
        # Group by unique key
        groups: dict[str, AggregatedSignal] = {}
        
        for signal in all_signals:
            group_key = f"{signal.market_id}_{signal.outcome_label}_{signal.direction}"
            
            if group_key not in groups:
                groups[group_key] = AggregatedSignal(
                    group_key=group_key,
                    market_id=signal.market_id,
                    market_name=signal.market_name,
                    outcome_label=signal.outcome_label,
                    direction=signal.direction,
                    category=signal.category,
                    market_slug=getattr(signal, 'market_slug', ''),
                    token_id=getattr(signal, 'token_id', ''),
                    current_price=signal.current_price,
                )
            
            agg = groups[group_key]
            agg.wallet_addresses.add(signal.wallet_address.lower())
            agg.total_conviction += signal.size_usdc
            agg.weighted_entry_sum += signal.entry_price * signal.size_usdc
            agg.current_price = signal.current_price
            
            # Keep the first non-empty token_id
            if not agg.token_id and getattr(signal, 'token_id', ''):
                agg.token_id = signal.token_id
            
            # Track earliest timestamp for freshness scoring
            if signal.timestamp:
                if agg.earliest_timestamp is None or signal.timestamp < agg.earliest_timestamp:
                    agg.earliest_timestamp = signal.timestamp
        
        return list(groups.values())
    
    async def get_ranked_signals(
        self, 
        min_wallets: int = 2,
        user_balance: Optional[float] = None,
        kelly_multiplier: float = 0.25,
        max_risk_cap: float = 0.05,
        hide_lottery: bool = False,
        longshot_tolerance: float = 1.0,
        trend_mode: bool = True,
        trend_mode: bool = True,
        yield_trigger_price: float = 0.85,
        yield_fixed_pct: float = 0.10,
        yield_min_whales: int = 3,
    ) -> list[SignalSchema]:
        """
        Get fully processed, ranked signals for the API.
        Uses Alpha Score 2.0 multi-factor model + Whale Quality Scoring.
        
        Ranking:
        1. Filter: wallet_count >= min_wallets
        2. Primary: wallet_count (desc)
        3. Secondary: alpha_score (desc)
        4. Tertiary: total_conviction (desc)
        """
        from app.services.database import db_service
        
        aggregated = await self.aggregate_signals()
        
        # =====================================================================
        # Whale Scoring: compute Smart Money Scores for all tracked wallets
        # =====================================================================
        whale_scores_map: Dict[str, dict] = {}  # address → score breakdown
        
        # Collect all wallet addresses from aggregated signals
        all_wallet_addrs: set[str] = set()
        for agg in aggregated:
            all_wallet_addrs.update(agg.wallet_addresses)
        
        # Fetch activity and compute scores for each wallet
        for wallet_addr in all_wallet_addrs:
            # Check DB cache first
            cached = db_service.get_whale_score(wallet_addr)
            if cached:
                whale_scores_map[wallet_addr.lower()] = cached
                continue
            
            try:
                activity = await gamma_client.fetch_activity(wallet_addr, limit=500)
                # Convert to WhaleTrade objects
                whale_trades = []
                for t in activity:
                    whale_trades.append(WhaleTrade(
                        asset=t.get("asset", ""),
                        condition_id=t.get("conditionId", ""),
                        side=t.get("side", "BUY").upper(),
                        price=float(t.get("price", 0)),
                        size=float(t.get("size", 0)),
                        timestamp=int(t.get("timestamp", 0)),
                        market_slug=t.get("slug", ""),
                    ))
                
                # Count active positions for precision scoring
                positions = await gamma_client.fetch_positions(wallet_addr)
                active_count = len(positions) if positions else 0
                
                # Compute score
                score_result = whale_evaluator.compute_score(whale_trades, active_count)
                score_dict = score_result.to_dict()
                
                # Cache in DB
                db_service.save_whale_score(wallet_addr, score_dict)
                whale_scores_map[wallet_addr.lower()] = score_dict
            except Exception as e:
                print(f"Whale scoring error for {wallet_addr[:10]}...: {e}")
                whale_scores_map[wallet_addr.lower()] = {
                    "total_score": 50, "tier": "UNRATED", "tags": [],
                    "roi_score": 50, "discipline_score": 50,
                    "precision_score": 50, "timing_score": 50,
                    "trade_count": 0, "details": {},
                }
        
                    # Removed filtering by tier/bagholder (showing all signals, relying on scoring)
                    filtered_wallets.add(w)
                agg.wallet_addresses = filtered_wallets
        
        # Fetch 7-day price averages from CLOB API for momentum scoring
        token_ids = [agg.token_id for agg in aggregated if agg.token_id]
        price_averages: Dict[str, float] = {}
        if trend_mode and token_ids:
            try:
                price_averages = await gamma_client.get_7d_averages_batch(token_ids)
            except Exception as e:
                print(f"Warning: Failed to fetch price history from CLOB API: {e}")
        
        # Build scoring config from user settings
        scoring_config = ScoringConfig(
            longshot_tolerance=longshot_tolerance,
            trend_mode=trend_mode,
        )
        
        # Filter by minimum wallets
        filtered = [s for s in aggregated if s.wallet_count >= min_wallets]
        
        # Calculate scores and convert to schema
        signals = []
        for agg in filtered:
            # Get 7-day average for this market's token
            market_7d_avg = price_averages.get(agg.token_id) if agg.token_id else None
            
            # Alpha Score 2.0
            score_breakdown = self.calculate_alpha_score_v2(
                agg, market_7d_avg, scoring_config
            )
            alpha_score = score_breakdown.total
            
            # Skip lottery tickets if filter is enabled
            if hide_lottery and alpha_score < 30:
                continue
            
            # Build WhaleMeta for this signal
            signal_whale_scores: List[int] = []
            has_elite = False
            has_bagholder = False
            wallet_tiers: Dict[str, str] = {}
            for w in agg.wallet_addresses:
                ws = whale_scores_map.get(w.lower(), {})
                w_total = ws.get("total_score", 50)
                w_tier = ws.get("tier", "UNRATED")
                signal_whale_scores.append(w_total)
                wallet_tiers[w[:10] + "..."] = w_tier
                if w_tier == "ELITE":
                    has_elite = True
                if w_tier == "WEAK":
                    has_bagholder = True
            
            avg_whale_score = (
                sum(signal_whale_scores) // len(signal_whale_scores)
                if signal_whale_scores else 50
            )
            
            # Build SignalConsensus object
            consensus_contributors = []
            for w in agg.wallet_addresses:
                ws = whale_scores_map.get(w.lower(), {})
                consensus_contributors.append(ConsensusContributor(
                    address=w,
                    score=ws.get("total_score", 50),
                    tier=ws.get("tier", "UNRATED")
                ))
            
            # Sort contributors by score desc
            consensus_contributors.sort(key=lambda c: -c.score)

            consensus_data = SignalConsensus(
                count=agg.wallet_count,
                has_elite=has_elite,
                weighted_score=avg_whale_score,
                contributors=consensus_contributors
            )
            
            # De-Biased Kelly sizing (replaces naive Kelly)
            rec_size, kelly_breakdown = risk_engine.calculate_position_size(
                current_price=agg.current_price,
                alpha_score=alpha_score,
                wallet_count=agg.wallet_count,
                category=agg.category,
                whale_scores=signal_whale_scores,
                user_balance=user_balance or settings.default_user_balance,
                kelly_multiplier=kelly_multiplier,
                max_risk_cap=max_risk_cap,
                kelly_multiplier=kelly_multiplier,
                max_risk_cap=max_risk_cap,
                yield_trigger_price=yield_trigger_price,
                yield_fixed_pct=yield_fixed_pct,
                yield_min_whales=yield_min_whales,
            )
            
            signals.append(SignalSchema(
                group_key=agg.group_key,
                market_id=agg.market_id,
                market_name=agg.market_name,
                market_slug=agg.market_slug,
                outcome_label=agg.outcome_label,
                direction=agg.direction,
                category=agg.category,
                wallet_count=agg.wallet_count,
                total_conviction=round(agg.total_conviction, 2),
                avg_entry_price=round(agg.avg_entry_price, 4),
                current_price=round(agg.current_price, 4),
                alpha_score=alpha_score,
                alpha_breakdown=score_breakdown.to_dict(),
                recommended_size=rec_size,
                kelly_breakdown=kelly_breakdown,
                consensus=consensus_data,  # New structured object
                whale_meta=None,     # Deprecated, using consensus object
            ))
        
        # Sort: wallet_count desc, alpha_score desc, conviction desc
        signals.sort(
            key=lambda s: (-s.wallet_count, -s.alpha_score, -s.total_conviction)
        )
        
        return signals
    
    # =========================================================================
    # Portfolio Validation
    # =========================================================================
    
    async def get_user_portfolio(
        self, 
        wallet_address: str
    ) -> PortfolioSchema:
        """
        Get user's portfolio compared against whale consensus.
        """
        # Fetch user's USDC balance
        usdc_balance = await web3_client.get_usdc_balance(wallet_address)
        
        # Fetch user's positions
        user_signals = await self._fetch_wallet_positions(wallet_address)
        
        # Get whale consensus for comparison
        consensus = await self.aggregate_signals()
        consensus_map = {
            f"{s.market_id}_{s.outcome_label}_{s.direction}": s
            for s in consensus
        }
        
        positions = []
        total_invested = 0.0
        total_pnl = 0.0
        validated_count = 0
        divergence_count = 0
        
        for signal in user_signals:
            key = f"{signal.market_id}_{signal.outcome_label}_{signal.direction}"
            
            # Calculate PnL
            if signal.entry_price > 0:
                pnl_percent = ((signal.current_price - signal.entry_price) / signal.entry_price) * 100
            else:
                pnl_percent = 0.0
            
            # Check consensus
            whale_signal = consensus_map.get(key)
            if whale_signal:
                status = "VALIDATED"
                whale_consensus = True
                whale_count = whale_signal.wallet_count
                validated_count += 1
            else:
                # Check if whales are on opposite side
                opposite_key = f"{signal.market_id}_{signal.outcome_label}_{'NO' if signal.direction == 'YES' else 'YES'}"
                opposite_signal = consensus_map.get(opposite_key)
                
                if opposite_signal and opposite_signal.wallet_count >= 2:
                    status = "DIVERGENCE"
                    divergence_count += 1
                elif pnl_percent > 20:
                    status = "TRIM"
                else:
                    status = "VALIDATED"
                
                whale_consensus = False
                whale_count = 0
            
            total_invested += signal.size_usdc
            position_pnl = signal.size_usdc * (pnl_percent / 100)
            total_pnl += position_pnl
            
            positions.append(PortfolioPositionSchema(
                market_id=signal.market_id,
                market_name=signal.market_name,
                outcome_label=signal.outcome_label,
                direction=signal.direction,
                size_usdc=round(signal.size_usdc, 2),
                entry_price=round(signal.entry_price, 4),
                current_price=round(signal.current_price, 4),
                pnl_percent=round(pnl_percent, 2),
                status=status,
                whale_consensus=whale_consensus,
                whale_count=whale_count,
            ))
        
        return PortfolioSchema(
            wallet_address=wallet_address,
            usdc_balance=round(usdc_balance, 2),
            total_invested=round(total_invested, 2),
            total_pnl=round(total_pnl, 2),
            positions=positions,
            validated_count=validated_count,
            divergence_count=divergence_count,
        )


# Global engine instance
consensus_engine = ConsensusEngine()
