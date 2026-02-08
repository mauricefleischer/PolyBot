/**
 * useBalance hook - Fetches USDC balance from Polygon for a wallet
 */
import { useQuery } from '@tanstack/react-query';

const API_BASE = 'http://localhost:8000/api/v1';

interface BalanceResponse {
    wallet: string;
    usdc_balance: number;
    currency: string;
    chain: string;
}

async function fetchBalance(walletAddress: string): Promise<number> {
    if (!walletAddress) return 0;

    try {
        const response = await fetch(`${API_BASE}/user/balance?wallet=${walletAddress}`);
        if (!response.ok) {
            console.warn('Failed to fetch balance');
            return 0;
        }
        const data: BalanceResponse = await response.json();
        return data.usdc_balance;
    } catch (error) {
        console.warn('Error fetching balance:', error);
        return 0;
    }
}

export function useBalance(walletAddress: string | null | undefined) {
    return useQuery({
        queryKey: ['balance', walletAddress],
        queryFn: () => fetchBalance(walletAddress || ''),
        enabled: !!walletAddress && walletAddress.length === 42,
        refetchInterval: 30000, // Refresh every 30 seconds
        staleTime: 15000,
    });
}
