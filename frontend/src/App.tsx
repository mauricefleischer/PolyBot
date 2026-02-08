import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Settings } from 'lucide-react';
import { Header } from './components/Header';
import { SignalTable, PortfolioMonitor, SettingsTab } from './components/terminal';
import { useSignals, usePortfolio, useWallets, DEFAULT_RISK_SETTINGS } from './hooks/useSignals';
import type { RiskSettings } from './types/api';
import './index.css';

// Create query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

type TabType = 'scanner' | 'portfolio' | 'settings';

// Local storage key for risk settings
const RISK_SETTINGS_KEY = 'consensus_terminal_risk_settings';

function loadRiskSettings(): RiskSettings {
  try {
    const stored = localStorage.getItem(RISK_SETTINGS_KEY);
    if (stored) {
      return { ...DEFAULT_RISK_SETTINGS, ...JSON.parse(stored) };
    }
  } catch {
    // ignore
  }
  return DEFAULT_RISK_SETTINGS;
}

function saveRiskSettings(settings: RiskSettings) {
  localStorage.setItem(RISK_SETTINGS_KEY, JSON.stringify(settings));
}

function TerminalApp() {
  const [activeTab, setActiveTab] = useState<TabType>('scanner');
  const [userBalance] = useState(1000); // Default user balance
  const [userWallet, setUserWallet] = useState<string | null>(null);
  const [riskSettings, setRiskSettings] = useState<RiskSettings>(loadRiskSettings);

  // Fetch data with risk settings
  const { data: signals = [], isLoading: signalsLoading, refetch: refetchSignals } = useSignals(userBalance, riskSettings);
  const { data: walletsData } = useWallets();
  const { data: portfolio, isLoading: portfolioLoading } = usePortfolio(userWallet);

  const walletCount = walletsData?.count ?? 0;
  const signalCount = signals.length;

  const handleRefresh = () => {
    refetchSignals();
  };

  const handleConnectWallet = (address: string) => {
    setUserWallet(address);
  };

  const handleDisconnectWallet = () => {
    setUserWallet(null);
  };

  const handleConnectFromPortfolio = () => {
    setActiveTab('settings');
  };

  const handleRiskSettingsChange = (newSettings: RiskSettings) => {
    setRiskSettings(newSettings);
    saveRiskSettings(newSettings);
  };

  return (
    <div className="min-h-screen bg-white">
      <Header
        usdcBalance={userBalance}
        walletCount={walletCount}
        signalCount={signalCount}
        onRefresh={handleRefresh}
        isRefreshing={signalsLoading}
      />

      {/* Tab Navigation */}
      <div className="border-b border-slate-200">
        <div className="px-6 flex gap-1">
          <button
            onClick={() => setActiveTab('scanner')}
            className={`px-4 py-3 text-sm font-semibold border-b-2 transition-colors ${activeTab === 'scanner'
                ? 'border-slate-900 text-slate-900'
                : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
          >
            Alpha Scanner
          </button>
          <button
            onClick={() => setActiveTab('portfolio')}
            className={`px-4 py-3 text-sm font-semibold border-b-2 transition-colors ${activeTab === 'portfolio'
                ? 'border-slate-900 text-slate-900'
                : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
          >
            Portfolio Monitor
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`px-4 py-3 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${activeTab === 'settings'
                ? 'border-slate-900 text-slate-900'
                : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
          >
            <Settings className="w-4 h-4" />
            Settings
          </button>
        </div>
      </div>

      {/* Main Content */}
      <main className="p-6">
        {activeTab === 'scanner' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-900">
                Consensus Signals
              </h2>
              <p className="text-sm text-slate-500">
                Showing {signals.length} signals from {walletCount} tracked wallets
              </p>
            </div>
            <SignalTable signals={signals} isLoading={signalsLoading} />
          </div>
        )}

        {activeTab === 'portfolio' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-900">
                Portfolio Validation
              </h2>
              {!userWallet && (
                <p className="text-sm text-amber-600">
                  Connect wallet to view portfolio
                </p>
              )}
            </div>
            {userWallet ? (
              <PortfolioMonitor
                positions={portfolio?.positions ?? []}
                isLoading={portfolioLoading}
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-64 bg-slate-50 rounded-lg border border-slate-200">
                <p className="text-slate-500 mb-4">
                  Connect your wallet to compare positions against whale consensus
                </p>
                <button
                  className="btn-primary"
                  onClick={handleConnectFromPortfolio}
                >
                  Connect Wallet
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="max-w-4xl mx-auto">
            <div className="mb-6">
              <h2 className="text-lg font-bold text-slate-900">Settings</h2>
              <p className="text-sm text-slate-500">
                Manage your wallet, risk parameters, and tracked whale wallets
              </p>
            </div>
            <SettingsTab
              userWallet={userWallet}
              onConnectWallet={handleConnectWallet}
              onDisconnectWallet={handleDisconnectWallet}
              riskSettings={riskSettings}
              onRiskSettingsChange={handleRiskSettingsChange}
            />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 px-6 py-4 text-center">
        <p className="text-xs text-slate-400">
          Data sourced from Polymarket Gamma API. Kelly Criterion sizing.
          Not financial advice.
        </p>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TerminalApp />
    </QueryClientProvider>
  );
}
