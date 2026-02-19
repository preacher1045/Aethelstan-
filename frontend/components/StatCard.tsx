'use client';

interface StatCardProps {
    title: string;
    value: string | number;
    subtitle?: string;
    icon?: React.ReactNode;
    trend?: 'up' | 'down' | 'neutral';
    trendValue?: string;
}

export default function StatCard({
    title,
    value,
    subtitle,
    icon,
    trend,
    trendValue,
    }: StatCardProps) {
    const getTrendColor = () => {
        switch (trend) {
        case 'up':
            return 'text-red-600 dark:text-red-400';
        case 'down':
            return 'text-green-600 dark:text-green-400';
        default:
            return 'text-zinc-600 dark:text-zinc-400';
        }
    };

    return (
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-zinc-600 dark:text-zinc-400">{title}</p>
            {icon && <div className="text-zinc-400">{icon}</div>}
        </div>
        <div className="flex items-baseline justify-between">
            <h3 className="text-3xl font-bold text-zinc-900 dark:text-zinc-100">{value}</h3>
            {trend && trendValue && (
            <span className={`text-sm font-medium ${getTrendColor()}`}>
                {trend === 'up' && '↑'} {trend === 'down' && '↓'} {trendValue}
            </span>
            )}
        </div>
        {subtitle && (
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">{subtitle}</p>
        )}
        </div>
    );
    }
