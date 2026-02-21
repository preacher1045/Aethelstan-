'use client';

import { useState } from 'react';
import { AnomalyResult, Insight } from '@/lib/api';

interface NetworkDashboardProps {
    results: AnomalyResult[];
    insights: Insight[];
    totalPackets?: number;
    totalBytes?: number;
    duration?: number;
}

interface TooltipProps {
    text: string;
    children: React.ReactNode;
}

function Tooltip({ text, children }: TooltipProps) {
    const [show, setShow] = useState(false);
    
    return (
        <div className="relative inline-block">
        <div
            onMouseEnter={() => setShow(true)}
            onMouseLeave={() => setShow(false)}
        >
            {children}
        </div>
        {show && (
            <div className="absolute z-50 w-64 p-3 text-xs bg-zinc-800 text-zinc-100 rounded-lg shadow-xl -top-2 left-full ml-2 border border-zinc-700">
            {text}
            <div className="absolute top-3 -left-1 w-2 h-2 bg-zinc-800 border-l border-b border-zinc-700 transform rotate-45"></div>
            </div>
        )}
        </div>
    );
}

export default function NetworkDashboard({ results, insights, totalPackets, totalBytes, duration }: NetworkDashboardProps) {
    const [timeRange, setTimeRange] = useState<'all' | '1h' | '24h'>('all');
    const [explanationMode, setExplanationMode] = useState<'technical' | 'beginner'>('technical');
    const [hoveredTimelinePoint, setHoveredTimelinePoint] = useState<number | null>(null);

    if (results.length === 0) {
        return (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-12 text-center">
            <p className="text-zinc-400">No analysis data available</p>
        </div>
        );
    }

    // Calculate metrics
    const anomalyCount = results.filter(r => r.is_anomaly).length;
    const criticalCount = results.filter(r => r.severity_level?.toLowerCase() === 'critical').length;
    const highCount = results.filter(r => r.severity_level?.toLowerCase() === 'high').length;
    
    const avgScore = results.reduce((sum, r) => sum + (r.anomaly_score || 0), 0) / results.length;
    const maxScore = Math.max(...results.map(r => r.anomaly_score || 0));
    
    // Network health score
    const healthScore = anomalyCount === 0 ? 'Optimal' :
                        anomalyCount / results.length < 0.1 ? 'Normal' :
                        anomalyCount / results.length < 0.3 ? 'Degraded' : 'Critical';
    
    const healthColor = healthScore === 'Optimal' || healthScore === 'Normal' ? 'text-emerald-400' :
                        healthScore === 'Degraded' ? 'text-amber-400' : 'text-red-400';

    // Calculate throughput
    const avgThroughput = duration && totalBytes ? (totalBytes / duration / 1024).toFixed(2) : 'N/A';

    // Severity distribution
    const severityData = [
        { name: 'Critical', count: criticalCount, color: 'bg-red-500' },
        { name: 'High', count: highCount, color: 'bg-orange-500' },
        { name: 'Medium', count: results.filter(r => r.severity_level?.toLowerCase() === 'medium').length, color: 'bg-amber-500' },
        { name: 'Low', count: results.filter(r => r.severity_level?.toLowerCase() === 'low').length, color: 'bg-cyan-500' },
    ];

    const maxSeverity = Math.max(...severityData.map(s => s.count), 1);

    // Anomaly timeline data
    const timelineData = results.map((r, idx) => ({
        window: idx + 1,
        score: r.anomaly_score || 0,
        isAnomaly: r.is_anomaly,
        severity: r.severity_level,
    }));

    return (
        <div className="space-y-6">
        {/* Header Controls */}
        <div className="flex items-center justify-between">
            <div>
            <h2 className="text-2xl font-bold text-zinc-100 flex items-center gap-3">
                Smart Network Traffic Analyzer
                <span className={`text-sm font-medium px-3 py-1 rounded-full ${
                healthScore === 'Optimal' || healthScore === 'Normal' 
                    ? 'bg-emerald-500/20 text-emerald-400' 
                    : healthScore === 'Degraded'
                    ? 'bg-amber-500/20 text-amber-400'
                    : 'bg-red-500/20 text-red-400'
                }`}>
                {healthScore}
                </span>
            </h2>
            <p className="text-sm text-zinc-400 mt-1">ML-Powered Traffic Analysis & Anomaly Detection</p>
            </div>
            <div className="flex items-center gap-2">
            <button
                onClick={() => setExplanationMode(explanationMode === 'technical' ? 'beginner' : 'technical')}
                className="px-3 py-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded border border-zinc-700 transition-colors"
            >
                {explanationMode === 'technical' ? '👨‍🎓 Beginner Mode' : '🔬 Technical Mode'}
            </button>
            </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <Tooltip text={explanationMode === 'beginner' 
            ? "Total number of time windows analyzed in your network capture" 
            : "Total flow aggregation windows extracted from PCAP"}>
            <div className="bg-linear-to-br from-zinc-900 to-zinc-800 border border-zinc-700 rounded-lg p-4 hover:border-cyan-500/50 transition-colors">
                <div className="text-xs text-zinc-400 uppercase tracking-wide mb-1">Total Windows</div>
                <div className="text-2xl font-bold text-zinc-100">{results.length}</div>
                <div className="text-xs text-cyan-400 mt-1">Time-aggregated</div>
            </div>
            </Tooltip>

            <Tooltip text={explanationMode === 'beginner'
            ? "Total packets captured in the network traffic"
            : "Sum of all packets across all flows in the capture"}>
            <div className="bg-linear-to-br from-zinc-900 to-zinc-800 border border-zinc-700 rounded-lg p-4 hover:border-cyan-500/50 transition-colors">
                <div className="text-xs text-zinc-400 uppercase tracking-wide mb-1">Total Packets</div>
                <div className="text-2xl font-bold text-zinc-100">{totalPackets?.toLocaleString() || 'N/A'}</div>
                <div className="text-xs text-zinc-500 mt-1">Captured</div>
            </div>
            </Tooltip>

            <Tooltip text={explanationMode === 'beginner'
            ? "Total amount of data transferred in megabytes"
            : "Aggregate data volume across all flows (application layer)"}>
            <div className="bg-linear-to-r from-zinc-900 to-zinc-800 border border-zinc-700 rounded-lg p-4 hover:border-cyan-500/50 transition-colors">
                <div className="text-xs text-zinc-400 uppercase tracking-wide mb-1">Data Transfer</div>
                <div className="text-2xl font-bold text-zinc-100">
                {totalBytes ? `${(totalBytes / 1024 / 1024).toFixed(2)}` : 'N/A'}
                </div>
                <div className="text-xs text-zinc-500 mt-1">MB</div>
            </div>
            </Tooltip>

            <Tooltip text={explanationMode === 'beginner'
            ? "Average speed of data transfer in kilobytes per second"
            : "Mean throughput calculated as total_bytes / capture_duration"}>
            <div className="bg-linear-to-r from-zinc-900 to-zinc-800 border border-zinc-700 rounded-lg p-4 hover:border-cyan-500/50 transition-colors">
                <div className="text-xs text-zinc-400 uppercase tracking-wide mb-1">Avg Throughput</div>
                <div className="text-2xl font-bold text-zinc-100">{avgThroughput}</div>
                <div className="text-xs text-zinc-500 mt-1">KB/s</div>
            </div>
            </Tooltip>

            <Tooltip text={explanationMode === 'beginner'
            ? "Time windows flagged as unusual by our ML algorithm"
            : "Anomalies detected using Isolation Forest / statistical deviation"}>
            <div className="bg-linear-to-r from-red-950/50 to-zinc-900 border border-red-900/50 rounded-lg p-4 hover:border-red-500/50 transition-colors">
                <div className="text-xs text-red-300 uppercase tracking-wide mb-1">Anomalies</div>
                <div className="text-2xl font-bold text-red-400">{anomalyCount}</div>
                <div className="text-xs text-red-500 mt-1">
                {((anomalyCount / results.length) * 100).toFixed(1)}% of windows
                </div>
            </div>
            </Tooltip>

            <Tooltip text={explanationMode === 'beginner'
            ? "Overall network health based on anomaly detection"
            : "Composite score: packet loss + anomaly rate + behavioral entropy"}>
            <div className={`bg-linear-to-r from-zinc-900 to-zinc-800 border rounded-lg p-4 hover:border-opacity-100 transition-colors ${
                healthScore === 'Optimal' || healthScore === 'Normal' 
                ? 'border-emerald-900/50 hover:border-emerald-500/50' 
                : healthScore === 'Degraded'
                ? 'border-amber-900/50 hover:border-amber-500/50'
                : 'border-red-900/50 hover:border-red-500/50'
            }`}>
                <div className="text-xs text-zinc-400 uppercase tracking-wide mb-1">Health Score</div>
                <div className={`text-2xl font-bold ${healthColor}`}>{healthScore}</div>
                <div className="text-xs text-zinc-500 mt-1">ML-Assessed</div>
            </div>
            </Tooltip>
        </div>

        {/* Main Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
            {/* Anomaly Score Timeline */}
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-6 lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
                <div>
                <h3 className="text-lg font-semibold text-zinc-100">Anomaly Score Timeline</h3>
                <p className="text-xs text-zinc-500 mt-1">
                    {explanationMode === 'beginner'
                    ? 'Higher scores indicate more unusual network behavior'
                    : 'ML confidence scores for behavioral deviation across time windows'}
                </p>
                </div>
            </div>
            
            <div className="relative h-64 mt-6">
                {/* Y-axis */}
                <div className="absolute left-0 top-0 bottom-8 w-12 flex flex-col justify-between text-xs text-zinc-500">
                <span>{maxScore.toFixed(2)}</span>
                <span>{(maxScore * 0.75).toFixed(2)}</span>
                <span>{(maxScore * 0.5).toFixed(2)}</span>
                <span>{(maxScore * 0.25).toFixed(2)}</span>
                <span>0.00</span>
                </div>

                {/* Chart */}
                <div className="ml-14 h-full pb-8 border-l border-b border-zinc-700 relative">
                <svg className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
                    {/* Grid */}
                    {[0, 25, 50, 75, 100].map((y) => (
                    <line
                        key={y}
                        x1="0"
                        y1={`${y}%`}
                        x2="100%"
                        y2={`${y}%`}
                        stroke="#3f3f46"
                        strokeWidth="0.5"
                        opacity="0.3"
                    />
                    ))}

                    {/* Area fill */}
                    <defs>
                    <linearGradient id="scoreGradient" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.3" />
                        <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
                    </linearGradient>
                    </defs>

                    <polygon
                    points={`0,100 ${timelineData
                        .map((d, i) => {
                        const x = (i / (timelineData.length - 1)) * 100;
                        const y = 100 - (d.score / maxScore) * 100;
                        return `${x},${y}`;
                        })
                        .join(' ')} 100,100`}
                    fill="url(#scoreGradient)"
                    />

                    {/* Line */}
                    <polyline
                    points={timelineData
                        .map((d, i) => {
                        const x = (i / (timelineData.length - 1)) * 100;
                        const y = 100 - (d.score / maxScore) * 100;
                        return `${x},${y}`;
                        })
                        .join(' ')}
                    fill="none"
                    stroke="#06b6d4"
                    strokeWidth="2"
                    vectorEffect="non-scaling-stroke"
                    />

                    {/* Anomaly markers */}
                    {timelineData.map((d, i) => {
                    if (!d.isAnomaly) return null;
                    const x = (i / (timelineData.length - 1)) * 100;
                    const y = 100 - (d.score / maxScore) * 100;
                    const color = d.severity === 'critical' ? '#ef4444' : 
                                    d.severity === 'high' ? '#f97316' : 
                                    d.severity === 'medium' ? '#f59e0b' : '#3b82f6';
                    return (
                        <circle
                        key={i}
                        cx={`${x}%`}
                        cy={`${y}%`}
                        r="4"
                        fill={color}
                        stroke="#18181b"
                        strokeWidth="1.5"
                        vectorEffect="non-scaling-stroke"
                        />
                    );
                    })}
                </svg>
                {/* Interactive hover layer */}
                <div className="absolute inset-0">
                  {timelineData.map((d, i) => {
                    if (!d.isAnomaly) return null;
                    const x = (i / (timelineData.length - 1)) * 100;
                    const y = 100 - (d.score / maxScore) * 100;
                    const color = d.severity === 'critical' ? 'bg-red-500' : 
                                    d.severity === 'high' ? 'bg-orange-500' : 
                                    d.severity === 'medium' ? 'bg-amber-500' : 'bg-blue-500';
                    return (
                      <div
                        key={i}
                        className="absolute group"
                        style={{ left: `${x}%`, top: `${y}%`, transform: 'translate(-50%, -50%)' }}
                        onMouseEnter={() => setHoveredTimelinePoint(i)}
                        onMouseLeave={() => setHoveredTimelinePoint(null)}
                      >
                        <div className={`w-2 h-2 rounded-full ${color} cursor-pointer opacity-0 group-hover:opacity-100 transition-opacity ring-2 ring-white/50`} />
                        {hoveredTimelinePoint === i && (
                          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-zinc-900 border border-cyan-500/50 rounded text-[10px] text-zinc-100 whitespace-nowrap z-10 pointer-events-none">
                            <div className="font-semibold">Window {i + 1}</div>
                            <div>Score: {d.score.toFixed(3)}</div>
                            <div className="text-red-400 capitalize">
                              {d.severity} Severity
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
                </div>

                <div className="ml-14 mt-2 flex items-center justify-center gap-4 text-xs text-zinc-500">
                <span>← Earlier</span>
                <span className="text-zinc-400">Time Window Progression</span>
                <span>Later →</span>
                </div>
            </div>
            </div>

            {/* Severity Distribution */}
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
                <div>
                <h3 className="text-lg font-semibold text-zinc-100">Threat Severity Distribution</h3>
                <p className="text-xs text-zinc-500 mt-1">
                    {explanationMode === 'beginner'
                    ? 'Breakdown of detected issues by importance level'
                    : 'Anomaly classification by ML-assigned severity levels'}
                </p>
                </div>
            </div>

            <div className="space-y-4">
                {severityData.map((item) => {
                const percentage = (item.count / maxSeverity) * 100;
                return (
                    <div key={item.name}>
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-zinc-300">{item.name}</span>
                        <span className="text-sm text-zinc-500">{item.count} anomalies</span>
                    </div>
                    <div className="relative w-full bg-zinc-800 rounded-full h-3 overflow-hidden">
                        <div
                        className={`h-3 ${item.color} rounded-full transition-all duration-700 ease-out`}
                        style={{ width: `${percentage}%` }}
                        >
                        <div className="absolute inset-0 bg-linear-to-r from-transparent via-white/10 to-transparent animate-shimmer"></div>
                        </div>
                    </div>
                    </div>
                );
                })}
            </div>

            {criticalCount > 0 && (
                <div className="mt-6 p-3 bg-red-950/30 border border-red-900/50 rounded-lg">
                <div className="flex items-start gap-2">
                    <span className="text-red-400 text-xl">⚠️</span>
                    <div>
                    <p className="text-sm font-medium text-red-300">Critical Threats Detected</p>
                    <p className="text-xs text-red-400/80 mt-1">
                        {criticalCount} window{criticalCount > 1 ? 's' : ''} flagged as high-priority. Review immediately.
                    </p>
                    </div>
                </div>
                </div>
            )}
            </div>

            {/* Detection Stats */}
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
                <div>
                <h3 className="text-lg font-semibold text-zinc-100">Detection Statistics</h3>
                <p className="text-xs text-zinc-500 mt-1">Model performance metrics</p>
                </div>
            </div>

            <div className="space-y-4">
                <div className="flex items-center justify-between py-3 border-b border-zinc-800">
                <span className="text-sm text-zinc-400">Average Anomaly Score</span>
                <span className="text-lg font-semibold text-cyan-400">{avgScore.toFixed(3)}</span>
                </div>
                <div className="flex items-center justify-between py-3 border-b border-zinc-800">
                <span className="text-sm text-zinc-400">Max Anomaly Score</span>
                <span className="text-lg font-semibold text-red-400">{maxScore.toFixed(3)}</span>
                </div>
                <div className="flex items-center justify-between py-3 border-b border-zinc-800">
                <span className="text-sm text-zinc-400">Detection Rate</span>
                <span className="text-lg font-semibold text-amber-400">
                    {((anomalyCount / results.length) * 100).toFixed(1)}%
                </span>
                </div>
                <div className="flex items-center justify-between py-3">
                <span className="text-sm text-zinc-400">Normal Behavior</span>
                <span className="text-lg font-semibold text-emerald-400">
                    {(((results.length - anomalyCount) / results.length) * 100).toFixed(1)}%
                </span>
                </div>
            </div>

            <div className="mt-6 p-3 bg-cyan-950/20 border border-cyan-900/30 rounded-lg">
                <p className="text-xs text-cyan-300">
                💡 {explanationMode === 'beginner' 
                    ? 'These scores help identify unusual patterns in your network traffic'
                    : 'Scores derived from Isolation Forest feature importance & statistical deviation'}
                </p>
            </div>
            </div>
        </div>

        {/* Educational Panel */}
        {explanationMode === 'beginner' && (
            <div className="bg-linear-to-r from-blue-950/30 to-purple-950/30 border border-blue-900/30 rounded-lg p-6">
            <h4 className="text-sm font-semibold text-blue-300 mb-3">📚 Understanding Your Dashboard</h4>
            <div className="grid md:grid-cols-2 gap-4 text-xs text-zinc-300">
                <div>
                <p className="font-medium text-blue-200 mb-1">What are anomalies?</p>
                <p>Unusual patterns in network traffic that may indicate security threats, performance issues, or misconfigurations.</p>
                </div>
                <div>
                <p className="font-medium text-blue-200 mb-1">Why does severity matter?</p>
                <p>Critical issues need immediate attention, while lower severity items can be addressed during routine maintenance.</p>
                </div>
                <div>
                <p className="font-medium text-blue-200 mb-1">How is health calculated?</p>
                <p>Based on the percentage of anomalous traffic and the severity distribution across your capture.</p>
                </div>
                <div>
                <p className="font-medium text-blue-200 mb-1">What should I do next?</p>
                <p>Review the "Insights" tab for AI-generated explanations and recommended actions.</p>
                </div>
            </div>
            </div>
        )}
    </div>
  );
}
