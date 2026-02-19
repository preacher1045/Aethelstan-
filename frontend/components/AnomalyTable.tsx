'use client';

import { AnomalyResult } from '@/lib/api';

interface AnomalyTableProps {
    results: AnomalyResult[];
}

export default function AnomalyTable({ results }: AnomalyTableProps) {
    if (results.length === 0) {
        return (
        <div className="text-center py-12 text-zinc-500">
            No anomaly results found
        </div>
        );
    }

    const getSeverityColor = (severity?: string) => {
        switch (severity?.toLowerCase()) {
        case 'critical':
            return 'bg-red-100 text-red-800 dark:bg-red-950/20 dark:text-red-400';
        case 'high':
            return 'bg-orange-100 text-orange-800 dark:bg-orange-950/20 dark:text-orange-400';
        case 'medium':
            return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950/20 dark:text-yellow-400';
        case 'low':
            return 'bg-blue-100 text-blue-800 dark:bg-blue-950/20 dark:text-blue-400';
        default:
            return 'bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-400';
        }
    };

    return (
        <div className="overflow-x-auto">
        <table className="w-full border-collapse">
            <thead>
            <tr className="bg-zinc-100 dark:bg-zinc-800 border-b border-zinc-200 dark:border-zinc-700">
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-600 dark:text-zinc-400 uppercase tracking-wider">
                Window
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-600 dark:text-zinc-400 uppercase tracking-wider">
                Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-600 dark:text-zinc-400 uppercase tracking-wider">
                Score
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-600 dark:text-zinc-400 uppercase tracking-wider">
                Confidence
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-600 dark:text-zinc-400 uppercase tracking-wider">
                Severity
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-600 dark:text-zinc-400 uppercase tracking-wider">
                Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-600 dark:text-zinc-400 uppercase tracking-wider">
                Model
                </th>
            </tr>
            </thead>
            <tbody className="bg-white dark:bg-zinc-900 divide-y divide-zinc-200 dark:divide-zinc-800">
            {results.map((result) => (
                <tr key={result.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                <td className="px-4 py-3 text-sm text-zinc-900 dark:text-zinc-100">
                    #{result.window_id}
                </td>
                <td className="px-4 py-3 text-sm">
                    {result.is_anomaly ? (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-950/20 dark:text-red-400">
                        Anomaly
                    </span>
                    ) : (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-950/20 dark:text-green-400">
                        Normal
                    </span>
                    )}
                </td>
                <td className="px-4 py-3 text-sm text-zinc-900 dark:text-zinc-100">
                    {result.anomaly_score?.toFixed(3) || 'N/A'}
                </td>
                <td className="px-4 py-3 text-sm text-zinc-900 dark:text-zinc-100">
                    {result.confidence_score ? `${(result.confidence_score * 100).toFixed(1)}%` : 'N/A'}
                </td>
                <td className="px-4 py-3 text-sm">
                    {result.severity_level ? (
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSeverityColor(result.severity_level)}`}>
                        {result.severity_level}
                    </span>
                    ) : (
                    <span className="text-zinc-500">N/A</span>
                    )}
                </td>
                <td className="px-4 py-3 text-sm text-zinc-900 dark:text-zinc-100">
                    {result.anomaly_type || 'N/A'}
                </td>
                <td className="px-4 py-3 text-sm text-zinc-500 dark:text-zinc-400">
                    {result.model_name || 'N/A'}
                </td>
                </tr>
            ))}
            </tbody>
        </table>
        </div>
    );
    }
