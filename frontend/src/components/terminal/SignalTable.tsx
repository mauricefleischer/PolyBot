import { useMemo } from 'react';
import {
    useReactTable,
    getCoreRowModel,
    getSortedRowModel,
    flexRender,
    type ColumnDef,
} from '@tanstack/react-table';
import { ArrowUpDown, HelpCircle } from 'lucide-react';
import type { Signal, RiskSettings } from '../../types/api';
import { Tooltip, AlphaTooltipContent, KellyTooltipContent, WhaleTooltipContent, AlphaGuideTooltip } from '../ui/Tooltip';
import {
    cn,
    formatCurrency,
    formatPrice,
    getHeatmapClass,
    getAlphaScoreInfo,
    getPriceDeltaClass,
    truncate,
} from '../../lib/utils';

interface SignalTableProps {
    signals: Signal[];
    isLoading?: boolean;
    settings?: RiskSettings;
}

export function SignalTable({ signals, isLoading, settings }: SignalTableProps) {
    const columns = useMemo<ColumnDef<Signal>[]>(
        () => [
            // Column 1: RANK & CONSENSUS
            {
                id: 'consensus',
                header: ({ column }) => (
                    <button
                        className="flex items-center gap-1 hover:text-slate-900"
                        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
                    >
                        Consensus
                        <ArrowUpDown className="h-3 w-3" />
                    </button>
                ),
                accessorKey: 'wallet_count',
                cell: ({ row }) => {
                    const consensus = row.original.consensus;
                    const walletCount = consensus.count;

                    // Elite status (Purple) is ONLY triggered by the actual count of elite wallets matching the threshold
                    const isPurple = (consensus as any).elite_count >= (settings?.consensusPurpleThreshold ?? 1);

                    const baseHeatmapClass = getHeatmapClass(walletCount, 1); // Always returns medium (Orange)

                    const barClass = isPurple
                        ? 'bg-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.5)]'
                        : baseHeatmapClass;

                    // Construct meta for tooltip compatibility
                    const tooltipMeta = {
                        avg_score: consensus.weighted_score,
                        has_elite: consensus.has_elite,
                        has_bagholder: false,
                        wallet_tiers: consensus.contributors.reduce((acc, c) => ({
                            ...acc,
                            [c.address]: c.tier
                        }), {} as Record<string, string>)
                    };

                    return (
                        <Tooltip
                            content={<WhaleTooltipContent meta={tooltipMeta} />}
                            position="right"
                        >
                            <div className="relative pl-3 cursor-help">
                                <div className={cn('heatmap-bar', barClass)} />
                                <div className="text-xl tabular-nums flex items-center gap-1.5 font-bold text-slate-900">
                                    {walletCount}
                                </div>
                                <div className="text-slate-500 text-xs">Wallets</div>
                            </div>
                        </Tooltip>
                    );
                },
            },

            // Column 2: MARKET & DIRECTION
            {
                id: 'market',
                header: 'Market',
                accessorKey: 'market_name',
                cell: ({ row }) => {
                    const { market_name, outcome_label, direction } = row.original;
                    const isShort = direction === 'NO';

                    return (
                        <div className="flex flex-col gap-1">
                            <div className="text-xs text-slate-500 font-semibold">
                                {truncate(market_name, 40)}
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-slate-900 font-semibold">
                                    {outcome_label}
                                </span>
                                <span
                                    className={cn(
                                        'badge',
                                        isShort ? 'badge-short' : 'badge-long'
                                    )}
                                >
                                    {isShort ? 'SHORT' : 'LONG'}
                                </span>
                            </div>
                        </div>
                    );
                },
            },

            // Column 3: BECKER ALPHA SCORE
            {
                id: 'alpha_score',
                header: ({ column }) => (
                    <div className="flex items-center">
                        <button
                            className="flex items-center gap-1 hover:text-slate-900"
                            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
                        >
                            Alpha Score
                            <ArrowUpDown className="h-3 w-3" />
                        </button>
                        <Tooltip content={<AlphaGuideTooltip />}>
                            <div className="ml-1 text-slate-400 hover:text-slate-600 cursor-help">
                                <HelpCircle className="w-3.5 h-3.5" />
                            </div>
                        </Tooltip>
                    </div>
                ),
                accessorKey: 'alpha_score',
                cell: ({ row }) => {
                    const score = row.original.alpha_score;
                    const breakdown = row.original.alpha_breakdown || [];
                    const { label, className } = getAlphaScoreInfo(score);
                    const progressWidth = `${score}%`;

                    return (
                        <Tooltip content={<AlphaTooltipContent score={score} breakdown={breakdown} />}>
                            <div className="relative cursor-help">
                                <div
                                    className={cn(
                                        'score-bar rounded',
                                        score > 70 ? 'bg-emerald-500' : score < 40 ? 'bg-rose-500' : 'bg-slate-400'
                                    )}
                                    style={{ width: progressWidth }}
                                />
                                <div className="relative flex items-center gap-2">
                                    <span className={cn('font-bold text-lg tabular-nums', className)}>
                                        {score}
                                    </span>
                                    {label && (
                                        <span
                                            className={cn(
                                                'badge text-xs',
                                                score > 70 ? 'badge-alpha' : 'badge-lottery'
                                            )}
                                        >
                                            {label}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </Tooltip >
                    );
                },
            },

            // Column 4: PRICE DELTA
            {
                id: 'price_delta',
                header: 'Price',
                cell: ({ row }) => {
                    const { avg_entry_price, current_price } = row.original;
                    const deltaClass = getPriceDeltaClass(avg_entry_price, current_price);

                    return (
                        <div className="tabular-nums">
                            <span className="text-slate-500">
                                Entry {formatPrice(avg_entry_price)}
                            </span>
                            <span className="text-slate-400 mx-1">&rarr;</span>
                            <span className={deltaClass}>
                                Now {formatPrice(current_price)}
                            </span>
                        </div>
                    );
                },
            },

            // Column 5: CONVICTION
            {
                id: 'conviction',
                header: ({ column }) => (
                    <button
                        className="flex items-center gap-1 hover:text-slate-900"
                        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
                    >
                        Conviction
                        <ArrowUpDown className="h-3 w-3" />
                    </button>
                ),
                accessorKey: 'total_conviction',
                cell: ({ row }) => (
                    <div className="text-slate-900 font-medium tabular-nums">
                        {formatCurrency(row.original.total_conviction)}
                    </div>
                ),
            },

            // Column 6: EXECUTE
            {
                id: 'execute',
                header: 'Execute',
                cell: ({ row }) => {
                    const { recommended_size, alpha_score, kelly_breakdown, market_slug, market_id } = row.original;
                    const isWarning = alpha_score < 40;

                    const handleBetClick = () => {
                        const baseUrl = 'https://polymarket.com';
                        const url = market_slug
                            ? `${baseUrl}/event/${market_slug}`
                            : `${baseUrl}/market/${market_id}`;
                        window.open(url, '_blank', 'noopener,noreferrer');
                    };

                    return (
                        <Tooltip content={<KellyTooltipContent size={recommended_size} breakdown={kelly_breakdown || {}} />}>
                            <button
                                onClick={handleBetClick}
                                className={cn(
                                    isWarning ? 'btn-warning' : 'btn-primary',
                                    'whitespace-nowrap hover:brightness-110 active:scale-95 transition-all'
                                )}
                            >
                                BET {formatCurrency(recommended_size)}
                            </button>
                        </Tooltip>
                    );
                },
            },
        ],
        [settings]
    );

    const table = useReactTable({
        data: signals,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
    });

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64 text-slate-500">
                Loading signals...
            </div>
        );
    }

    if (signals.length === 0) {
        return (
            <div className="flex items-center justify-center h-64 text-slate-500">
                No consensus signals found. Add more whale wallets or check API connection.
            </div>
        );
    }

    return (
        <div className="overflow-x-auto border border-slate-200 rounded-lg">
            <table className="terminal-table">
                <thead>
                    {table.getHeaderGroups().map((headerGroup) => (
                        <tr key={headerGroup.id}>
                            {headerGroup.headers.map((header) => (
                                <th key={header.id}>
                                    {header.isPlaceholder
                                        ? null
                                        : flexRender(
                                            header.column.columnDef.header,
                                            header.getContext()
                                        )}
                                </th>
                            ))}
                        </tr>
                    ))}
                </thead>
                <tbody>
                    {table.getRowModel().rows.map((row) => (
                        <tr key={row.id}>
                            {row.getVisibleCells().map((cell) => (
                                <td key={cell.id}>
                                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
