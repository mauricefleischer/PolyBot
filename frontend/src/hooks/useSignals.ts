import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Signal, Portfolio, WalletConfigRequest, WalletConfigResponse, RiskSettings, WhaleScore } from '../types/api';

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
    params.set('longshot_tolerance', (riskSettings.longshotTolerance ?? 1.0).toString());
    params.set('trend_mode', (riskSettings.trendMode ?? true).toString());
    params.set('flb_correction_mode', riskSettings.flbCorrectionMode || 'STANDARD');
    params.set('optimism_tax', (riskSettings.optimismTax ?? true).toString());
    params.set('min_whale_tier', riskSettings.minWhaleTier || 'ALL');
    params.set('ignore_bagholders', (riskSettings.ignoreBagholders ?? true).toString());
    params.set('yield_trigger_price', (riskSettings.yieldTriggerPrice ?? 0.85).toString());
    params.set('yield_fixed_pct', (riskSettings.yieldFixedPct ?? 0.10).toString());
    params.set('yield_min_whales', (riskSettings.yieldMinWhales ?? 3).toString());

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
async function fetchWallets(): Promise<{ wallets: string[]; names: Record<string, string>; count: number }> {
    const response = await fetch(`${API_BASE}/config/wallets`);
    if (!response.ok) {
        throw new Error('Failed to fetch wallets');
    }
    return response.json();
}

/**
 * Fetch whale scores
 */
async function fetchWhaleScores(): Promise<WhaleScore[]> {
    const response = await fetch(`${API_BASE}/whale-scores`);
    if (!response.ok) {
        throw new Error('Failed to fetch whale scores');
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
    longshotTolerance: 1.0,
    trendMode: true,
    flbCorrectionMode: 'STANDARD',
    optimismTax: true,
    minWhaleTier: 'ALL',
    ignoreBagholders: true,
    yieldTriggerPrice: 0.85,
    yieldFixedPct: 0.10,
    yieldMinWhales: 3,
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
async function setWalletName(params: { address: string; name: string }) {
    const response = await fetch(`${API_BASE}/config/wallet-name?address=${params.address}&name=${encodeURIComponent(params.name)}`, {
        method: 'PUT',
    });
    if (!response.ok) throw new Error('Failed to set wallet name');
    return response.json();
}

export function useWalletConfig() {
    const queryClient = useQueryClient();

    const mutation = useMutation({
        mutationFn: configureWallet,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['wallets'] });
            queryClient.invalidateQueries({ queryKey: ['signals'] });
        },
    });

    const nameMutation = useMutation({
        mutationFn: setWalletName,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['wallets'] });
        },
    });

    return {
        addWallet: (address: string) => mutation.mutateAsync({ action: 'add', address }),
        removeWallet: (address: string) => mutation.mutateAsync({ action: 'remove', address }),
        setWalletName: (address: string, name: string) => nameMutation.mutateAsync({ address, name }),
        isPending: mutation.isPending || nameMutation.isPending,
    };
}

/**
 * Hook to fetch whale scores
 */
export function useWhaleScores() {
    return useQuery({
        queryKey: ['whale-scores'],
        queryFn: fetchWhaleScores,
        refetchInterval: 60000, // 1 minute polling
    });
}
