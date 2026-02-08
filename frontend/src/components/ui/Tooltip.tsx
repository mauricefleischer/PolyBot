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

                setCoords({ top, left });
            }
            setIsVisible(true);
        }, 300);
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

interface AlphaTooltipContentProps {
    score: number;
    breakdown: string[];
}

export function AlphaTooltipContent({ score, breakdown }: AlphaTooltipContentProps) {
    return (
        <div className="space-y-1">
            <div className="font-semibold text-emerald-400">Alpha Score: {score}</div>
            <div className="text-slate-300 text-[10px] space-y-0.5">
                {breakdown.map((item, i) => (
                    <div key={i}>{item}</div>
                ))}
            </div>
        </div>
    );
}

interface KellyTooltipContentProps {
    size: number;
    breakdown: {
        net_odds?: number;
        real_prob?: number;
        kelly_multiplier?: number;
        capped_percent?: number;
        reason?: string;
    };
}

export function KellyTooltipContent({ size, breakdown }: KellyTooltipContentProps) {
    const kellyName = breakdown.kelly_multiplier === 0.1
        ? 'Conservative'
        : breakdown.kelly_multiplier === 0.5
            ? 'Aggressive'
            : 'Quarter Kelly';

    if (breakdown.reason === 'Negative EV') {
        return (
            <div className="text-amber-400">
                No bet recommended (Negative Expected Value)
            </div>
        );
    }

    return (
        <div className="space-y-1">
            <div className="font-semibold text-blue-400">${size} Recommended</div>
            <div className="text-slate-300 text-[10px] space-y-0.5">
                <div>Odds: {breakdown.net_odds}:1</div>
                <div>Est. Prob: {((breakdown.real_prob || 0) * 100).toFixed(0)}%</div>
                <div>Strategy: {kellyName}</div>
                {breakdown.capped_percent && (
                    <div>Risk: {(breakdown.capped_percent * 100).toFixed(1)}%</div>
                )}
            </div>
        </div>
    );
}
