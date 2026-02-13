/**
 * useSettings hook - Syncs settings with server API
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { RiskSettings } from '../types/api';

const API_BASE = 'http://localhost:8000/api/v1';

export const DEFAULT_RISK_SETTINGS: RiskSettings = {
    kellyMultiplier: 0.25,
    maxRiskCap: 0.05,
    minWallets: 2,
    hideLottery: false,
    connectedWallet: undefined,
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

interface ServerSettings {
    kelly_multiplier: number;
    max_risk_cap: number;
    min_wallets: number;
    hide_lottery: boolean;
    connected_wallet: string | null;
    longshot_tolerance: number;
    trend_mode: boolean;
    flb_correction_mode: 'AGGRESSIVE' | 'STANDARD' | 'OFF';
    optimism_tax: boolean;
    min_whale_tier: 'ALL' | 'PRO' | 'ELITE';
    ignore_bagholders: boolean;
    yield_trigger_price: number;
    yield_fixed_pct: number;
    yield_min_whales: number;
}

// Convert server format to frontend format
function fromServer(server: ServerSettings): RiskSettings {
    return {
        kellyMultiplier: server.kelly_multiplier,
        maxRiskCap: server.max_risk_cap,
        minWallets: server.min_wallets,
        hideLottery: server.hide_lottery,
        connectedWallet: server.connected_wallet || undefined,
        longshotTolerance: server.longshot_tolerance ?? 1.0,
        trendMode: server.trend_mode ?? true,
        flbCorrectionMode: server.flb_correction_mode ?? 'STANDARD',
        optimismTax: server.optimism_tax ?? true,
        minWhaleTier: server.min_whale_tier ?? 'ALL',
        ignoreBagholders: server.ignore_bagholders ?? true,
        yieldTriggerPrice: server.yield_trigger_price ?? 0.85,
        yieldFixedPct: server.yield_fixed_pct ?? 0.10,
        yieldMinWhales: server.yield_min_whales ?? 3,
    };
}

// Convert frontend format to server format
function toServer(settings: Partial<RiskSettings>): Partial<ServerSettings> {
    const result: Partial<ServerSettings> = {};
    if (settings.kellyMultiplier !== undefined) result.kelly_multiplier = settings.kellyMultiplier;
    if (settings.maxRiskCap !== undefined) result.max_risk_cap = settings.maxRiskCap;
    if (settings.minWallets !== undefined) result.min_wallets = settings.minWallets;
    if (settings.hideLottery !== undefined) result.hide_lottery = settings.hideLottery;
    if (settings.connectedWallet !== undefined) result.connected_wallet = settings.connectedWallet;
    if (settings.longshotTolerance !== undefined) result.longshot_tolerance = settings.longshotTolerance;
    if (settings.trendMode !== undefined) result.trend_mode = settings.trendMode;
    if (settings.flbCorrectionMode !== undefined) result.flb_correction_mode = settings.flbCorrectionMode;
    if (settings.optimismTax !== undefined) result.optimism_tax = settings.optimismTax;
    if (settings.minWhaleTier !== undefined) result.min_whale_tier = settings.minWhaleTier;
    if (settings.ignoreBagholders !== undefined) result.ignore_bagholders = settings.ignoreBagholders;
    if (settings.yieldTriggerPrice !== undefined) result.yield_trigger_price = settings.yieldTriggerPrice;
    if (settings.yieldFixedPct !== undefined) result.yield_fixed_pct = settings.yieldFixedPct;
    if (settings.yieldMinWhales !== undefined) result.yield_min_whales = settings.yieldMinWhales;
    return result;
}

async function fetchSettings(): Promise<RiskSettings> {
    try {
        const response = await fetch(`${API_BASE}/settings`);
        if (!response.ok) throw new Error('Failed to fetch settings');
        const data: ServerSettings = await response.json();
        return fromServer(data);
    } catch (error) {
        console.warn('Failed to load settings from server, using defaults');
        return DEFAULT_RISK_SETTINGS;
    }
}

async function updateSettings(settings: Partial<RiskSettings>): Promise<RiskSettings> {
    const response = await fetch(`${API_BASE}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(toServer(settings)),
    });
    if (!response.ok) throw new Error('Failed to update settings');
    const data: ServerSettings = await response.json();
    return fromServer(data);
}

export function useSettings() {
    const queryClient = useQueryClient();

    const query = useQuery({
        queryKey: ['settings'],
        queryFn: fetchSettings,
        staleTime: 30000, // 30 seconds
        refetchOnWindowFocus: false,
    });

    const mutation = useMutation({
        mutationFn: updateSettings,
        onMutate: async (newSettingsPartial) => {
            // Cancel any outgoing refetches
            await queryClient.cancelQueries({ queryKey: ['settings'] });

            // Snapshot the previous value
            const previousSettings = queryClient.getQueryData<RiskSettings>(['settings']);

            // Optimistically update to the new value
            if (previousSettings) {
                queryClient.setQueryData<RiskSettings>(['settings'], {
                    ...previousSettings,
                    ...newSettingsPartial,
                });
            }

            return { previousSettings };
        },
        onError: (_err, _newSettings, context) => {
            // Rollback on error
            if (context?.previousSettings) {
                queryClient.setQueryData(['settings'], context.previousSettings);
            }
        },
        onSettled: () => {
            // Always refetch after error or success to ensure sync
            queryClient.invalidateQueries({ queryKey: ['settings'] });
        },
    });

    return {
        settings: query.data ?? DEFAULT_RISK_SETTINGS,
        isLoading: query.isLoading,
        updateSettings: mutation.mutate,
        isUpdating: mutation.isPending,
    };
}
