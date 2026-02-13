import { useState, useEffect, useRef, useCallback } from 'react';
import { Wallet, Sliders, Check, AlertCircle } from 'lucide-react';
import { cn } from '../../lib/utils';
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
    const debouncedSaveRef = useRef<ReturnType<typeof setTimeout>>();

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
                                    type="range"
                                    min={1}
                                    max={5}
                                    step={1}
                                    value={settings.yieldMinWhales}
                                    onChange={(e) => updateRiskSetting('yieldMinWhales', parseInt(e.target.value))}
                                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-slate-600"
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
                            Minimum Whale Consensus
                        </label>
                        <select
                            value={settings.minWallets}
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
                                checked={settings.hideLottery}
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
                                checked={settings.trendMode ?? true}
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

            {/* Algo Configuration (Whale Quality & FLB) */}
            <section className="bg-white rounded-lg border border-slate-200">
                <div className="p-6 border-b border-slate-200">
                    <h3 className="text-lg font-bold text-slate-900 mb-1 flex items-center gap-2">
                        <Sliders className="w-5 h-5" />
                        Algo Configuration
                    </h3>
                    <p className="text-sm text-slate-500">
                        Configure the De-Biased Kelly Engine and Smart Money Filters.
                    </p>
                </div>

                <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* FLB Correction Mode */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                            FLB Correction Mode
                        </label>
                        <select
                            value={settings.flbCorrectionMode || 'STANDARD'}
                            onChange={(e) => updateRiskSetting('flbCorrectionMode', e.target.value as any)}
                            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500"
                        >
                            <option value="AGGRESSIVE">Aggressive (Heavy Penalty)</option>
                            <option value="STANDARD">Standard (J-Curve)</option>
                            <option value="OFF">Off (Naive Kelly)</option>
                        </select>
                        <p className="mt-1 text-xs text-slate-500">
                            Adjusts probabilities for Favorite-Longshot Bias
                        </p>
                    </div>

                    {/* Minimum Whale Tier */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                            Minimum Whale Tier
                        </label>
                        <div className="flex rounded-lg overflow-hidden border border-slate-300">
                            {['ALL', 'PRO', 'ELITE'].map((tier) => (
                                <button
                                    key={tier}
                                    onClick={() => updateRiskSetting('minWhaleTier', tier as any)}
                                    className={cn(
                                        "flex-1 py-2 text-sm font-medium transition-colors",
                                        (settings.minWhaleTier || 'ALL') === tier
                                            ? "bg-slate-800 text-white"
                                            : "bg-white text-slate-600 hover:bg-slate-50"
                                    )}
                                >
                                    {tier}
                                </button>
                            ))}
                        </div>
                        <p className="mt-1 text-xs text-slate-500">
                            Filter signals by consensus quality
                        </p>
                    </div>

                    {/* Optimism Tax */}
                    <div>
                        <label className="flex items-center gap-3 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={settings.optimismTax ?? true}
                                onChange={(e) => updateRiskSetting('optimismTax', e.target.checked)}
                                className="w-5 h-5 rounded border-slate-300 text-slate-900 focus:ring-slate-500"
                            />
                            <div>
                                <span className="text-sm font-medium text-slate-700">Apply Optimism Tax</span>
                                <p className="text-xs text-slate-500">5% handicap for Sports & Politics</p>
                            </div>
                        </label>
                    </div>

                    {/* Ignore Bagholders */}
                    <div>
                        <label className="flex items-center gap-3 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={settings.ignoreBagholders ?? true}
                                onChange={(e) => updateRiskSetting('ignoreBagholders', e.target.checked)}
                                className="w-5 h-5 rounded border-slate-300 text-slate-900 focus:ring-slate-500"
                            />
                            <div>
                                <span className="text-sm font-medium text-slate-700">Ignore Bagholders</span>
                                <p className="text-xs text-slate-500">Exclude wallets with Discipline Score &lt; 30</p>
                            </div>
                        </label>
                    </div>
                </div>
            </section>

            {/* User Wallet Connection */}
            < section className="bg-slate-50 rounded-lg p-6 border border-slate-200" >
                <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
                    <Wallet className="w-5 h-5" />
                    Your Wallet
                </h3>

                {
                    userWallet ? (
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
                    )
                }
            </section >
        </div >
    );
}
