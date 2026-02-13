"""
Configuration module for the Consensus Terminal backend.
Loads environment variables and provides typed settings.
"""
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Polygon RPC Configuration
    polygon_rpc_url: str = Field(
        default="https://polygon-rpc.com",
        description="Polygon RPC endpoint (Alchemy/Infura recommended)"
    )
    
    # Polymarket Gamma API
    gamma_api_base_url: str = Field(
        default="https://gamma-api.polymarket.com",
        description="Polymarket Gamma API base URL"
    )
    
    # Rate Limiting
    rate_limit_requests_per_second: int = Field(
        default=10,
        description="Maximum requests per second to external APIs"
    )
    
    # Cache TTL Settings (in seconds)
    market_cache_ttl: int = Field(
        default=60,
        description="TTL for market metadata cache"
    )
    price_cache_ttl: int = Field(
        default=5,
        description="TTL for price data cache"
    )
    
    # Risk Management
    default_risk_percent: float = Field(
        default=0.05,
        description="Default risk percentage for position sizing (5%)"
    )
    default_user_balance: float = Field(
        default=1000.0,
        description="Default USDC balance for unconnected users"
    )
    
    # Contract Addresses (Polygon)
    usdc_contract_address: str = Field(
        default="0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
        description="USDC contract address on Polygon"
    )
    conditional_tokens_address: str = Field(
        default="0x4D97DCd97eC945f40cF65F87097ACe5EA0476045",
        description="Polymarket Conditional Tokens (ERC1155) on Polygon"
    )
    
    # Wallets file path (Absolute, relative to backend root)
    wallets_file_path: str = Field(
        default=str(Path(__file__).resolve().parent.parent.parent / "wallets.json"),
        description="Path to persistent wallets storage"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience export
settings = get_settings()
