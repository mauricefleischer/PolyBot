import { Wallet, Activity, TrendingUp, RefreshCw } from 'lucide-react';
import { formatCurrency } from '../lib/utils';

interface HeaderProps {
    usdcBalance?: number | null;
    walletCount: number;
    signalCount: number;
    isRefreshing?: boolean;
    onRefresh?: () => void;
}

export function Header({
    usdcBalance,
    walletCount,
    signalCount,
    isRefreshing,
    onRefresh,
}: HeaderProps) {
    return (
        <header className="bg-white border-b border-slate-200">
            {/* Main Header */}
            <div className="px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-slate-900 rounded-lg flex items-center justify-center">
                        <TrendingUp className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h1 className="text-xl font-bold text-slate-900">
                            Consensus Terminal
                        </h1>
                        <p className="text-xs text-slate-500">
                            Whale Position Aggregator
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    {/* Liquidity Display */}
                    <div className="flex items-center gap-2 bg-slate-100 rounded-lg px-4 py-2">
                        <Wallet className="w-4 h-4 text-slate-500" />
                        <span className="text-slate-500 text-sm">Available:</span>
                        <span className="text-slate-900 text-xl font-bold tabular-nums">
                            {usdcBalance != null ? formatCurrency(usdcBalance) : '—'}
                        </span>
                    </div>

                    {/* Refresh Button */}
                    <button
                        onClick={onRefresh}
                        disabled={isRefreshing}
                        className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 transition-colors disabled:opacity-50"
                        title="Refresh data"
                    >
                        <RefreshCw
                            className={`w-5 h-5 text-slate-600 ${isRefreshing ? 'animate-spin' : ''}`}
                        />
                    </button>
                </div>
            </div>

            {/* Context Bar */}
            <div className="bg-slate-100 px-6 py-2 flex items-center gap-6 text-sm">
                <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-emerald-600" />
                    <span className="text-slate-500">Status:</span>
                    <span className="text-emerald-700 font-semibold">LIVE</span>
                </div>

                <div className="w-px h-4 bg-slate-300" />

                <div className="flex items-center gap-2">
                    <span className="text-slate-500">Tracked Wallets:</span>
                    <span className="text-slate-900 font-semibold tabular-nums">{walletCount}</span>
                </div>

                <div className="w-px h-4 bg-slate-300" />

                <div className="flex items-center gap-2">
                    <span className="text-slate-500">Active Signals:</span>
                    <span className="text-slate-900 font-semibold tabular-nums">{signalCount}</span>
                </div>

                <div className="w-px h-4 bg-slate-300" />

                <div className="flex items-center gap-2">
                    <span className="text-slate-500">Refresh:</span>
                    <span className="text-slate-600 font-mono">5s</span>
                </div>
            </div>
        </header>
    );
}
