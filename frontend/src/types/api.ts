/**
 * API Types for the Consensus Terminal
 */

export interface KellyBreakdown {
    net_odds: number;
    real_prob: number;
    prob_boosts?: string[];
    kelly_raw: number;
    kelly_multiplier?: number;
    stake_percent?: number;
    capped_percent?: number;
    max_risk_cap?: number;
    reason?: string;
    error?: string;
}

export interface AlphaBreakdown {
    base: number;
    flb: number;
    momentum: number;
    smart_short: number;
    freshness: number;
    total: number;
    details: string[];
}

export interface WhaleMeta {
    avg_score: number;
    has_elite: boolean;
    has_bagholder: boolean;
    wallet_tiers: Record<string, string>;
}

export interface WhaleScore {
    address: string;
    total_score: number;
    roi_score: number;
    discipline_score: number;
    precision_score: number;
    timing_score: number;
    tier: 'ELITE' | 'PRO' | 'STD' | 'WEAK' | 'UNRATED';
    tags: string[];
    trade_count: number;
    details: Record<string, string>;
}

export interface Signal {
    group_key: string;
    market_id: string;
    market_name: string;
    market_slug?: string;
    outcome_label: string;
    direction: 'YES' | 'NO';
    category: string;
    wallet_count: number;
    total_conviction: number;
    avg_entry_price: number;
    current_price: number;
    alpha_score: number;
    alpha_breakdown: AlphaBreakdown;
    recommended_size: number;
    kelly_breakdown: KellyBreakdown;
    consensus: SignalConsensus;
    whale_meta?: WhaleMeta; // DEPRECATED
}

export interface ConsensusContributor {
    address: string;
    score: number;
    tier: string;
}

export interface SignalConsensus {
    count: number;
    has_elite: boolean;
    weighted_score: number;
    contributors: ConsensusContributor[];
}

export interface RiskSettings {
    kellyMultiplier: number;
    maxRiskCap: number;
    minWallets: number;
    hideLottery: boolean;
    connectedWallet?: string;
    longshotTolerance: number;
    trendMode: boolean;
    yieldTriggerPrice: number;
    yieldFixedPct: number;
    yieldMinWhales: number;
}

export interface PortfolioPosition {
    market_id: string;
    market_name: string;
    outcome_label: string;
    direction: 'YES' | 'NO';
    size_usdc: number;
    entry_price: number;
    current_price: number;
    pnl_percent: number;
    status: 'VALIDATED' | 'DIVERGENCE' | 'TRIM';
    whale_consensus: boolean;
    whale_count: number;
}

export interface Portfolio {
    wallet_address: string;
    usdc_balance: number;
    total_invested: number;
    total_pnl: number;
    positions: PortfolioPosition[];
    validated_count: number;
    divergence_count: number;
}

export interface WalletConfigRequest {
    action: 'add' | 'remove';
    address: string;
}

export interface WalletConfigResponse {
    success: boolean;
    message: string;
    wallets: string[];
}
