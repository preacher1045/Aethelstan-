'use client';

import { AnomalyResult } from '@/lib/api';

interface DashboardChartsProps {
    results: AnomalyResult[];
    totalPackets?: number;
}

export default function DashboardCharts({ results, totalPackets }: DashboardChartsProps) {
    if (results.length === 0) {
        return null;
    }

    // Calculate statistics
    const anomalyCount = results.filter(r => r.is_anomaly).length;
    const normalCount = results.length - anomalyCount;
    const anomalyPercentage = (anomalyCount / results.length) * 100;

    // Severity distribution
    const severityCounts = results.reduce((acc, r) => {
        if (r.is_anomaly && r.severity_level) {
        const level = r.severity_level.toLowerCase();
        acc[level] = (acc[level] || 0) + 1;
        }
        return acc;
    }, {} as Record<string, number>);

    const maxSeverity = Math.max(...Object.values(severityCounts), 1);

    // Anomaly score timeline
    const scoreData = results.map((r, idx) => ({
        window: idx + 1,
        score: r.anomaly_score || 0,
        isAnomaly: r.is_anomaly,
    }));

    const maxScore = Math.max(...scoreData.map(d => d.score), 1);

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Anomaly Distribution Pie Chart */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-4">
            Detection Overview
            </h3>
            <div className="flex items-center justify-center">
            <div className="relative w-48 h-48">
                <svg viewBox="0 0 100 100" className="transform -rotate-90">
                {/* Normal arc */}
                <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke="#22c55e"
                    strokeWidth="20"
                    strokeDasharray={`${(normalCount / results.length) * 251.2} 251.2`}
                    className="opacity-80"
                />
                {/* Anomaly arc */}
                <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke="#ef4444"
                    strokeWidth="20"
                    strokeDasharray={`${(anomalyCount / results.length) * 251.2} 251.2`}
                    strokeDashoffset={`-${(normalCount / results.length) * 251.2}`}
                    className="opacity-80"
                />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                <div className="text-3xl font-bold text-zinc-900 dark:text-zinc-100">
                    {anomalyPercentage.toFixed(1)}%
                </div>
                <div className="text-xs text-zinc-500">Anomalies</div>
                </div>
            </div>
            </div>
            <div className="mt-6 space-y-2">
            <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
                <span className="text-sm text-zinc-700 dark:text-zinc-300">Normal</span>
                </div>
                <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {normalCount} ({((normalCount / results.length) * 100).toFixed(1)}%)
                </span>
            </div>
            <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <span className="text-sm text-zinc-700 dark:text-zinc-300">Anomalies</span>
                </div>
                <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {anomalyCount} ({anomalyPercentage.toFixed(1)}%)
                </span>
            </div>
            </div>
        </div>

        {/* Severity Distribution Bar Chart */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-4">
            Severity Distribution
            </h3>
            <div className="space-y-4">
            {['critical', 'high', 'medium', 'low'].map((severity) => {
                const count = severityCounts[severity] || 0;
                const percentage = maxSeverity > 0 ? (count / maxSeverity) * 100 : 0;
                const colors = {
                critical: 'bg-red-500',
                high: 'bg-orange-500',
                medium: 'bg-yellow-500',
                low: 'bg-blue-500',
                };

                return (
                <div key={severity}>
                    <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300 capitalize">
                        {severity}
                    </span>
                    <span className="text-sm text-zinc-500">{count}</span>
                    </div>
                    <div className="w-full bg-zinc-200 dark:bg-zinc-800 rounded-full h-2">
                    <div
                        className={`h-2 rounded-full ${colors[severity as keyof typeof colors]} transition-all duration-500`}
                        style={{ width: `${percentage}%` }}
                    ></div>
                    </div>
                </div>
                );
            })}
            </div>
        </div>

        {/* Anomaly Score Timeline */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-6 lg:col-span-2">
            <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-4">
            Anomaly Score Timeline
            </h3>
            <div className="relative h-64 mt-8">
            {/* Y-axis labels */}
            <div className="absolute left-0 top-0 bottom-8 flex flex-col justify-between text-xs text-zinc-500">
                <span>{maxScore.toFixed(2)}</span>
                <span>{(maxScore * 0.75).toFixed(2)}</span>
                <span>{(maxScore * 0.5).toFixed(2)}</span>
                <span>{(maxScore * 0.25).toFixed(2)}</span>
                <span>0.00</span>
            </div>

            {/* Chart area */}
            <div className="ml-12 h-full pb-8 border-l border-b border-zinc-300 dark:border-zinc-700 relative">
                <svg className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
                {/* Grid lines */}
                {[0, 25, 50, 75, 100].map((y) => (
                    <line
                    key={y}
                    x1="0"
                    y1={`${y}%`}
                    x2="100%"
                    y2={`${y}%`}
                    stroke="currentColor"
                    strokeWidth="0.5"
                    className="text-zinc-200 dark:text-zinc-800"
                    />
                ))}

                {/* Line chart */}
                <polyline
                    points={scoreData
                    .map((d, i) => {
                        const x = (i / (scoreData.length - 1)) * 100;
                        const y = 100 - (d.score / maxScore) * 100;
                        return `${x},${y}`;
                    })
                    .join(' ')}
                    fill="none"
                    stroke="#3b82f6"
                    strokeWidth="2"
                    vectorEffect="non-scaling-stroke"
                />

                {/* Anomaly markers */}
                {scoreData.map((d, i) => {
                    if (!d.isAnomaly) return null;
                    const x = (i / (scoreData.length - 1)) * 100;
                    const y = 100 - (d.score / maxScore) * 100;
                    return (
                    <circle
                        key={i}
                        cx={`${x}%`}
                        cy={`${y}%`}
                        r="3"
                        fill="#ef4444"
                        vectorEffect="non-scaling-stroke"
                    />
                    );
                })}
                </svg>
            </div>

            {/* X-axis label */}
            <div className="ml-12 mt-2 text-center text-xs text-zinc-500">
                Time Window
            </div>
            </div>
        </div>
        </div>
    );
    }
