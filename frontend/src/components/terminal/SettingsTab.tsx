import { useState, useEffect, useRef, useCallback } from 'react';
import { Wallet, Sliders, Check, AlertCircle, Eye, Monitor } from 'lucide-react';

import type { RiskSettings } from '../../types/api';

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
    const [connectAddress, setConnectAddress] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // Local state for immediate UI updates
    const [localSettings, setLocalSettings] = useState<RiskSettings>(riskSettings);

    // Sync local state when props change (e.g. initial load)
    useEffect(() => {
        setLocalSettings(riskSettings);
    }, [riskSettings]);

    // Debounced save function
    const debouncedSaveRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const saveSettings = useCallback((newSettings: RiskSettings) => {
        if (debouncedSaveRef.current) {
            clearTimeout(debouncedSaveRef.current);
        }

        debouncedSaveRef.current = setTimeout(() => {
            onRiskSettingsChange(newSettings);
        }, 500);
    }, [onRiskSettingsChange]);

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
        const newSettings = { ...localSettings, [key]: value };
        setLocalSettings(newSettings); // Immediate UI update
        saveSettings(newSettings); // Debounced API call
    };

    // Helper to safely access settings with connection fallback
    // (using localSettings for UI consistency during edits)
    const settings = localSettings;

    return (
        <div className="space-y-8">
            {/* 1. Risk Configuration */}
            <section className="bg-white rounded-lg border border-slate-200">
                <div className="p-6 border-b border-slate-200">
                    <h3 className="text-lg font-bold text-slate-900 mb-1 flex items-center gap-2">
                        <Sliders className="w-5 h-5" />
                        Risk Configuration
                    </h3>
                    <p className="text-sm text-slate-500">
                        Adjust Kelly Criterion parameters and sizing logic.
                    </p>
                </div>

                <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Strategy Mode Sliders */}
                    <div className="col-span-1 md:col-span-2 bg-slate-50 p-4 rounded-lg border border-slate-200">
                        <h4 className="font-bold text-slate-700 mb-4 flex items-center gap-2">
                            Active Strategy Configuration
                            <span className="text-[10px] font-normal bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full border border-blue-200">
                                Dynamic Risk Engine
                            </span>
                        </h4>

                        <div className="space-y-6">
                            {/* Yield Zone Start */}
                            <div>
                                <div className="flex justify-between text-sm mb-2">
                                    <span className="font-medium text-slate-700">Yield Zone Start (Price)</span>
                                    <span className="font-mono font-bold text-blue-600">{(settings.yieldTriggerPrice * 100).toFixed(0)}¢</span>
                                </div>
                                <input
                                    type="range"
                                    min={0.50}
                                    max={0.99}
                                    step={0.01}
                                    value={settings.yieldTriggerPrice}
                                    onChange={(e) => updateRiskSetting('yieldTriggerPrice', parseFloat(e.target.value))}
                                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                                />
                                <p className="mt-1 text-xs text-slate-500">
                                    Prices above this level trigger "Yield Mode" (fixed sizing) instead of Kelly.
                                </p>
                            </div>

                            {/* Yield Fixed Size */}
                            <div>
                                <div className="flex justify-between text-sm mb-2">
                                    <span className="font-medium text-slate-700">Yield Fixed Size (Capital %)</span>
                                    <span className="font-mono font-bold text-emerald-600">{(settings.yieldFixedPct * 100).toFixed(0)}%</span>
                                </div>
                                <input
                                    type="range"
                                    min={0.01}
                                    max={0.50}
                                    step={0.01}
                                    value={settings.yieldFixedPct}
                                    onChange={(e) => updateRiskSetting('yieldFixedPct', parseFloat(e.target.value))}
                                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                                />
                                <p className="mt-1 text-xs text-slate-500">
                                    Fixed position size when in Yield Mode.
                                </p>
                            </div>

                            {/* Min Whales for Yield */}
                            <div>
                                <div className="flex justify-between text-sm mb-2">
                                    <span className="font-medium text-slate-700">Min. Whales for Yield Mode</span>
                                    <span className="font-mono font-bold text-slate-900">{settings.yieldMinWhales} Whales</span>
                                </div>
                                <input
                                    type="number"
                                    min={1}
                                    max={100}
                                    step={1}
                                    value={settings.yieldMinWhales}
                                    onChange={(e) => updateRiskSetting('yieldMinWhales', parseInt(e.target.value) || 1)}
                                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 font-mono"
                                />
                                <p className="mt-1 text-xs text-slate-500">
                                    Required consensus count to activate Yield Mode.
                                </p>
                            </div>
                        </div>
                    </div>
                    {/* Kelly Multiplier */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                            Kelly Aggressiveness
                        </label>
                        <select
                            value={settings.kellyMultiplier}
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
                            Max Risk Per Trade: {(settings.maxRiskCap * 100).toFixed(0)}%
                        </label>
                        <input
                            type="range"
                            min={0.01}
                            max={0.20}
                            step={0.01}
                            value={settings.maxRiskCap}
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
                            Global Minimum Whales
                        </label>
                        <input
                            type="number"
                            min={1}
                            max={100}
                            step={1}
                            value={settings.minWallets}
                            onChange={(e) => updateRiskSetting('minWallets', parseInt(e.target.value) || 1)}
                            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 font-mono"
                        />
                        <p className="mt-1 text-xs text-slate-500">
                            Signals with fewer whales are hidden completely.
                        </p>
                    </div>

                    {/* Longshot Tolerance */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                            Longshot Tolerance: {(settings.longshotTolerance ?? 1.0).toFixed(1)}x
                        </label>
                        <input
                            type="range"
                            min={0.5}
                            max={1.5}
                            step={0.1}
                            value={settings.longshotTolerance ?? 1.0}
                            onChange={(e) => updateRiskSetting('longshotTolerance', parseFloat(e.target.value))}
                            className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                        />
                        <div className="flex justify-between text-xs text-slate-400 mt-1">
                            <span>Lenient (0.5x)</span>
                            <span>Default (1.0x)</span>
                            <span>Strict (1.5x)</span>
                        </div>
                        <p className="mt-1 text-xs text-slate-500">
                            Scales how much longshot bets are penalized by the FLB model.
                        </p>
                    </div>
                </div>
            </section>

            {/* 2. Visual Interface Settings */}
            <section className="bg-white rounded-lg border border-slate-200">
                <div className="p-6 border-b border-slate-200">
                    <h3 className="text-lg font-bold text-slate-900 mb-1 flex items-center gap-2">
                        <Monitor className="w-5 h-5" />
                        Interface Settings
                    </h3>
                    <p className="text-sm text-slate-500">
                        Customize visual indicators, color thresholds, and view filters.
                    </p>
                </div>

                <div className="p-6 space-y-8">
                    {/* Perspective: Consensus Thresholds */}
                    <div>
                        <h4 className="font-bold text-slate-700 mb-4 flex items-center gap-2">
                            <Eye className="w-4 h-4" />
                            Consensus Visualization
                        </h4>

                        <div className="space-y-6">
                            {/* Purple Threshold Override */}
                            <div>
                                <div className="flex justify-between text-sm mb-2">
                                    <span className="font-medium text-slate-700 flex items-center gap-2">
                                        <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                                        Elite Consensus Threshold
                                    </span>
                                    <span className="font-mono font-bold text-slate-900">
                                        {settings.consensusPurpleThreshold ?? 4} Whales
                                    </span>
                                </div>
                                <input
                                    type="number"
                                    min={1}
                                    max={100}
                                    step={1}
                                    value={settings.consensusPurpleThreshold ?? 4}
                                    onChange={(e) => updateRiskSetting('consensusPurpleThreshold', parseInt(e.target.value) || 1)}
                                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono"
                                />
                                <p className="mt-1 text-xs text-slate-500">
                                    Minimum distinct wallets required to trigger the Elite (Purple) status.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-slate-100">
                        {/* Hide Lottery */}
                        <div>
                            <label className="block text-sm font-bold text-slate-700 mb-2">
                                Low Quality Filtering
                            </label>
                            <label className="flex items-center gap-3 cursor-pointer p-3 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors">
                                <input
                                    type="checkbox"
                                    checked={settings.hideLottery}
                                    onChange={(e) => updateRiskSetting('hideLottery', e.target.checked)}
                                    className="w-5 h-5 rounded border-slate-300 text-slate-900 focus:ring-slate-500"
                                />
                                <div>
                                    <span className="text-sm font-medium text-slate-900 block">
                                        Hide Lottery Tickets
                                    </span>
                                    <span className="text-xs text-slate-500 block">
                                        Exclude signals with Alpha Score &lt; 30
                                    </span>
                                </div>
                            </label>
                        </div>

                        {/* Trend Following Mode */}
                        <div>
                            <label className="block text-sm font-bold text-slate-700 mb-2">
                                Scoring Logic
                            </label>
                            <label className="flex items-center gap-3 cursor-pointer p-3 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors">
                                <input
                                    type="checkbox"
                                    checked={settings.trendMode ?? true}
                                    onChange={(e) => updateRiskSetting('trendMode', e.target.checked)}
                                    className="w-5 h-5 rounded border-slate-300 text-slate-900 focus:ring-slate-500"
                                />
                                <div>
                                    <span className="text-sm font-medium text-slate-900 block">
                                        Trend Following Mode
                                    </span>
                                    <span className="text-xs text-slate-500 block">
                                        Enable momentum scoring (price vs 7d avg)
                                    </span>
                                </div>
                            </label>
                        </div>
                    </div>
                </div>
            </section>

            {/* 3. User Wallet Connection */}
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
                        {error && (
                            <div className="flex items-center gap-2 text-rose-600 text-sm">
                                <AlertCircle className="w-4 h-4" />
                                {error}
                            </div>
                        )}
                        {success && (
                            <div className="flex items-center gap-2 text-emerald-600 text-sm">
                                <Check className="w-4 h-4" />
                                {success}
                            </div>
                        )}
                    </form>
                )}
            </section>
        </div>
    );
}
