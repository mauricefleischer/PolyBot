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

export interface Signal {
    group_key: string;
    market_id: string;
    market_name: string;
    outcome_label: string;
    direction: 'YES' | 'NO';
    category: string;
    wallet_count: number;
    total_conviction: number;
    avg_entry_price: number;
    current_price: number;
    alpha_score: number;
    alpha_breakdown: string[];
    recommended_size: number;
    kelly_breakdown: KellyBreakdown;
}

export interface RiskSettings {
    kellyMultiplier: number;
    maxRiskCap: number;
    minWallets: number;
    hideLottery: boolean;
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
