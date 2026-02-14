import { useState, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

interface TooltipProps {
    content: ReactNode;
    children: ReactNode;
    position?: 'top' | 'bottom' | 'left' | 'right';
}

export function Tooltip({ content, children, position = 'top' }: TooltipProps) {
    const [isVisible, setIsVisible] = useState(false);
    const [coords, setCoords] = useState({ top: 0, left: 0 });
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const triggerRef = useRef<HTMLDivElement>(null);

    const showTooltip = () => {
        timeoutRef.current = setTimeout(() => {
            if (triggerRef.current) {
                const rect = triggerRef.current.getBoundingClientRect();
                const scrollTop = window.scrollY;
                const scrollLeft = window.scrollX;

                let top = 0;
                let left = 0;

                // Adjust positioning to avoid edge overflow
                const tooltipWidth = 250; // Approximated
                const viewportWidth = window.innerWidth;

                switch (position) {
                    case 'top':
                        top = rect.top + scrollTop - 8;
                        left = rect.left + scrollLeft + rect.width / 2;
                        break;
                    case 'bottom':
                        top = rect.bottom + scrollTop + 8;
                        left = rect.left + scrollLeft + rect.width / 2;
                        break;
                    case 'left':
                        top = rect.top + scrollTop + rect.height / 2;
                        left = rect.left + scrollLeft - 8;
                        break;
                    case 'right':
                        top = rect.top + scrollTop + rect.height / 2;
                        left = rect.right + scrollLeft + 8;
                        break;
                }

                // Simple edge detection for right side
                if (left + tooltipWidth / 2 > viewportWidth) {
                    left = viewportWidth - tooltipWidth / 2 - 20;
                }

                setCoords({ top, left });
            }
            setIsVisible(true);
        }, 100); // Faster hover
    };

    const hideTooltip = () => {
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
        }
        setIsVisible(false);
    };

    const getTransformClass = () => {
        switch (position) {
            case 'top': return 'translate-x-[-50%] translate-y-[-100%]';
            case 'bottom': return 'translate-x-[-50%]';
            case 'left': return 'translate-x-[-100%] translate-y-[-50%]';
            case 'right': return 'translate-y-[-50%]';
            default: return 'translate-x-[-50%] translate-y-[-100%]';
        }
    };

    const tooltipElement = isVisible ? (
        <div
            className={`absolute z-[9999] ${getTransformClass()} pointer-events-none`}
            style={{ top: coords.top, left: coords.left }}
        >
            <div className="bg-slate-900 text-white text-xs rounded-lg px-3 py-2 shadow-xl border border-slate-700 max-w-xs">
                {content}
            </div>
        </div>
    ) : null;

    return (
        <div
            ref={triggerRef}
            className="inline-block"
            onMouseEnter={showTooltip}
            onMouseLeave={hideTooltip}
        >
            {children}
            {typeof document !== 'undefined' && createPortal(tooltipElement, document.body)}
        </div>
    );
}

interface AlphaBreakdownData {
    base?: number;
    flb?: number;
    momentum?: number;
    smart_short?: number;
    freshness?: number;
    total?: number;
    details?: string[];
}

interface AlphaTooltipContentProps {
    score: number;
    breakdown: AlphaBreakdownData | string[];
}

export function AlphaTooltipContent({ score, breakdown }: AlphaTooltipContentProps) {
    // Handle both v1 (string[]) and v2 (structured object) formats
    const isV2 = breakdown && !Array.isArray(breakdown) && typeof breakdown === 'object';

    const scoreColor = score >= 70
        ? 'text-emerald-400'
        : score >= 40
            ? 'text-yellow-400'
            : 'text-red-400';

    if (isV2) {
        const b = breakdown as AlphaBreakdownData;
        return (
            <div className="space-y-1.5 min-w-[220px]">
                <div className={`font-bold ${scoreColor}`}>
                    Alpha Score: {score}/100
                </div>
                <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[10px] text-slate-400 border-t border-slate-700 pt-1">
                    <span>Base</span><span className="text-right">{b.base ?? 50}</span>
                    <span>FLB</span><span className={`text-right ${(b.flb ?? 0) > 0 ? 'text-emerald-400' : (b.flb ?? 0) < 0 ? 'text-red-400' : ''}`}>{(b.flb ?? 0) > 0 ? '+' : ''}{b.flb ?? 0}</span>
                    <span>Momentum</span><span className={`text-right ${(b.momentum ?? 0) > 0 ? 'text-emerald-400' : (b.momentum ?? 0) < 0 ? 'text-red-400' : ''}`}>{(b.momentum ?? 0) > 0 ? '+' : ''}{b.momentum ?? 0}</span>
                    <span>Smart Short</span><span className={`text-right ${(b.smart_short ?? 0) > 0 ? 'text-emerald-400' : ''}`}>{(b.smart_short ?? 0) > 0 ? '+' : ''}{b.smart_short ?? 0}</span>
                    <span>Freshness</span><span className={`text-right ${(b.freshness ?? 0) > 0 ? 'text-emerald-400' : ''}`}>{(b.freshness ?? 0) > 0 ? '+' : ''}{b.freshness ?? 0}</span>
                </div>
                {b.details && b.details.length > 1 && (
                    <div className="text-slate-300 text-[10px] space-y-0.5 border-t border-slate-700 pt-1">
                        {b.details.slice(1).map((item, i) => (
                            <div key={i}>{item}</div>
                        ))}
                    </div>
                )}
            </div>
        );
    }

    // Fallback for v1 format (string array)
    return (
        <div className="space-y-1">
            <div className={`font-semibold ${scoreColor}`}>Alpha Score: {score}</div>
            <div className="text-slate-300 text-[10px] space-y-0.5">
                {(breakdown as string[]).map((item, i) => (
                    <div key={i}>{item}</div>
                ))}
            </div>
        </div>
    );
}

interface WhaleTooltipContentProps {
    meta: {
        avg_score: number;
        has_elite: boolean;
        has_bagholder: boolean;
        wallet_tiers: Record<string, string>;
    };
}

export function WhaleTooltipContent({ meta }: WhaleTooltipContentProps) {
    const sortedTiers = Object.entries(meta.wallet_tiers).sort(([, a], [, b]) => {
        const tierOrder = { ELITE: 4, PRO: 3, STD: 2, WEAK: 1, UNRATED: 0 };
        return (tierOrder[b as keyof typeof tierOrder] || 0) - (tierOrder[a as keyof typeof tierOrder] || 0);
    });

    return (
        <div className="space-y-1.5 min-w-[200px]">
            <div className="flex items-center justify-between border-b border-slate-700 pb-1">
                <span className="font-bold text-slate-200">Consensus Quality</span>
                <span className={`font-mono font-bold ${meta.avg_score >= 80 ? 'text-purple-400' :
                    meta.avg_score >= 60 ? 'text-emerald-400' :
                        'text-amber-400'
                    }`}>
                    Avg: {meta.avg_score}
                </span>
            </div>
            <div className="space-y-1">
                {sortedTiers.map(([wallet, tier]) => (
                    <div key={wallet} className="flex items-center justify-between text-[10px] font-mono">
                        <span className="text-slate-400">{wallet}</span>
                        <span className={
                            tier === 'ELITE' ? 'text-purple-400 font-bold' :
                                tier === 'PRO' ? 'text-emerald-400' :
                                    tier === 'WEAK' ? 'text-rose-400' : 'text-slate-500'
                        }>
                            {tier}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}

interface WhaleScoreTooltipProps {
    score: {
        roi_score: number;
        precision_score: number;
        discipline_score: number;
        timing_score: number;
        total_score: number;
        trade_count: number;
        tier: string;
    };
}

export function WhaleScoreTooltip({ score }: WhaleScoreTooltipProps) {
    return (
        <div className="space-y-2 min-w-[200px]">
            <div className="flex items-center justify-between border-b border-slate-700 pb-1">
                <span className="font-bold text-slate-200">Whale Score</span>
                <span className={`font-mono font-bold ${score.tier === 'ELITE' ? 'text-purple-400' :
                    score.tier === 'PRO' ? 'text-emerald-400' :
                        score.tier === 'WEAK' ? 'text-rose-400' : 'text-slate-400'
                    }`}>
                    {score.total_score} ({score.tier})
                </span>
            </div>

            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] text-slate-300">
                <span>ROI Score</span>
                <span className={`text-right ${score.roi_score >= 80 ? 'text-emerald-400' : 'text-slate-200'}`}>
                    {score.roi_score}
                </span>

                <span>Precision</span>
                <span className={`text-right ${score.precision_score >= 80 ? 'text-emerald-400' : 'text-slate-200'}`}>
                    {score.precision_score}
                </span>

                <span>Discipline</span>
                <span className={`text-right ${score.discipline_score >= 80 ? 'text-emerald-400' : 'text-slate-200'}`}>
                    {score.discipline_score}
                </span>

                <span>Timing</span>
                <span className={`text-right ${score.timing_score >= 80 ? 'text-emerald-400' : 'text-slate-200'}`}>
                    {score.timing_score}
                </span>

                <div className="col-span-2 pt-1 mt-1 border-t border-slate-700 flex justify-between items-center text-slate-400">
                    <span>Analyzed Trades</span>
                    <span className="text-slate-200 font-mono">{score.trade_count}</span>
                </div>
            </div>
        </div>
    );
}

interface KellyTooltipContentProps {
    size: number;
    breakdown: {
        net_odds?: number;
        real_prob?: number;
        prob_boosts?: string[];
        kelly_multiplier?: number;
        capped_percent?: number;
        reason?: string;
        kelly_raw?: number;
        strategy?: string;
        yield_trigger?: number;
        fixed_pct?: number;
        final_pct?: number;
    };
}

export function KellyTooltipContent({ size, breakdown }: KellyTooltipContentProps) {
    // Yield Mode Display
    if (breakdown.strategy === 'YIELD_MODE') {
        return (
            <div className="space-y-1.5 min-w-[220px]">
                <div className="flex items-center justify-between border-b border-emerald-900/50 pb-1">
                    <span className="font-bold text-emerald-400">Yield Mode Active</span>
                    <span className="text-[10px] text-emerald-600 font-mono">FIXED SIZE</span>
                </div>
                <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[10px] text-slate-300">
                    <span>Trigger Price</span>
                    <span className="text-right text-slate-200">${(breakdown.yield_trigger || 0).toFixed(2)}</span>

                    <span>Fixed Allocation</span>
                    <span className="text-right text-emerald-400">{((breakdown.fixed_pct || 0) * 100).toFixed(1)}%</span>

                    <div className="col-span-2 pt-1 text-[9px] text-slate-500 italic text-center">
                        Price &gt; Trigger • Whale Consensus Met
                    </div>

                    <span className="pt-2 mt-1 border-t border-slate-800 font-bold text-slate-200">Recommended</span>
                    <span className="pt-2 mt-1 border-t border-slate-800 font-bold text-right text-emerald-400 text-base">
                        ${size.toLocaleString()}
                    </span>
                </div>
            </div>
        );
    }

    const kellyName = breakdown.kelly_multiplier === 0.1
        ? 'Conservative'
        : breakdown.kelly_multiplier === 0.5
            ? 'Aggressive'
            : 'Quarter Kelly';

    if (breakdown.reason === 'Negative EV' || size === 0) {
        return (
            <div className="text-amber-400 min-w-[200px]">
                <div className="font-bold border-b border-amber-900/50 pb-1 mb-1">No Bet Recommended</div>
                <div className="text-[10px] text-slate-300">
                    Reason: {breakdown.reason || 'Risk limit reached'}
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-1.5 min-w-[220px]">
            <div className="flex items-center justify-between border-b border-slate-700 pb-1">
                <span className="font-bold text-blue-400">${size} Recommended</span>
                <span className="text-[10px] text-slate-400">{kellyName}</span>
            </div>

            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[10px] text-slate-300">
                <span>Net Odds</span>
                <span className="text-right text-slate-200">{breakdown.net_odds}:1</span>

                <span>Real Prob</span>
                <span className="text-right text-emerald-400">
                    {((breakdown.real_prob || 0) * 100).toFixed(1)}%
                </span>

                {breakdown.prob_boosts && breakdown.prob_boosts.length > 0 && (
                    <div className="col-span-2 text-[9px] text-emerald-500/80 italic text-right">
                        {breakdown.prob_boosts.join(', ')}
                    </div>
                )}

                <span className="pt-1 mt-1 border-t border-slate-800 text-slate-400">Kelly Raw</span>
                <span className="pt-1 mt-1 border-t border-slate-800 text-right">
                    {((breakdown.kelly_raw || 0) * 100).toFixed(1)}%
                </span>

                <span className="font-bold text-slate-200">Final Risk</span>
                <span className="font-bold text-right text-blue-400">
                    {((breakdown.capped_percent || 0) * 100).toFixed(1)}%
                </span>
            </div>
        </div>
    );
}

export function AlphaGuideTooltip() {
    return (
        <div className="space-y-2 min-w-[220px]">
            <div className="font-bold border-b border-slate-700 pb-1 text-slate-200">
                Alpha Score Guide
            </div>

            <div className="grid grid-cols-[70px_1fr] gap-x-2 gap-y-1.5 text-[10px] text-slate-300">
                <span className="text-slate-400 font-mono">Base</span>
                <span>Signal Strength (Volume/Price)</span>

                <span className="text-slate-400 font-mono">FLB</span>
                <span>Front-running protection</span>

                <span className="text-slate-400 font-mono">Momentum</span>
                <span>Price Velocity & Acceleration</span>

                <span className="text-slate-400 font-mono">Smart Short</span>
                <span>High value trading against retail</span>

                <span className="text-slate-400 font-mono">Freshness</span>
                <span>Time decay penalty</span>
            </div>
        </div>
    );
}

export function TierGuideTooltip() {
    return (
        <div className="space-y-2 min-w-[180px]">
            <div className="font-bold border-b border-slate-700 pb-1 text-slate-200">
                Whale Tier Guide
            </div>
            <div className="space-y-1.5 text-[10px]">
                <div className="flex justify-between items-center">
                    <span className="font-bold text-purple-400">ELITE (80+)</span>
                    <span className="text-slate-400">Perfect Track Record</span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="font-bold text-emerald-400">PRO (60-79)</span>
                    <span className="text-slate-400">Consistent Profit</span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="font-bold text-amber-400">STD (40-59)</span>
                    <span className="text-slate-400">Average Trader</span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="font-bold text-rose-400">WEAK (&lt;40)</span>
                    <span className="text-slate-400">Counter-Trade Signal</span>
                </div>
            </div>
            <div className="border-t border-slate-700 pt-1.5 mt-1 text-[9px] text-slate-500 leading-tight italic">
                Based on ROI, Precision, Discipline, and Timing over last 500 trades.
            </div>
        </div>
    );
}

export function PerformanceTagsTooltip() {
    return (
        <div className="space-y-2 min-w-[200px]">
            <div className="font-bold border-b border-slate-700 pb-1 text-slate-200">
                Performance Tags Guide
            </div>
            <div className="grid grid-cols-[45px_1fr] gap-x-2 gap-y-1.5 text-[10px] text-slate-300">
                <span className="text-purple-400 font-bold font-mono">PROF</span>
                <span>Highly profitable trader</span>

                <span className="text-emerald-400 font-bold font-mono">PRC</span>
                <span>High precision sniper</span>

                <span className="text-blue-400 font-bold font-mono">HLD</span>
                <span>Diamond hands (holds &gt;24h)</span>

                <span className="text-amber-400 font-bold font-mono">PNIR</span>
                <span>Early pioneer in markets</span>

                <span className="text-rose-400 font-bold font-mono">DUMP</span>
                <span>Fast dumper / Paper hands</span>

                <span className="text-slate-400 font-bold font-mono">CHRN</span>
                <span>High volume churner</span>
            </div>
        </div>
    );
}
