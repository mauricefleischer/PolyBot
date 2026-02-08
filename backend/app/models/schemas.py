"""
Pydantic models and dataclasses for the Consensus Terminal.
Strict typing for financial data validation.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


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
    alpha_score: int = Field(ge=0, le=100, description="Becker Alpha Score")
    alpha_breakdown: List[str] = Field(default=[], description="Score breakdown for tooltip")
    
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
