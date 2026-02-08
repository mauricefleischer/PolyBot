import type { PortfolioPosition } from '../../types/api';
import { cn, formatCurrency, formatPrice, formatPercent } from '../../lib/utils';

interface PortfolioMonitorProps {
    positions: PortfolioPosition[];
    isLoading?: boolean;
}

export function PortfolioMonitor({ positions, isLoading }: PortfolioMonitorProps) {
    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-48 text-slate-500">
                Loading portfolio...
            </div>
        );
    }

    if (positions.length === 0) {
        return (
            <div className="flex items-center justify-center h-48 text-slate-500">
                No active positions found.
            </div>
        );
    }

    return (
        <div className="overflow-x-auto border border-slate-200 rounded-lg">
            <table className="terminal-table">
                <thead>
                    <tr>
                        <th>Market</th>
                        <th>Position</th>
                        <th>Size</th>
                        <th>Entry / Now</th>
                        <th>PnL</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {positions.map((position, index) => (
                        <PositionRow key={`${position.market_id}-${index}`} position={position} />
                    ))}
                </tbody>
            </table>
        </div>
    );
}

interface PositionRowProps {
    position: PortfolioPosition;
}

function PositionRow({ position }: PositionRowProps) {
    const {
        market_name,
        outcome_label,
        direction,
        size_usdc,
        entry_price,
        current_price,
        pnl_percent,
        status,
        whale_count,
    } = position;

    const isShort = direction === 'NO';
    const isProfitable = pnl_percent >= 0;

    const getStatusBadge = () => {
        switch (status) {
            case 'VALIDATED':
                return (
                    <span className="badge badge-validated">
                        VALIDATED
                    </span>
                );
            case 'DIVERGENCE':
                return (
                    <span className="badge badge-divergence">
                        DIVERGENCE
                    </span>
                );
            case 'TRIM':
                return (
                    <span className="badge badge-trim">
                        TRIM
                    </span>
                );
            default:
                return null;
        }
    };

    const getActionButton = () => {
        switch (status) {
            case 'DIVERGENCE':
                return (
                    <button className="btn-danger text-xs py-1 px-3">
                        SELL
                    </button>
                );
            case 'TRIM':
                return (
                    <button className="btn-warning text-xs py-1 px-3">
                        REDUCE
                    </button>
                );
            default:
                return (
                    <button className="text-slate-400 text-xs cursor-default" disabled>
                        HOLD
                    </button>
                );
        }
    };

    return (
        <tr>
            {/* Market */}
            <td>
                <div className="text-xs text-slate-500 font-semibold max-w-[200px] truncate">
                    {market_name}
                </div>
            </td>

            {/* Position */}
            <td>
                <div className="flex items-center gap-2">
                    <span className="text-slate-900 font-semibold">{outcome_label}</span>
                    <span className={cn('badge', isShort ? 'badge-short' : 'badge-long')}>
                        {isShort ? 'SHORT' : 'LONG'}
                    </span>
                </div>
            </td>

            {/* Size */}
            <td>
                <span className="text-slate-900 font-medium tabular-nums">
                    {formatCurrency(size_usdc)}
                </span>
            </td>

            {/* Entry / Now */}
            <td>
                <div className="tabular-nums">
                    <span className="text-slate-500">{formatPrice(entry_price)}</span>
                    <span className="text-slate-400 mx-1">&rarr;</span>
                    <span className={isProfitable ? 'price-profit' : 'price-loss'}>
                        {formatPrice(current_price)}
                    </span>
                </div>
            </td>

            {/* PnL */}
            <td>
                <span
                    className={cn(
                        'font-semibold tabular-nums',
                        isProfitable ? 'text-emerald-700' : 'text-rose-700'
                    )}
                >
                    {formatPercent(pnl_percent)}
                </span>
            </td>

            {/* Status */}
            <td>
                <div className="flex items-center gap-2">
                    {getStatusBadge()}
                    {whale_count > 0 && (
                        <span className="text-xs text-slate-500">
                            ({whale_count} whales)
                        </span>
                    )}
                </div>
            </td>

            {/* Action */}
            <td>{getActionButton()}</td>
        </tr>
    );
}
