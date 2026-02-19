'use client';

import { Insight } from '@/lib/api';

interface InsightsPanelProps {
    insights: Insight[];
}

export default function InsightsPanel({ insights }: InsightsPanelProps) {
    const summary = insights.find(i => i.insight_type === 'summary');
    const alerts = insights.filter(i => i.insight_type === 'alert');

    const getSeverityColor = (severity?: string) => {
        switch (severity?.toLowerCase()) {
        case 'critical':
            return 'bg-red-100 text-red-800 border-red-200 dark:bg-red-950/20 dark:text-red-400 dark:border-red-800';
        case 'high':
            return 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-950/20 dark:text-orange-400 dark:border-orange-800';
        case 'medium':
            return 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-950/20 dark:text-yellow-400 dark:border-yellow-800';
        case 'low':
            return 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-950/20 dark:text-blue-400 dark:border-blue-800';
        default:
            return 'bg-zinc-100 text-zinc-800 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700';
        }
    };

    const getAlertIcon = (severity?: string) => {
        switch (severity?.toLowerCase()) {
        case 'critical':
        case 'high':
            return '🚨';
        case 'medium':
            return '⚠️';
        case 'low':
            return 'ℹ️';
        default:
            return '📊';
        }
    };

    return (
        <div className="space-y-6">
        {/* Summary Section */}
        {summary && (
            <div className="bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-3">
                Summary
            </h3>
            <p className="text-sm text-blue-800 dark:text-blue-200 whitespace-pre-wrap">
                {summary.summary}
            </p>
            {summary.details && (() => {
                try {
                    const detailsText = typeof summary.details === 'string'
                        ? JSON.stringify(JSON.parse(summary.details), null, 2)
                        : JSON.stringify(summary.details, null, 2);
                    return (
                        <div className="mt-4 pt-4 border-t border-blue-200 dark:border-blue-800">
                            <pre className="text-xs text-blue-700 dark:text-blue-300 overflow-x-auto">
                                {detailsText}
                            </pre>
                        </div>
                    );
                } catch (e) {
                    return (
                        <div className="mt-4 pt-4 border-t border-blue-200 dark:border-blue-800">
                            <p className="text-xs text-blue-700 dark:text-blue-300">
                                {String(summary.details)}
                            </p>
                        </div>
                    );
                }
            })()}
            </div>
        )}

        {/* Alerts Section */}
        {alerts.length > 0 && (
            <div>
            <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-4">
                Alerts ({alerts.length})
            </h3>
            <div className="space-y-3">
                {alerts.map((alert) => (
                <div
                    key={alert.id}
                    className={`border rounded-lg p-4 ${getSeverityColor(alert.severity)}`}
                >
                    <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center space-x-2">
                        <span className="text-xl">{getAlertIcon(alert.severity)}</span>
                        <div>
                        <h4 className="font-semibold text-sm">
                            {alert.alert_type || 'Alert'}
                        </h4>
                        {alert.confidence && (
                            <span className="text-xs opacity-75">
                            Confidence: {(alert.confidence * 100).toFixed(0)}%
                            </span>
                        )}
                        </div>
                    </div>
                    {alert.severity && (
                        <span className="text-xs font-medium uppercase px-2 py-1 rounded">
                        {alert.severity}
                        </span>
                    )}
                    </div>
                    <p className="text-sm mb-3">{alert.summary}</p>
                    
                    {/* Alert Stats */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                    {alert.packet_count !== null && alert.packet_count !== undefined && (
                        <div>
                        <span className="opacity-75">Packets:</span>{' '}
                        <span className="font-medium">{alert.packet_count.toLocaleString()}</span>
                        </div>
                    )}
                    {alert.total_bytes !== null && alert.total_bytes !== undefined && (
                        <div>
                        <span className="opacity-75">Bytes:</span>{' '}
                        <span className="font-medium">{(alert.total_bytes / 1024).toFixed(1)} KB</span>
                        </div>
                    )}
                    {alert.unique_src_ips !== null && alert.unique_src_ips !== undefined && (
                        <div>
                        <span className="opacity-75">Src IPs:</span>{' '}
                        <span className="font-medium">{alert.unique_src_ips}</span>
                        </div>
                    )}
                    {alert.unique_dst_ips !== null && alert.unique_dst_ips !== undefined && (
                        <div>
                        <span className="opacity-75">Dst IPs:</span>{' '}
                        <span className="font-medium">{alert.unique_dst_ips}</span>
                        </div>
                    )}
                    </div>

                    {/* Tags */}
                    {alert.tags && alert.tags.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1">
                        {alert.tags.map((tag, idx) => (
                        <span
                            key={idx}
                            className="text-xs px-2 py-1 rounded bg-white/50 dark:bg-black/20"
                        >
                            {tag}
                        </span>
                        ))}
                    </div>
                    )}
                </div>
                ))}
            </div>
            </div>
        )}

        {insights.length === 0 && (
            <div className="text-center py-12 text-zinc-500">
            No insights available yet
            </div>
        )}
        </div>
    );
    }
