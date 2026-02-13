"""
FastAPI Entrypoint for the Consensus Terminal.
Exposes API endpoints for signals, portfolio, and wallet management.
"""
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.models.schemas import (
    SignalSchema,
    PortfolioSchema,
    WalletConfigRequest,
    WalletAction,
    WhaleScoreSchema,
)
from app.services.aggregator import consensus_engine
from app.services.polymarket import gamma_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: Initialize market cache
    print("Initializing market cache...")
    await gamma_client.initialize_market_cache()
    print("Market cache initialized.")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="Consensus Terminal API",
    description="High-performance whale consensus aggregator for Polymarket",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "Consensus Terminal",
        "version": "1.0.0",
    }


@app.get("/api/v1/signals", response_model=list[SignalSchema])
async def get_signals(
    min_wallets: int = Query(default=1, ge=1, le=10, description="Minimum wallet consensus"),
    user_balance: Optional[float] = Query(default=None, ge=0, description="User USDC balance for sizing"),
    kelly_multiplier: float = Query(default=0.25, ge=0.1, le=1.0, description="Kelly fraction"),
    max_risk_cap: float = Query(default=0.05, ge=0.01, le=0.20, description="Maximum risk per trade"),
    hide_lottery: bool = Query(default=False, description="Hide signals with Alpha Score < 30"),
    longshot_tolerance: float = Query(default=1.0, ge=0.5, le=1.5, description="FLB penalty scaling"),
    trend_mode: bool = Query(default=True, description="Enable momentum scoring"),
    flb_correction_mode: str = Query(default="STANDARD", description="AGGRESSIVE, STANDARD, or OFF"),
    optimism_tax: bool = Query(default=True, description="Apply 5% Optimism Tax for Sports/Politics"),
    min_whale_tier: str = Query(default="ALL", description="ALL, PRO, or ELITE"),
    ignore_bagholders: bool = Query(default=True, description="Exclude wallets with Discipline < 30"),
    yield_trigger_price: float = Query(default=0.85, ge=0.01, le=1.0, description="Yield Mode trigger price"),
    yield_fixed_pct: float = Query(default=0.10, ge=0.01, le=1.0, description="Yield Mode fixed size"),
    yield_min_whales: int = Query(default=3, ge=1, description="Min whales for Yield Mode"),
):
    """
    Get ranked consensus signals from tracked whales.
    
    Returns signals sorted by:
    1. Wallet Count (descending)
    2. Alpha Score (descending)
    3. Total Conviction (descending)
    
    Kelly Criterion sizing with configurable parameters.
    """
    try:
        signals = await consensus_engine.get_ranked_signals(
            min_wallets=min_wallets,
            user_balance=user_balance,
            kelly_multiplier=kelly_multiplier,
            max_risk_cap=max_risk_cap,
            hide_lottery=hide_lottery,
            longshot_tolerance=longshot_tolerance,
            trend_mode=trend_mode,
            flb_correction_mode=flb_correction_mode,
            optimism_tax=optimism_tax,
            min_whale_tier=min_whale_tier,
            ignore_bagholders=ignore_bagholders,
            yield_trigger_price=yield_trigger_price,
            yield_fixed_pct=yield_fixed_pct,
            yield_min_whales=yield_min_whales,
        )
        return signals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/user/portfolio", response_model=PortfolioSchema)
async def get_portfolio(
    wallet: str = Query(..., min_length=42, max_length=42, description="User wallet address"),
):
    """
    Get user's portfolio compared against whale consensus.
    
    Returns:
    - Active positions with PnL
    - Validation status (VALIDATED, DIVERGENCE, TRIM)
    - USDC balance
    """
    try:
        portfolio = await consensus_engine.get_user_portfolio(wallet)
        return portfolio
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class WalletConfigResponse(BaseModel):
    """Response for wallet configuration changes."""
    success: bool
    message: str
    wallets: list[str]


@app.post("/api/v1/config/wallets", response_model=WalletConfigResponse)
async def configure_wallets(request: WalletConfigRequest):
    """
    Add or remove wallets from tracking.
    
    Wallets are persisted to SQLite database.
    """
    from app.services.database import db_service
    
    try:
        if request.action == WalletAction.ADD:
            # Add to both legacy engine and database
            success = consensus_engine.add_wallet(request.address)
            db_service.add_wallet(request.address, request.address[:10] + "...")
            message = f"Wallet {request.address} added" if success else "Wallet already tracked"
        else:
            success = consensus_engine.remove_wallet(request.address)
            db_service.remove_wallet(request.address)
            message = f"Wallet {request.address} removed" if success else "Wallet not found"
        
        return WalletConfigResponse(
            success=success,
            message=message,
            wallets=consensus_engine.get_wallets(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/config/wallets")
async def get_wallets():
    """Get list of currently tracked wallets with names."""
    from app.services.database import db_service
    
    wallet_names = db_service.get_wallet_names()
    wallets = consensus_engine.get_wallets()
    
    return {
        "wallets": wallets,
        "names": wallet_names,
        "count": len(wallets),
    }


@app.get("/api/v1/whale-scores", response_model=list[WhaleScoreSchema])
async def get_whale_scores():
    """Get Smart Money Scores for all tracked wallets."""
    from app.services.database import db_service
    
    scores = db_service.get_all_whale_scores()
    return scores


@app.post("/api/v1/whale-scores/refresh")
async def refresh_whale_scores():
    """Trigger a refresh of whale scores."""
    # This is implicitly done in get_signals, but we can expose it
    # if we want to separate scoring from signal generation.
    # For now, we'll just return success as get_signals handles it lazy-ish.
    return {"message": "Scores refresh on signal generation"}


# ============================================================================
# Settings Endpoints
# ============================================================================

class SettingsRequest(BaseModel):
    """Settings update request."""
    kelly_multiplier: Optional[float] = None
    max_risk_cap: Optional[float] = None
    min_wallets: Optional[int] = None
    hide_lottery: Optional[bool] = None
    connected_wallet: Optional[str] = None
    longshot_tolerance: Optional[float] = None
    trend_mode: Optional[bool] = None
    flb_correction_mode: Optional[str] = None
    optimism_tax: Optional[bool] = None
    min_whale_tier: Optional[str] = None
    ignore_bagholders: Optional[bool] = None
    yield_trigger_price: Optional[float] = None
    yield_fixed_pct: Optional[float] = None
    yield_min_whales: Optional[int] = None


class SettingsResponse(BaseModel):
    """Settings response."""
    kelly_multiplier: float
    max_risk_cap: float
    min_wallets: int
    hide_lottery: bool
    connected_wallet: Optional[str]
    longshot_tolerance: float
    trend_mode: bool
    flb_correction_mode: str
    optimism_tax: bool
    min_whale_tier: str
    ignore_bagholders: bool
    yield_trigger_price: float = 0.85
    yield_fixed_pct: float = 0.10
    yield_min_whales: int = 3


@app.get("/api/v1/settings", response_model=SettingsResponse)
async def get_settings():
    """Get user settings from database."""
    from app.services.database import db_service
    
    settings_data = db_service.get_settings()
    return SettingsResponse(
        kelly_multiplier=settings_data.kelly_multiplier,
        max_risk_cap=settings_data.max_risk_cap,
        min_wallets=settings_data.min_wallets,
        hide_lottery=settings_data.hide_lottery,
        connected_wallet=settings_data.connected_wallet,
        longshot_tolerance=settings_data.longshot_tolerance,
        trend_mode=settings_data.trend_mode,
        flb_correction_mode=settings_data.flb_correction_mode,
        optimism_tax=settings_data.optimism_tax,
        min_whale_tier=settings_data.min_whale_tier,
        ignore_bagholders=settings_data.ignore_bagholders,
        yield_trigger_price=getattr(settings_data, "yield_trigger_price", 0.85),
        yield_fixed_pct=getattr(settings_data, "yield_fixed_pct", 0.10),
        yield_min_whales=getattr(settings_data, "yield_min_whales", 3),
    )


@app.put("/api/v1/settings", response_model=SettingsResponse)
async def update_settings(request: SettingsRequest):
    """Update user settings in database."""
    from app.services.database import db_service
    
    updated = db_service.update_settings(
        kelly_multiplier=request.kelly_multiplier,
        max_risk_cap=request.max_risk_cap,
        min_wallets=request.min_wallets,
        hide_lottery=request.hide_lottery,
        connected_wallet=request.connected_wallet,
        longshot_tolerance=request.longshot_tolerance,
        trend_mode=request.trend_mode,
        flb_correction_mode=request.flb_correction_mode,
        optimism_tax=request.optimism_tax,
        min_whale_tier=request.min_whale_tier,
        ignore_bagholders=request.ignore_bagholders,
        yield_trigger_price=request.yield_trigger_price,
        yield_fixed_pct=request.yield_fixed_pct,
        yield_min_whales=request.yield_min_whales,
    )
    
    return SettingsResponse(
        kelly_multiplier=updated.kelly_multiplier,
        max_risk_cap=updated.max_risk_cap,
        min_wallets=updated.min_wallets,
        hide_lottery=updated.hide_lottery,
        connected_wallet=updated.connected_wallet,
        longshot_tolerance=updated.longshot_tolerance,
        trend_mode=updated.trend_mode,
        flb_correction_mode=updated.flb_correction_mode,
        optimism_tax=updated.optimism_tax,
        min_whale_tier=updated.min_whale_tier,
        ignore_bagholders=updated.ignore_bagholders,
        yield_trigger_price=getattr(updated, "yield_trigger_price", 0.85),
        yield_fixed_pct=getattr(updated, "yield_fixed_pct", 0.10),
        yield_min_whales=getattr(updated, "yield_min_whales", 3),
    )


@app.put("/api/v1/config/wallet-name")
async def set_wallet_name(address: str, name: str):
    """Set a display name for a wallet address."""
    from app.services.database import db_service
    
    db_service.set_wallet_name(address, name)
    return {"success": True, "address": address, "name": name}


@app.get("/api/v1/user/balance")
async def get_user_balance(
    wallet: str = Query(..., min_length=42, max_length=42, description="User wallet address"),
):
    """
    Get USDC balance for a wallet on Polygon.
    
    Returns:
    - usdc_balance: Available USDC (not in positions)
    """
    from app.services.chain_data import web3_client
    
    try:
        balance = await web3_client.get_usdc_balance(wallet)
        return {
            "wallet": wallet,
            "usdc_balance": balance,
            "currency": "USDC",
            "chain": "Polygon",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "tracked_wallets": len(consensus_engine.get_wallets()),
        "cache_status": "active",
        "database": "sqlite",
    }
