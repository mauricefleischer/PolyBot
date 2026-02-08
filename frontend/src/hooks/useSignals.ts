import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Signal, Portfolio, WalletConfigRequest, WalletConfigResponse, RiskSettings } from '../types/api';

const API_BASE = 'http://localhost:8000/api/v1';

/**
 * Fetch signals from the API with risk settings
 */
async function fetchSignals(
    userBalance: number,
    riskSettings: RiskSettings
): Promise<Signal[]> {
    const params = new URLSearchParams();
    params.set('min_wallets', riskSettings.minWallets.toString());
    params.set('user_balance', userBalance.toString());
    params.set('kelly_multiplier', riskSettings.kellyMultiplier.toString());
    params.set('max_risk_cap', riskSettings.maxRiskCap.toString());
    params.set('hide_lottery', riskSettings.hideLottery.toString());

    const response = await fetch(`${API_BASE}/signals?${params}`);
    if (!response.ok) {
        throw new Error('Failed to fetch signals');
    }
    return response.json();
}

/**
 * Fetch user portfolio
 */
async function fetchPortfolio(walletAddress: string): Promise<Portfolio> {
    const response = await fetch(`${API_BASE}/user/portfolio?wallet=${walletAddress}`);
    if (!response.ok) {
        throw new Error('Failed to fetch portfolio');
    }
    return response.json();
}

/**
 * Configure wallets (add/remove)
 */
async function configureWallet(request: WalletConfigRequest): Promise<WalletConfigResponse> {
    const response = await fetch(`${API_BASE}/config/wallets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
    });
    if (!response.ok) {
        throw new Error('Failed to configure wallet');
    }
    return response.json();
}

/**
 * Fetch tracked wallets
 */
async function fetchWallets(): Promise<{ wallets: string[]; count: number }> {
    const response = await fetch(`${API_BASE}/config/wallets`);
    if (!response.ok) {
        throw new Error('Failed to fetch wallets');
    }
    return response.json();
}

// ============================================================================
// Default Risk Settings
// ============================================================================

export const DEFAULT_RISK_SETTINGS: RiskSettings = {
    kellyMultiplier: 0.25,
    maxRiskCap: 0.05,
    minWallets: 2,
    hideLottery: false,
};

// ============================================================================
// React Query Hooks
// ============================================================================

/**
 * Hook to fetch and poll signals with risk settings
 */
export function useSignals(userBalance: number, riskSettings: RiskSettings = DEFAULT_RISK_SETTINGS) {
    return useQuery({
        queryKey: ['signals', userBalance, riskSettings],
        queryFn: () => fetchSignals(userBalance, riskSettings),
        refetchInterval: 5000, // 5 second polling
        staleTime: 2000, // 2 second stale time
    });
}

/**
 * Hook to fetch user portfolio
 */
export function usePortfolio(walletAddress: string | null) {
    return useQuery({
        queryKey: ['portfolio', walletAddress],
        queryFn: () => fetchPortfolio(walletAddress!),
        enabled: !!walletAddress,
        refetchInterval: 10000, // 10 second polling
        staleTime: 5000,
    });
}

/**
 * Hook to fetch tracked wallets
 */
export function useWallets() {
    return useQuery({
        queryKey: ['wallets'],
        queryFn: fetchWallets,
    });
}

/**
 * Hook to add/remove wallets
 */
export function useWalletMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: configureWallet,
        onSuccess: () => {
            // Invalidate signals and wallets queries
            queryClient.invalidateQueries({ queryKey: ['wallets'] });
            queryClient.invalidateQueries({ queryKey: ['signals'] });
        },
    });
}
