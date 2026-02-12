import { useState } from 'react';
import { Plus, Trash2, Wallet, AlertCircle, Check, X, Sliders } from 'lucide-react';
import { useWallets, useWalletMutation } from '../../hooks/useSignals';
import type { RiskSettings } from '../../types/api';

interface WalletEntry {
    address: string;
    name: string;
}

// Local storage helper for wallet names
const WALLET_NAMES_KEY = 'consensus_terminal_wallet_names';

function getWalletNames(): Record<string, string> {
    try {
        const stored = localStorage.getItem(WALLET_NAMES_KEY);
        return stored ? JSON.parse(stored) : {};
    } catch {
        return {};
    }
}

function saveWalletName(address: string, name: string) {
    const names = getWalletNames();
    names[address.toLowerCase()] = name;
    localStorage.setItem(WALLET_NAMES_KEY, JSON.stringify(names));
}

function removeWalletName(address: string) {
    const names = getWalletNames();
    delete names[address.toLowerCase()];
    localStorage.setItem(WALLET_NAMES_KEY, JSON.stringify(names));
}

const KELLY_OPTIONS = [
    { value: 0.1, label: 'Conservative (0.1x)' },
    { value: 0.25, label: 'Balanced (0.25x)' },
    { value: 0.5, label: 'Aggressive (0.5x)' },
];

interface SettingsTabProps {
    userWallet: string | null;
    onConnectWallet: (address: string) => void;
    onDisconnectWallet: () => void;
    riskSettings: RiskSettings;
    onRiskSettingsChange: (settings: RiskSettings) => void;
}

export function SettingsTab({
    userWallet,
    onConnectWallet,
    onDisconnectWallet,
    riskSettings,
    onRiskSettingsChange
}: SettingsTabProps) {
    const { data: walletsData, isLoading } = useWallets();
    const walletMutation = useWalletMutation();

    const [newAddress, setNewAddress] = useState('');
    const [newName, setNewName] = useState('');
    const [connectAddress, setConnectAddress] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    const walletNames = getWalletNames();

    const wallets: WalletEntry[] = (walletsData?.wallets || []).map(addr => ({
        address: addr,
        name: walletNames[addr.toLowerCase()] || '',
    }));

    const handleAddWallet = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSuccess(null);

        if (!newAddress.match(/^0x[a-fA-F0-9]{40}$/)) {
            setError('Invalid wallet address format');
            return;
        }

        try {
            await walletMutation.mutateAsync({
                action: 'add',
                address: newAddress,
            });

            if (newName.trim()) {
                saveWalletName(newAddress, newName.trim());
            }

            setSuccess(`Wallet added: ${newName || newAddress.slice(0, 10)}...`);
            setNewAddress('');
            setNewName('');
        } catch {
            setError('Failed to add wallet');
        }
    };

    const handleRemoveWallet = async (address: string) => {
        try {
            await walletMutation.mutateAsync({
                action: 'remove',
                address,
            });
            removeWalletName(address);
        } catch {
            setError('Failed to remove wallet');
        }
    };

    const handleConnectWallet = (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!connectAddress.match(/^0x[a-fA-F0-9]{40}$/)) {
            setError('Invalid wallet address format');
            return;
        }

        onConnectWallet(connectAddress);
        setConnectAddress('');
        setSuccess('Wallet connected!');
    };

    const updateRiskSetting = <K extends keyof RiskSettings>(key: K, value: RiskSettings[K]) => {
        onRiskSettingsChange({ ...riskSettings, [key]: value });
    };

    return (
        <div className="space-y-8">
            {/* Risk Configuration */}
            <section className="bg-white rounded-lg border border-slate-200">
                <div className="p-6 border-b border-slate-200">
                    <h3 className="text-lg font-bold text-slate-900 mb-1 flex items-center gap-2">
                        <Sliders className="w-5 h-5" />
                        Risk Configuration
                    </h3>
                    <p className="text-sm text-slate-500">
                        Adjust Kelly Criterion parameters and view filters.
                    </p>
                </div>

                <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Kelly Multiplier */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                            Kelly Aggressiveness
                        </label>
                        <select
                            value={riskSettings.kellyMultiplier}
                            onChange={(e) => updateRiskSetting('kellyMultiplier', parseFloat(e.target.value))}
                            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500"
                        >
                            {KELLY_OPTIONS.map(opt => (
                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                        </select>
                        <p className="mt-1 text-xs text-slate-500">
                            Fraction of Kelly optimal to bet
                        </p>
                    </div>

                    {/* Max Risk Cap */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                            Max Risk Per Trade: {(riskSettings.maxRiskCap * 100).toFixed(0)}%
                        </label>
                        <input
                            type="range"
                            min="0.01"
                            max="0.20"
                            step="0.01"
                            value={riskSettings.maxRiskCap}
                            onChange={(e) => updateRiskSetting('maxRiskCap', parseFloat(e.target.value))}
                            className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                        />
                        <div className="flex justify-between text-xs text-slate-400 mt-1">
                            <span>1%</span>
                            <span>10%</span>
                            <span>20%</span>
                        </div>
                    </div>

                    {/* Minimum Wallets */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                            Minimum Whale Consensus
                        </label>
                        <select
                            value={riskSettings.minWallets}
                            onChange={(e) => updateRiskSetting('minWallets', parseInt(e.target.value))}
                            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500"
                        >
                            {[1, 2, 3, 4, 5].map(n => (
                                <option key={n} value={n}>{n} wallet{n > 1 ? 's' : ''}</option>
                            ))}
                        </select>
                        <p className="mt-1 text-xs text-slate-500">
                            Hide signals below this threshold
                        </p>
                    </div>

                    {/* Hide Lottery */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                            View Filters
                        </label>
                        <label className="flex items-center gap-3 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={riskSettings.hideLottery}
                                onChange={(e) => updateRiskSetting('hideLottery', e.target.checked)}
                                className="w-5 h-5 rounded border-slate-300 text-slate-900 focus:ring-slate-500"
                            />
                            <span className="text-sm text-slate-700">
                                Hide Lottery Tickets (Alpha &lt; 30)
                            </span>
                        </label>
                    </div>

                    {/* Longshot Tolerance (Alpha 2.0) */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                            Longshot Tolerance: {(riskSettings.longshotTolerance ?? 1.0).toFixed(1)}x
                        </label>
                        <input
                            type="range"
                            min="0.5"
                            max="1.5"
                            step="0.1"
                            value={riskSettings.longshotTolerance ?? 1.0}
                            onChange={(e) => updateRiskSetting('longshotTolerance', parseFloat(e.target.value))}
                            className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                        />
                        <div className="flex justify-between text-xs text-slate-400 mt-1">
                            <span>Lenient (0.5x)</span>
                            <span>Default (1.0x)</span>
                            <span>Strict (1.5x)</span>
                        </div>
                        <p className="mt-1 text-xs text-slate-500">
                            Scales how much longshot bets are penalized by the FLB model
                        </p>
                    </div>

                    {/* Trend Following Mode (Alpha 2.0) */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                            Alpha Score 2.0
                        </label>
                        <label className="flex items-center gap-3 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={riskSettings.trendMode ?? true}
                                onChange={(e) => updateRiskSetting('trendMode', e.target.checked)}
                                className="w-5 h-5 rounded border-slate-300 text-slate-900 focus:ring-slate-500"
                            />
                            <span className="text-sm text-slate-700">
                                Trend Following Mode
                            </span>
                        </label>
                        <p className="mt-1 text-xs text-slate-500">
                            Enable momentum scoring (price vs 7-day average)
                        </p>
                    </div>
                </div>
            </section>

            {/* User Wallet Connection */}
            <section className="bg-slate-50 rounded-lg p-6 border border-slate-200">
                <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
                    <Wallet className="w-5 h-5" />
                    Your Wallet
                </h3>

                {userWallet ? (
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-slate-500">Connected as:</p>
                            <p className="font-mono text-slate-900">{userWallet}</p>
                        </div>
                        <button
                            onClick={onDisconnectWallet}
                            className="btn-danger text-sm py-2 px-4"
                        >
                            Disconnect
                        </button>
                    </div>
                ) : (
                    <form onSubmit={handleConnectWallet} className="space-y-4">
                        <p className="text-sm text-slate-500">
                            Connect your wallet to compare your positions against whale consensus.
                        </p>
                        <div className="flex gap-3">
                            <input
                                type="text"
                                value={connectAddress}
                                onChange={(e) => setConnectAddress(e.target.value)}
                                placeholder="0x..."
                                className="flex-1 px-4 py-2 border border-slate-300 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-slate-500"
                            />
                            <button type="submit" className="btn-primary">
                                Connect
                            </button>
                        </div>
                    </form>
                )}
            </section>

            {/* Tracked Whales Section */}
            <section className="bg-white rounded-lg border border-slate-200">
                <div className="p-6 border-b border-slate-200">
                    <h3 className="text-lg font-bold text-slate-900 mb-1">
                        Tracked Whale Wallets
                    </h3>
                    <p className="text-sm text-slate-500">
                        Add whale wallets to track their positions and generate consensus signals.
                    </p>
                </div>

                {/* Add Wallet Form */}
                <form onSubmit={handleAddWallet} className="p-6 bg-slate-50 border-b border-slate-200">
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
                            disabled={walletMutation.isPending}
                            className="btn-primary flex items-center gap-2"
                        >
                            <Plus className="w-4 h-4" />
                            Add Wallet
                        </button>
                    </div>
                </form>

                {/* Messages */}
                {error && (
                    <div className="mx-6 mt-4 flex items-center gap-2 text-rose-700 bg-rose-50 px-4 py-2 rounded-lg border border-rose-200">
                        <AlertCircle className="w-4 h-4" />
                        <span className="text-sm">{error}</span>
                        <button onClick={() => setError(null)} className="ml-auto">
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                )}

                {success && (
                    <div className="mx-6 mt-4 flex items-center gap-2 text-emerald-700 bg-emerald-50 px-4 py-2 rounded-lg border border-emerald-200">
                        <Check className="w-4 h-4" />
                        <span className="text-sm">{success}</span>
                        <button onClick={() => setSuccess(null)} className="ml-auto">
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                )}

                {/* Wallet List */}
                <div className="divide-y divide-slate-100">
                    {isLoading ? (
                        <div className="p-6 text-center text-slate-500">
                            Loading wallets...
                        </div>
                    ) : wallets.length === 0 ? (
                        <div className="p-6 text-center text-slate-500">
                            No wallets tracked yet. Add a wallet above.
                        </div>
                    ) : (
                        wallets.map((wallet) => (
                            <WalletRow
                                key={wallet.address}
                                wallet={wallet}
                                onRemove={() => handleRemoveWallet(wallet.address)}
                                onUpdateName={(name) => {
                                    saveWalletName(wallet.address, name);
                                    // Force re-render by triggering a state update
                                    setSuccess(null);
                                }}
                            />
                        ))
                    )}
                </div>
            </section>
        </div>
    );
}

interface WalletRowProps {
    wallet: WalletEntry;
    onRemove: () => void;
    onUpdateName: (name: string) => void;
}

function WalletRow({ wallet, onRemove, onUpdateName }: WalletRowProps) {
    const [isEditing, setIsEditing] = useState(false);
    const [editName, setEditName] = useState(wallet.name);

    const handleSave = () => {
        onUpdateName(editName);
        setIsEditing(false);
    };

    return (
        <div className="flex items-center justify-between px-6 py-4 hover:bg-slate-50">
            <div className="flex-1 min-w-0">
                {isEditing ? (
                    <div className="flex items-center gap-2">
                        <input
                            type="text"
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            placeholder="Enter name..."
                            className="px-3 py-1 border border-slate-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-slate-500"
                            autoFocus
                        />
                        <button
                            onClick={handleSave}
                            className="p-1 text-emerald-600 hover:bg-emerald-50 rounded"
                        >
                            <Check className="w-4 h-4" />
                        </button>
                        <button
                            onClick={() => {
                                setEditName(wallet.name);
                                setIsEditing(false);
                            }}
                            className="p-1 text-slate-400 hover:bg-slate-100 rounded"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                ) : (
                    <div>
                        <div className="flex items-center gap-2">
                            {wallet.name ? (
                                <span className="font-semibold text-slate-900">{wallet.name}</span>
                            ) : (
                                <button
                                    onClick={() => setIsEditing(true)}
                                    className="text-sm text-slate-400 hover:text-slate-600"
                                >
                                    + Add name
                                </button>
                            )}
                            {wallet.name && (
                                <button
                                    onClick={() => setIsEditing(true)}
                                    className="text-xs text-slate-400 hover:text-slate-600"
                                >
                                    Edit
                                </button>
                            )}
                        </div>
                        <p className="font-mono text-sm text-slate-500 truncate">
                            {wallet.address}
                        </p>
                    </div>
                )}
            </div>

            <button
                onClick={onRemove}
                className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                title="Remove wallet"
            >
                <Trash2 className="w-4 h-4" />
            </button>
        </div>
    );
}
