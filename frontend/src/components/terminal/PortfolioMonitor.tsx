import { useState, useMemo } from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import type { PortfolioPosition } from '../../types/api';
import { Tooltip } from '../ui/Tooltip';
import { cn, formatCurrency, formatPrice, formatPercent } from '../../lib/utils';

interface PortfolioMonitorProps {
    positions: PortfolioPosition[];
    isLoading?: boolean;
}

type SortField = 'market_name' | 'size_usdc' | 'pnl_percent' | 'status' | 'whale_count';
type SortDirection = 'asc' | 'desc';

// Status explanations for tooltips
const STATUS_INFO = {
    VALIDATED: {
        title: '✅ VALIDATED',
        description: 'Your position aligns with whale consensus. Whales are holding the same position - this is a strong signal to hold.',
    },
    DIVERGENCE: {
        title: '⚠️ DIVERGENCE',
        description: 'Your position differs from whale consensus. Whales have exited or taken the opposite side. Consider selling.',
    },
    TRIM: {
        title: '🔻 TRIM',
        description: 'Your position is larger than optimal. Whales have reduced exposure. Consider reducing your position size.',
    },
};

export function PortfolioMonitor({ positions, isLoading }: PortfolioMonitorProps) {
    const [sortField, setSortField] = useState<SortField>('pnl_percent');
    const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDirection('desc');
        }
    };

    const sortedPositions = useMemo(() => {
        return [...positions].sort((a, b) => {
            let comparison = 0;

            switch (sortField) {
                case 'market_name':
                    comparison = a.market_name.localeCompare(b.market_name);
                    break;
                case 'size_usdc':
                    comparison = a.size_usdc - b.size_usdc;
                    break;
                case 'pnl_percent':
                    comparison = a.pnl_percent - b.pnl_percent;
                    break;
                case 'status':
                    const statusOrder = { VALIDATED: 0, DIVERGENCE: 1, TRIM: 2 };
                    comparison = (statusOrder[a.status] || 0) - (statusOrder[b.status] || 0);
                    break;
                case 'whale_count':
                    comparison = a.whale_count - b.whale_count;
                    break;
            }

            return sortDirection === 'asc' ? comparison : -comparison;
        });
    }, [positions, sortField, sortDirection]);

    const SortHeader = ({ field, children }: { field: SortField; children: React.ReactNode }) => {
        const isActive = sortField === field;
        return (
            <th
                onClick={() => handleSort(field)}
                className="cursor-pointer hover:bg-slate-100 select-none transition-colors"
            >
                <div className="flex items-center gap-1">
                    {children}
                    {isActive ? (
                        sortDirection === 'desc' ? (
                            <ArrowDown className="w-3 h-3 text-blue-600" />
                        ) : (
                            <ArrowUp className="w-3 h-3 text-blue-600" />
                        )
                    ) : (
                        <ArrowUpDown className="w-3 h-3 text-slate-400" />
                    )}
                </div>
            </th>
        );
    };

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
                        <SortHeader field="market_name">Market</SortHeader>
                        <th>Position</th>
                        <SortHeader field="size_usdc">Size</SortHeader>
                        <th>Entry / Now</th>
                        <SortHeader field="pnl_percent">PnL</SortHeader>
                        <SortHeader field="status">Status</SortHeader>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {sortedPositions.map((position, index) => (
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
                    <Tooltip content={
                        <div className="space-y-1">
                            <div className="font-semibold text-emerald-400">{STATUS_INFO.VALIDATED.title}</div>
                            <div className="text-slate-300 text-[10px] leading-tight max-w-[180px]">
                                {STATUS_INFO.VALIDATED.description}
                            </div>
                        </div>
                    }>
                        <span className="cursor-help badge badge-validated">
                            VALIDATED
                        </span>
                    </Tooltip>
                );
            case 'DIVERGENCE':
                return (
                    <Tooltip content={
                        <div className="space-y-1">
                            <div className="font-semibold text-rose-400">{STATUS_INFO.DIVERGENCE.title}</div>
                            <div className="text-slate-300 text-[10px] leading-tight max-w-[180px]">
                                {STATUS_INFO.DIVERGENCE.description}
                            </div>
                        </div>
                    }>
                        <span className="cursor-help badge badge-divergence">
                            DIVERGENCE
                        </span>
                    </Tooltip>
                );
            case 'TRIM':
                return (
                    <Tooltip content={
                        <div className="space-y-1">
                            <div className="font-semibold text-amber-400">{STATUS_INFO.TRIM.title}</div>
                            <div className="text-slate-300 text-[10px] leading-tight max-w-[180px]">
                                {STATUS_INFO.TRIM.description}
                            </div>
                        </div>
                    }>
                        <span className="cursor-help badge badge-trim">
                            TRIM
                        </span>
                    </Tooltip>
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
