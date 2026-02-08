import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import numeral from 'numeral';

/**
 * Merge Tailwind classes with clsx
 */
export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

/**
 * Format currency value
 */
export function formatCurrency(value: number): string {
    return numeral(value).format('$0,0.00');
}

/**
 * Format price (0-1 range)
 */
export function formatPrice(value: number): string {
    return numeral(value).format('$0.00');
}

/**
 * Format percentage
 */
export function formatPercent(value: number): string {
    const prefix = value >= 0 ? '+' : '';
    return `${prefix}${numeral(value / 100).format('0.00%')}`;
}

/**
 * Format large numbers
 */
export function formatNumber(value: number): string {
    if (value >= 1000000) {
        return numeral(value).format('$0.0a').toUpperCase();
    }
    if (value >= 1000) {
        return numeral(value).format('$0,0');
    }
    return numeral(value).format('$0.00');
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text: string, maxLength: number): string {
    if (text.length <= maxLength) return text;
    return `${text.substring(0, maxLength)}...`;
}

/**
 * Get heatmap class based on wallet count
 */
export function getHeatmapClass(walletCount: number): string {
    if (walletCount >= 4) return 'heatmap-high';
    if (walletCount >= 2) return 'heatmap-medium';
    return '';
}

/**
 * Get alpha score label and class
 */
export function getAlphaScoreInfo(score: number): { label: string; className: string } {
    if (score < 40) {
        return { label: 'LOTTERY', className: 'text-rose-600' };
    }
    if (score > 70) {
        return { label: 'ALPHA', className: 'text-emerald-600' };
    }
    return { label: '', className: 'text-slate-600' };
}

/**
 * Get price delta class
 */
export function getPriceDeltaClass(entry: number, current: number): string {
    if (current > entry) return 'price-profit';
    if (current < entry) return 'price-loss';
    return 'text-slate-600';
}
