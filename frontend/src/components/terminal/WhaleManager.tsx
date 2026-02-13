import { useState } from 'react';
import { Trash2, Plus, AlertCircle, Check } from 'lucide-react';
import { useWallets, useWhaleScores, useWalletConfig } from '../../hooks/useSignals';
import { Tooltip, WhaleScoreTooltip } from '../ui/Tooltip';

export function WhaleManager() {
    const { data: walletsData, isLoading: walletsLoading } = useWallets();
    const { data: whaleScores = [] } = useWhaleScores();
    const { addWallet, removeWallet, setWalletName, isPending } = useWalletConfig();

    const [newAddress, setNewAddress] = useState('');
    const [newName, setNewName] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    const handleAddWallet = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSuccess(null);

        if (!newAddress.match(/^0x[a-fA-F0-9]{40}$/)) {
            setError('Invalid wallet address format');
            return;
        }

        try {
            await addWallet(newAddress);

            if (newName.trim()) {
                await setWalletName(newAddress, newName.trim());
            }

            setSuccess(`Wallet added: ${newName || newAddress.slice(0, 10)}...`);
            setNewAddress('');
            setNewName('');
        } catch {
            setError('Failed to add wallet');
        }
    };

    const trackedWallets = walletsData?.wallets || [];
    const walletNames = walletsData?.names || {};

    // Merge wallet data with scores
    const walletRows = trackedWallets.map(address => {
        const scoreData = whaleScores.find(s => s.address.toLowerCase() === address.toLowerCase());
        return {
            address,
            name: walletNames[address] || '',
            score: scoreData,
        };
    });

    // Sort by score (desc), then address
    walletRows.sort((a, b) => {
        const scoreA = a.score?.total_score || 0;
        const scoreB = b.score?.total_score || 0;
        return scoreB - scoreA;
    });

    if (walletsLoading) {
        return <div className="p-12 text-center text-slate-500">Loading wallet data...</div>;
    }

    return (
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
                <h3 className="font-bold text-slate-700">Tracked Whales ({walletRows.length})</h3>
                <div className="text-xs text-slate-500">
                    High-Density CRM View
                </div>
            </div>

            {/* Add Wallet Form */}
            <form onSubmit={handleAddWallet} className="p-4 bg-white border-b border-slate-200">
                <div className="flex gap-3">
                    <input
                        type="text"
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        placeholder="Wallet Name (optional)"
                        className="w-48 px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-500"
                    />
                    <input
                        type="text"
                        value={newAddress}
                        onChange={(e) => setNewAddress(e.target.value)}
                        placeholder="0x... wallet address"
                        className="flex-1 px-4 py-2 border border-slate-300 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-slate-500"
                    />
                    <button
                        type="submit"
                        disabled={isPending}
                        className="btn-primary flex items-center gap-2"
                    >
                        <Plus className="w-4 h-4" />
                        Add Whale
                    </button>
                </div>
                {error && (
                    <div className="mt-2 flex items-center gap-2 text-rose-600 text-xs">
                        <AlertCircle className="w-3 h-3" />
                        <span>{error}</span>
                    </div>
                )}
                {success && (
                    <div className="mt-2 flex items-center gap-2 text-emerald-600 text-xs">
                        <Check className="w-3 h-3" />
                        <span>{success}</span>
                    </div>
                )}
            </form>

            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 text-slate-500 font-medium border-b border-slate-200">
                        <tr>
                            <th className="px-6 py-3 w-48">Address / Name</th>
                            <th className="px-6 py-3 w-32">Tier & Score</th>
                            <th className="px-6 py-3">Performance Tags</th>
                            <th className="px-6 py-3 text-right">Stats (Win% | ROI)</th>
                            <th className="px-6 py-3 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                        {walletRows.map((wallet) => (
                            <tr key={wallet.address} className="hover:bg-slate-50 transition-colors">
                                <td className="px-6 py-3">
                                    <div className="font-mono font-medium text-slate-700">
                                        {wallet.name || `${wallet.address.slice(0, 6)}...${wallet.address.slice(-4)}`}
                                    </div>
                                    <div className="text-[10px] text-slate-400 font-mono">
                                        {wallet.address}
                                    </div>
                                </td>
                                <td className="px-6 py-3">
                                    {wallet.score ? (
                                        <Tooltip
                                            content={<WhaleScoreTooltip score={wallet.score} />}
                                            position="top"
                                        >
                                            <div className="cursor-help inline-flex items-center gap-2">
                                                <span className={`font-bold ${wallet.score.tier === 'ELITE' ? 'text-purple-600' :
                                                    wallet.score.tier === 'PRO' ? 'text-emerald-600' :
                                                        wallet.score.tier === 'WEAK' ? 'text-rose-500' : 'text-slate-500'
                                                    }`}>
                                                    {wallet.score.tier}
                                                </span>
                                                <div className={`px-2 py-0.5 rounded text-white font-bold text-xs ${wallet.score.total_score >= 80 ? 'bg-purple-500' :
                                                    wallet.score.total_score >= 60 ? 'bg-emerald-500' :
                                                        wallet.score.total_score >= 40 ? 'bg-amber-500' : 'bg-slate-400'
                                                    }`}>
                                                    {wallet.score.total_score}
                                                </div>
                                            </div>
                                        </Tooltip>
                                    ) : (
                                        <span className="text-slate-400 italic">Unscored</span>
                                    )}
                                </td>
                                <td className="px-6 py-3">
                                    <div className="flex gap-1">
                                        {wallet.score?.tags.map(tag => (
                                            <span key={tag} className="px-1.5 py-0.5 bg-slate-100 text-slate-600 text-[10px] font-bold rounded border border-slate-200">
                                                {tag}
                                            </span>
                                        ))}
                                    </div>
                                </td>
                                <td className="px-6 py-3 text-right font-mono text-xs text-slate-600">
                                    {wallet.score ? (
                                        <>
                                            <span className="text-emerald-600">
                                                {wallet.score.win_rate !== undefined
                                                    ? (wallet.score.win_rate * 100).toFixed(2)
                                                    : wallet.score.precision_score}%
                                            </span>
                                            <span className="mx-1 text-slate-300">|</span>
                                            <span className={wallet.score.roi_perf !== undefined && wallet.score.roi_perf < 0 ? "text-rose-500" : "text-blue-600"}>
                                                {wallet.score.roi_perf !== undefined
                                                    ? (wallet.score.roi_perf * 100).toFixed(2)
                                                    : wallet.score.roi_score}%
                                            </span>
                                        </>
                                    ) : '-'}
                                </td>
                                <td className="px-6 py-3 text-right">
                                    <button
                                        onClick={() => removeWallet(wallet.address)}
                                        className="p-1.5 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded transition-colors"
                                        title="Stop Tracking"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </td>
                            </tr>
                        ))}

                        {walletRows.length === 0 && (
                            <tr>
                                <td colSpan={5} className="px-6 py-12 text-center text-slate-400 font-medium">
                                    No wallets tracked. Add one in Settings.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div >
    );
}
