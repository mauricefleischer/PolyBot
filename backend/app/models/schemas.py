"""
Pydantic models and dataclasses for the Consensus Terminal.
Strict typing for financial data validation.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict


@dataclass
class ScoringConfig:
    """User-tunable scoring parameters for Alpha Score 2.0."""
    longshot_tolerance: float = 1.0   # 0.5 (lenient) to 1.5 (strict)
    trend_mode: bool = True           # Enable/disable momentum scoring


@dataclass
class ScoreBreakdown:
    """Structured Alpha Score 2.0 breakdown for UI tooltips."""
    base: int = 50
    flb: int = 0            # -40 to +15
    momentum: int = 0       # -10 to +10
    smart_short: int = 0    # 0 to +20
    freshness: int = 0      # 0 to +10
    total: int = 50
    details: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "base": self.base,
            "flb": self.flb,
            "momentum": self.momentum,
            "smart_short": self.smart_short,
            "freshness": self.freshness,
            "total": self.total,
            "details": self.details,
        }


@dataclass
class RawSignal:
    """
    Internal representation of a single wallet position.
    Used during the data ingestion and normalization phase.
    """
    wallet_address: str
    market_id: str
    outcome_label: str  # e.g., "Trump", "Biden", "25bps cut"
    direction: str  # "YES" or "NO"
    entry_price: float
    current_price: float
    size_usdc: float
    category: str  # "Sports", "Politics", "Finance", "Entertainment"
    market_name: str = ""
    outcome_index: int = 0
    market_slug: str = ""
    token_id: str = ""  # CLOB token ID for price history lookups
    timestamp: Optional[datetime] = None  # Position creation time for freshness


class SignalSchema(BaseModel):
    """
    API response schema for aggregated consensus signals.
    Represents a grouped position across multiple wallets.
    """
    model_config = ConfigDict(strict=False)  # Allow dict fields
    
    # Identification
    group_key: str = Field(description="Unique key: market_id_outcome_direction")
    market_id: str = Field(description="Polymarket market/condition ID")
    market_name: str = Field(description="Human-readable market name")
    market_slug: str = Field(default="", description="Polymarket event slug for linking")
    outcome_label: str = Field(description="Outcome being bet on")
    direction: str = Field(description="YES or NO")
    category: str = Field(description="Market category")
    
    # Consensus Metrics
    wallet_count: int = Field(ge=0, description="Number of wallets in consensus")
    total_conviction: float = Field(ge=0, description="Total USDC invested")
    
    # Pricing
    avg_entry_price: float = Field(ge=0, le=1, description="Weighted average entry")
    current_price: float = Field(ge=0, le=1, description="Current market price")
    
    # Scoring
    alpha_score: int = Field(ge=0, le=100, description="Becker Alpha Score 2.0")
    alpha_breakdown: dict = Field(default={}, description="Structured score breakdown for tooltip")
    
    # Risk Sizing (calculated for default user)
    recommended_size: float = Field(ge=0, description="Recommended position size in USDC")
    kelly_breakdown: dict = Field(default={}, description="Kelly calculation breakdown for tooltip")


class PortfolioPositionSchema(BaseModel):
    """Schema for a single user position in the portfolio."""
    model_config = ConfigDict(strict=True)
    
    market_id: str
    market_name: str
    outcome_label: str
    direction: str
    size_usdc: float
    entry_price: float
    current_price: float
    pnl_percent: float = Field(description="Profit/Loss percentage")
    
    # Consensus validation
    status: str = Field(description="VALIDATED, DIVERGENCE, or TRIM")
    whale_consensus: bool = Field(description="Whether whales agree with this position")
    whale_count: int = Field(ge=0, description="Number of whales with same position")


class PortfolioSchema(BaseModel):
    """Complete portfolio response with all positions."""
    model_config = ConfigDict(strict=True)
    
    wallet_address: str
    usdc_balance: float = Field(ge=0)
    total_invested: float = Field(ge=0)
    total_pnl: float
    positions: list[PortfolioPositionSchema]
    validated_count: int = Field(ge=0)
    divergence_count: int = Field(ge=0)


class WalletAction(str, Enum):
    """Wallet configuration actions."""
    ADD = "add"
    REMOVE = "remove"


class WalletConfigRequest(BaseModel):
    """Request body for wallet configuration endpoint."""
    action: WalletAction
    address: str = Field(
        min_length=42,
        max_length=42,
        pattern=r"^0x[a-fA-F0-9]{40}$",
        description="Ethereum wallet address"
    )


class WalletConfigResponse(BaseModel):
    """Response for wallet configuration changes."""
    success: bool
    message: str
    wallets: list[str]
