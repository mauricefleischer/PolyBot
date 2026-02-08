"""
Consensus Engine - The Logic Core.
Aggregates wallet positions and calculates Becker Alpha scores.
"""
from __future__ import annotations
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict

from app.core.config import settings
from app.models.schemas import RawSignal, SignalSchema, PortfolioPositionSchema, PortfolioSchema
from app.services.polymarket import gamma_client
from app.services.chain_data import web3_client


@dataclass
class AggregatedSignal:
    """Intermediate aggregate before final scoring."""
    group_key: str
    market_id: str
    market_name: str
    outcome_label: str
    direction: str
    category: str
    wallet_addresses: set
    total_conviction: float
    weighted_entry_sum: float  # For calculating weighted avg entry
    current_price: float
    
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
    Implements the Becker Alpha scoring algorithm.
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
    
    async def _fetch_wallet_positions(self, wallet_address: str) -> list[RawSignal]:
        """
        Fetch and normalize positions for a single wallet.
        Implements Universal Netting: If wallet holds YES and NO, subtract min.
        """
        raw_signals = []
        
        try:
            # Fetch positions from Gamma API
            positions = await gamma_client.fetch_positions(wallet_address)
            
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
                outcome_label = pos.get("title", outcome)  # Use title as outcome label
                
                # The data-api uses 'asset' for token ID
                token_id = pos.get("asset", pos.get("tokenId", pos.get("token_id", "")))
                
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
                else:
                    mp["no_size"] += size
                    mp["no_entry"] = avg_price
                    mp["no_token_id"] = token_id
                    mp["no_cur_price"] = current_price_raw
            
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
                
                # Use curPrice from data-api directly instead of fetching again
                if yes_size > 0:
                    current_price = mp.get("yes_cur_price", 0.5)
                    raw_signals.append(RawSignal(
                        wallet_address=wallet_address,
                        market_id=market_id,
                        outcome_label=mp["outcome_label"],
                        direction="YES",
                        entry_price=mp["yes_entry"],
                        current_price=current_price,
                        size_usdc=yes_size * mp["yes_entry"],  # Size in USDC
                        category=mp["category"],
                        market_name=mp["market_name"],
                        market_slug=mp.get("market_slug", ""),
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
                    ))

        except Exception as e:
            print(f"Error fetching positions for {wallet_address}: {e}")
        
        return raw_signals

    # ... (skipping calculate_alpha_score methods) ...

    async def get_ranked_signals(
        self,
        min_wallets: int = 1,
        user_balance: Optional[float] = None,
        kelly_multiplier: float = 0.25,
        max_risk_cap: float = 0.05,
        hide_lottery: bool = False,
    ) -> List[SignalSchema]:
        """
        Get aggregated, ranked signals with Kelly sizing.
        """
        raw_signals = await self.aggregate_positions()
        
        # Group by Market + Outcome + Direction
        grouped_signals: Dict[str, AggregatedSignal] = {}
        
        for sig in raw_signals:
            key = f"{sig.market_id}_{sig.outcome_label}_{sig.direction}"
            
            if key not in grouped_signals:
                grouped_signals[key] = AggregatedSignal(
                    id=key,
                    market_id=sig.market_id,
                    market_name=sig.market_name,
                    outcome_label=sig.outcome_label,
                    direction=sig.direction,
                    category=sig.category,
                    market_slug=sig.market_slug,
                )
            
            group = grouped_signals[key]
            group.wallets.add(sig.wallet_address)
            group.total_conviction += sig.size_usdc
            group.current_price = sig.current_price  # Assess latest price
            
            # Weighted average entry
            current_total_value = (group.avg_entry_price * (group.total_conviction - sig.size_usdc)) + (sig.entry_price * sig.size_usdc)
            if group.total_conviction > 0:
                group.avg_entry_price = current_total_value / group.total_conviction
            else:
                group.avg_entry_price = sig.entry_price

        # ... (rest of filtering) ...

        results = []
        for group in grouped_signals.values():
            if len(group.wallets) < min_wallets:
                continue
                
            alpha_score, text_breakdown = self.calculate_alpha_score(group)
            
            if hide_lottery and alpha_score < 30:
                continue
            
            recommended_size = 0.0
            kelly_breakdown = {}
            
            if user_balance:
                recommended_size, kelly_breakdown = self.calculate_kelly_size(
                    group.current_price,
                    alpha_score,
                    user_balance,
                    multiplier=kelly_multiplier,
                    max_risk_cap=max_risk_cap
                )
            
            results.append(SignalSchema(
                group_key=group.id,
                market_id=group.market_id,
                market_name=group.market_name,
                market_slug=group.market_slug,
                outcome_label=group.outcome_label,
                direction=group.direction,
                category=group.category,
                wallet_count=len(group.wallets),
                total_conviction=group.total_conviction,
                avg_entry_price=group.avg_entry_price,
                current_price=group.current_price,
                alpha_score=alpha_score,
                alpha_breakdown=text_breakdown,
                recommended_size=recommended_size,
                kelly_breakdown=kelly_breakdown,
            ))
        
        # Sort by Wallet Count DESC, then Alpha Score DESC
        results.sort(key=lambda x: (x.wallet_count, x.alpha_score, x.total_conviction), reverse=True)
        
        return results
    
    def calculate_alpha_score(self, signal: AggregatedSignal) -> tuple[int, List[str]]:
        """
        Calculate Becker Alpha Score (0-100) with breakdown for tooltips.
        
        Returns: (score, breakdown_list)
        """
        score = 50  # Base score
        breakdown = ["Base: 50"]
        
        # Rule 1: Smart Short Bonus
        if signal.direction == "NO":
            score += 20
            breakdown.append("+20 Smart Short")
        
        # Rule 2: Longshot Penalty
        if signal.direction == "YES" and signal.current_price < 0.10:
            score -= 30
            breakdown.append("-30 Longshot")
        
        # Rule 3: Extreme Favorite Boost
        if signal.direction == "YES" and signal.current_price > 0.80:
            score += 10
            breakdown.append("+10 Favorite")
        
        # Rule 4: Sector Inefficiency Bonus
        if signal.category in ["Sports", "Politics", "Entertainment"]:
            score += 5
            breakdown.append("+5 Sector")
        
        # Rule 5: Conviction Multiplier
        if signal.wallet_count >= 3:
            score += 10
            breakdown.append("+10 Consensus")
        
        # Clamp to 0-100
        final_score = max(0, min(100, score))
        return final_score, breakdown
    
    def calculate_kelly_size(
        self,
        current_price: float,
        alpha_score: int,
        wallet_count: int,
        user_balance: float = None,
        kelly_multiplier: float = 0.25,
        max_risk_cap: float = 0.05
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
        # f = (p * b - (1-p)) / b = (p * b - q) / b where q = 1-p
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
        
        # Build breakdown for tooltip
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
                    wallet_addresses=set(),
                    total_conviction=0.0,
                    weighted_entry_sum=0.0,
                    current_price=signal.current_price,
                )
            
            agg = groups[group_key]
            agg.wallet_addresses.add(signal.wallet_address.lower())
            agg.total_conviction += signal.size_usdc
            agg.weighted_entry_sum += signal.entry_price * signal.size_usdc
            # Update price to latest
            agg.current_price = signal.current_price
        
        return list(groups.values())
    
    async def get_ranked_signals(
        self, 
        min_wallets: int = 2,
        user_balance: Optional[float] = None,
        kelly_multiplier: float = 0.25,
        max_risk_cap: float = 0.05,
        hide_lottery: bool = False
    ) -> list[SignalSchema]:
        """
        Get fully processed, ranked signals for the API.
        
        Ranking:
        1. Filter: wallet_count >= min_wallets
        2. Primary: wallet_count (desc)
        3. Secondary: alpha_score (desc)
        4. Tertiary: total_conviction (desc)
        """
        aggregated = await self.aggregate_signals()
        
        # Filter by minimum wallets
        filtered = [s for s in aggregated if s.wallet_count >= min_wallets]
        
        # Calculate scores and convert to schema
        signals = []
        for agg in filtered:
            alpha_score, alpha_breakdown = self.calculate_alpha_score(agg)
            
            # Skip lottery tickets if filter is enabled
            if hide_lottery and alpha_score < 30:
                continue
            
            rec_size, kelly_breakdown = self.calculate_kelly_size(
                current_price=agg.current_price,
                alpha_score=alpha_score,
                wallet_count=agg.wallet_count,
                user_balance=user_balance,
                kelly_multiplier=kelly_multiplier,
                max_risk_cap=max_risk_cap
            )
            
            signals.append(SignalSchema(
                group_key=agg.group_key,
                market_id=agg.market_id,
                market_name=agg.market_name,
                outcome_label=agg.outcome_label,
                direction=agg.direction,
                category=agg.category,
                wallet_count=agg.wallet_count,
                total_conviction=round(agg.total_conviction, 2),
                avg_entry_price=round(agg.avg_entry_price, 4),
                current_price=round(agg.current_price, 4),
                alpha_score=alpha_score,
                alpha_breakdown=alpha_breakdown,
                recommended_size=rec_size,
                kelly_breakdown=kelly_breakdown,
            ))
        
        # Sort: wallet_count desc, alpha_score desc, conviction desc
        signals.sort(
            key=lambda s: (-s.wallet_count, -s.alpha_score, -s.total_conviction)
        )
        
        return signals
    
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
                    status = "VALIDATED"  # No consensus either way
                
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
