'use client';

import { useEffect, useMemo, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getSessions, getResults, getInsights, getTrafficWindows, getFlows, Session, AnomalyResult, Insight, TrafficWindow, FlowRecord } from '@/lib/api';
import AnomalyTable from '@/components/AnomalyTable';
import InsightsPanel from '@/components/InsightsPanel';

export default function SessionDetailPage() {
    const params = useParams();
    const router = useRouter();
    const sessionId = params.sessionId as string;

    const [session, setSession] = useState<Session | null>(null);
    const [results, setResults] = useState<AnomalyResult[]>([]);
    const [insights, setInsights] = useState<Insight[]>([]);
    const [trafficWindows, setTrafficWindows] = useState<TrafficWindow[]>([]);
    const [flows, setFlows] = useState<FlowRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'overview' | 'results' | 'insights'>('overview');
    const [mode, setMode] = useState<'technical' | 'beginner'>('technical');

    const loadSessionData = useCallback(async () => {
        try {
        const [sessionsData, resultsData, insightsData, trafficWindowsData, flowsData] = await Promise.all([
            getSessions(undefined, 1000),
            getResults(sessionId),
            getInsights(sessionId),
            getTrafficWindows(sessionId),
            getFlows(sessionId, 1000),
        ]);

        const currentSession = sessionsData.find(s => s.session_id === sessionId);
        if (!currentSession) {
            setError('Session not found');
            setLoading(false);
            return;
        }

        setSession(currentSession);
        setResults(resultsData);
        setInsights(insightsData);
        setTrafficWindows(trafficWindowsData);
        setFlows(flowsData);
        setError(null);
        } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load session data');
        } finally {
        setLoading(false);
        }
    }, [sessionId]);

    useEffect(() => {
        loadSessionData();
    }, [loadSessionData]);

    useEffect(() => {
        if (session?.status === 'processing') {
            const interval = setInterval(() => {
                loadSessionData();
            }, 3000);
            return () => clearInterval(interval);
        }
    }, [session?.status, loadSessionData]);

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleString();
    };

    const derived = useMemo(() => {
        const totalFlows = trafficWindows.length > 0
        ? trafficWindows.reduce((sum, window) => sum + (window.flow_count ?? 0), 0)
        : results.length || 0;
        const totalPackets = session?.total_packets ?? null;
        const totalBytes = session?.file_size_bytes ?? null;
        const durationSeconds = session?.duration_seconds ?? null;
        const avgThroughput = durationSeconds && totalBytes && durationSeconds > 0
        ? (totalBytes / durationSeconds / 1024 / 1024)
        : null;
        const activeIps = insights.length > 0
        ? Math.max(
            insights.reduce((max, item) => Math.max(max, item.unique_src_ips ?? 0), 0),
            insights.reduce((max, item) => Math.max(max, item.unique_dst_ips ?? 0), 0),
            )
        : null;
        const anomalyCount = results.length > 0
        ? results.filter((r) => r.is_anomaly).length
        : 0;

        return {
        totalFlows,
        totalPackets,
        totalBytes,
        avgThroughput,
        activeIps,
        anomalyCount,
        };
    }, [session, results, insights, trafficWindows]);

    const packetSeries = useMemo<number[] | null>(() => {
        if (trafficWindows.length === 0) {
            return null;
        }
        return trafficWindows.map((window) => window.packets_per_sec ?? 0);
    }, [trafficWindows]);

    type ProtocolData = {tcp: number, udp: number, icmp: number};
    const protocolSeries = useMemo<ProtocolData[] | null>(() => {
        if (trafficWindows.length === 0) {
            return null;
        }
        return trafficWindows.map(window => ({
            tcp: window.tcp_ratio ?? 0,
            udp: window.udp_ratio ?? 0,
            icmp: window.icmp_ratio ?? 0,
        }));
    }, [trafficWindows]);

    const latestProtocol = protocolSeries ? protocolSeries[protocolSeries.length - 1] : null;
    const protocolTotal = latestProtocol ? latestProtocol.tcp + latestProtocol.udp + latestProtocol.icmp : 0;
    const tcpHeight = latestProtocol && protocolTotal > 0 ? Math.round((latestProtocol.tcp / protocolTotal) * 100) : 0;
    const udpHeight = latestProtocol && protocolTotal > 0 ? Math.round((latestProtocol.udp / protocolTotal) * 100) : 0;
    const icmpHeight = latestProtocol && protocolTotal > 0 ? Math.round((latestProtocol.icmp / protocolTotal) * 100) : 0;

    type TopTalkerData = {ip: string, bytes: number, share: number};
    const topTalkers = useMemo<TopTalkerData[] | null>(() => {
        if (flows.length === 0) return null;
        
        // Aggregate bytes by source IP
        const ipStats: Record<string, number> = {};
        let totalBytes = 0;
        
        flows.forEach(flow => {
            const ip = flow.src_ip;
            ipStats[ip] = (ipStats[ip] || 0) + flow.total_bytes;
            totalBytes += flow.total_bytes;
        });
        
        if (totalBytes === 0) return null;
        
        // Convert to array, sort by bytes descending, take top 10
        const talkers = Object.entries(ipStats)
            .map(([ip, bytes]) => ({
                ip,
                bytes,
                share: (bytes / totalBytes) * 100
            }))
            .sort((a, b) => b.bytes - a.bytes)
            .slice(0, 10);
        
        return talkers.length > 0 ? talkers : null;
    }, [flows]);

    if (loading) {
        return (
        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg px-4 py-3 text-sm text-zinc-400">
            Loading session metrics...
        </div>
        );
    }

    if (error) {
        return (
        <div className="bg-red-950/40 border border-red-900/40 rounded-lg px-4 py-3 text-sm text-red-200">
            {error}
            <button
            onClick={() => router.push('/sessions')}
            className="mt-4 text-red-300 hover:text-red-200 underline"
            >
            Back to Sessions
            </button>
        </div>
        );
    }

    if (!session) {
        return null;
    }

    return (
        <div className="space-y-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
            <h1 className="text-3xl font-bold text-zinc-100">Session Overview</h1>
            <p className="text-sm text-zinc-400 mt-1">
                {session.filename} · {session.session_id}
            </p>
            <p className="text-xs text-zinc-500 mt-1">
                Uploaded on {formatDate(session.created_at)}
            </p>
            </div>
            <div className="flex items-center gap-2">
            <button
                onClick={() => setMode(mode === 'technical' ? 'beginner' : 'technical')}
                className="px-3 py-2 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded border border-zinc-700"
            >
                {mode === 'technical' ? 'Beginner Explanations' : 'Technical Explanations'}
            </button>
            <button
                onClick={() => router.push('/sessions')}
                className="px-3 py-2 text-xs text-cyan-300 border border-cyan-700/50 rounded hover:border-cyan-400"
            >
                Back to Sessions
            </button>
            </div>
        </div>

        {/* Processing Message */}
        {session.status === 'processing' && (
            <div className="bg-cyan-950/30 border border-cyan-900/40 rounded-lg px-4 py-3 text-sm text-cyan-200">
            Analysis in progress... This page will auto-update when complete.
            </div>
        )}

        {/* Error Message */}
        {session.error_message && (
            <div className="bg-red-950/40 border border-red-900/40 rounded-lg px-4 py-3 text-sm text-red-200">
            {session.error_message}
            </div>
        )}

        {/* Tabs */}
        {session.status === 'completed' && (
            <>
            <div className="border-b border-zinc-800">
                <nav className="flex space-x-8">
                {['overview', 'results', 'insights'].map((tab) => (
                    <button
                    key={tab}
                    onClick={() => setActiveTab(tab as any)}
                    className={`py-4 px-1 border-b-2 font-medium text-sm capitalize transition-colors ${
                        activeTab === tab
                        ? 'border-cyan-400 text-cyan-300'
                        : 'border-transparent text-zinc-500 hover:text-zinc-100'
                    }`}
                    >
                    {tab}
                    </button>
                ))}
                </nav>
            </div>

            {/* Tab Content */}
            <div>
                {activeTab === 'overview' && (
                <div className="space-y-6">
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                    {[
                        { label: 'Total Flows', value: derived.totalFlows > 0 ? derived.totalFlows.toLocaleString() : 'No data', tip: 'Number of flow windows extracted from the capture.' },
                        { label: 'Total Packets', value: derived.totalPackets !== null ? derived.totalPackets.toLocaleString() : 'No data', tip: 'Sum of all packets observed in the capture.' },
                        { label: 'Data Transferred', value: derived.totalBytes !== null ? `${(derived.totalBytes / 1024 / 1024 / 1024).toFixed(1)} GB` : 'No data', tip: 'Aggregate bytes sent and received across all flows.' },
                        { label: 'Avg Throughput', value: derived.avgThroughput !== null ? `${derived.avgThroughput.toFixed(1)} MB/s` : 'No data', tip: 'Average data rate over the capture duration.' },
                        { label: 'Active IPs', value: derived.activeIps !== null ? derived.activeIps.toLocaleString() : 'No data', tip: 'Unique source and destination IP addresses.' },
                        { label: 'Detected Anomalies', value: derived.anomalyCount.toLocaleString(), tip: 'ML-flagged time windows with unusual behavior.' },
                    ].map((card) => (
                        <div
                        key={card.label}
                        className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-4"
                        title={mode === 'beginner' ? card.tip : `${card.tip} (timestamp indexed)`}
                        >
                        <div className="text-xs text-zinc-500 uppercase tracking-wide">{card.label}</div>
                        <div className="text-2xl font-semibold text-zinc-100 mt-1">{card.value}</div>
                        </div>
                    ))}
                    </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2 bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
                        <div className="flex items-center justify-between">
                        <h3 className="text-lg font-semibold text-zinc-100">Packets per Second</h3>
                        <span className="text-xs text-zinc-500">Timestamp-indexed</span>
                        </div>
                        <p className="text-xs text-zinc-500 mt-1">
                        {mode === 'beginner'
                            ? 'Spikes indicate bursts of activity or scans.'
                            : 'Per-second packet rate derived from sliding time windows.'}
                        </p>
                        {packetSeries ? (
                        <div className="mt-4 rounded-lg bg-gradient-to-b from-cyan-500/10 to-transparent border border-cyan-700/30 p-5">
                        <div className="relative h-56">
                            <div className="absolute left-0 top-0 bottom-8 w-12 flex flex-col justify-between text-[10px] text-zinc-500">
                            {(() => {
                                const maxPackets = Math.max(...packetSeries, 1);
                                return [1, 0.75, 0.5, 0.25, 0].map((pct) => (
                                  <span key={pct}>{Math.round(maxPackets * pct).toLocaleString()}</span>
                                ));
                            })()}
                            </div>
                            <div className="absolute -left-2 top-1/2 -translate-y-1/2 -rotate-90 text-[10px] text-zinc-500">
                            Packets/sec
                            </div>
                            <div className="ml-14 h-full pb-8 border-l border-b border-zinc-700 relative">
                            <div className="absolute inset-0 flex items-end gap-1 px-3 pb-4">
                                {packetSeries.map((value, i) => (
                                <div
                                    key={i}
                                    className="w-2 bg-cyan-400/70 rounded-t"
                                    style={{ height: `${Math.min(100, (value / Math.max(...packetSeries, 1)) * 100)}%` }}
                                ></div>
                                ))}
                            </div>
                            </div>
                            <div className="ml-14 mt-3 grid grid-cols-5 text-[9px] text-zinc-500 text-center px-2">
                            <span>00:00</span>
                            <span>06:00</span>
                            <span>12:00</span>
                            <span>18:00</span>
                            <span>24:00</span>
                            </div>
                            <div className="ml-14 text-center text-[10px] text-zinc-500">Time</div>
                        </div>
                        </div>
                        ) : (
                        <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
                            <p className="text-zinc-500 text-sm">No packet rate data available</p>
                            <p className="text-zinc-600 text-xs mt-1">Traffic window metrics required</p>
                        </div>
                        )}
                    </div>

                    <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
                        <h3 className="text-lg font-semibold text-zinc-100">Network Health</h3>
                        <p className="text-xs text-zinc-500 mt-1">Overall score based on detected anomalies</p>
                        <div className="mt-6 flex items-center justify-center">
                        {(() => {
                            const anomalyRate = results.length > 0 ? (derived.anomalyCount / results.length) : 0;
                            const healthStatus = anomalyRate === 0 ? 'Optimal' :
                                anomalyRate < 0.05 ? 'Normal' :
                                anomalyRate < 0.3 ? 'Degraded' : 'Critical';
                            const borderColor = healthStatus === 'Optimal' || healthStatus === 'Normal' ? 'border-emerald-500/30' :
                                healthStatus === 'Degraded' ? 'border-amber-500/30' : 'border-red-500/30';
                            const textColor = healthStatus === 'Optimal' || healthStatus === 'Normal' ? 'text-emerald-400' :
                                healthStatus === 'Degraded' ? 'text-amber-400' : 'text-red-400';
                            return (
                                <div className={`w-48 h-48 rounded-full border-8 ${borderColor} flex items-center justify-center`}>
                                    <div className="text-center">
                                    <div className={`text-xl font-bold ${textColor}`}>{healthStatus}</div>
                                    {/* <div className="text-xs text-zinc-500">{(anomalyRate * 100).toFixed(1)}% anomalies</div> */}
                                    </div>
                                </div>
                            );
                        })()}
                        </div>
                        <div className="mt-6 text-xs text-zinc-400">
                        {mode === 'beginner'
                            ? `${derived.anomalyCount} anomalies detected out of ${results.length} time windows analyzed.`
                            : `Anomaly rate: ${results.length > 0 ? ((derived.anomalyCount / results.length) * 100).toFixed(2) : 0}%`}
                        </div>
                    </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
                        <h3 className="text-lg font-semibold text-zinc-100">Protocol Distribution</h3>
                        <p className="text-xs text-zinc-500 mt-1">Stacked area chart over time (TCP/UDP/ICMP)</p>
                        {protocolSeries ? (
                        <div className="mt-4 rounded-lg bg-gradient-to-b from-teal-500/10 to-transparent border border-teal-700/30 p-5">
                        <div className="relative h-56">
                            <div className="absolute left-0 top-0 bottom-8 w-12 flex flex-col justify-between text-[10px] text-zinc-500">
                            <span>100%</span>
                            <span>75%</span>
                            <span>50%</span>
                            <span>25%</span>
                            <span>0%</span>
                            </div>
                            <div className="absolute -left-2 top-1/2 -translate-y-1/2 -rotate-90 text-[10px] text-zinc-500">
                            Share
                            </div>
                            <div className="ml-14 h-full pb-8 border-l border-b border-zinc-700 relative overflow-hidden">
                            <div className="absolute inset-0 flex items-end">
                                <div className="w-full bg-teal-500/40" style={{ height: `${udpHeight}%` }}></div>
                                <div className="w-full bg-cyan-500/40 -ml-full" style={{ height: `${tcpHeight}%` }}></div>
                                <div className="w-full bg-amber-500/40 -ml-full" style={{ height: `${icmpHeight}%` }}></div>
                            </div>
                            </div>
                            <div className="ml-14 mt-3 grid grid-cols-5 text-[9px] text-zinc-500 text-center px-2">
                            <span>00:00</span>
                            <span>06:00</span>
                            <span>12:00</span>
                            <span>18:00</span>
                            <span>24:00</span>
                            </div>
                            <div className="ml-14 text-center text-[10px] text-zinc-500">Time</div>
                        </div>
                        </div>
                        ) : (
                        <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
                            <p className="text-zinc-500 text-sm">No protocol distribution data available</p>
                            <p className="text-zinc-600 text-xs mt-1">Traffic window metrics required</p>
                        </div>
                        )}
                        <div className="mt-3 flex gap-4 text-xs text-zinc-400">
                        <span className="flex items-center gap-1"><span className="w-2 h-2 bg-cyan-400 rounded"></span>TCP</span>
                        <span className="flex items-center gap-1"><span className="w-2 h-2 bg-teal-400 rounded"></span>UDP</span>
                        <span className="flex items-center gap-1"><span className="w-2 h-2 bg-amber-400 rounded"></span>ICMP</span>
                        </div>
                    </div>

                    <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
                        <h3 className="text-lg font-semibold text-zinc-100">Top 10 Talkers</h3>
                        <p className="text-xs text-zinc-500 mt-1">IPs ranked by total bytes transferred</p>
                        {topTalkers ? (
                        <div className="mt-4 space-y-3">
                        {topTalkers.map((talker) => (
                            <div key={talker.ip} className="flex items-center gap-3">
                            <span className="text-xs text-zinc-500 w-16">{talker.ip}</span>
                            <div className="flex-1 h-2 bg-zinc-800 rounded-full ml-4.5">
                                <div className="h-2 bg-amber-400 rounded-full" style={{ width: `${talker.share}%` }}></div>
                            </div>
                            <span className="text-xs text-zinc-400">{talker.bytes} GB</span>
                            </div>
                        ))}
                        </div>
                        ) : (
                        <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
                            <p className="text-zinc-500 text-sm">No IP traffic data available</p>
                            <p className="text-zinc-600 text-xs mt-1">Detailed flow metrics required</p>
                        </div>
                        )}
                        <div className="mt-4 text-xs text-zinc-500">
                        {mode === 'beginner'
                            ? 'Large talkers can be backups, streaming, or potential data exfiltration.'
                            : 'Top talkers by aggregate byte volume for forensic triage.'}
                        </div>
                    </div>
                    </div>
                </div>
                )}

                {activeTab === 'results' && (
                <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg overflow-hidden">
                    <AnomalyTable results={results} />
                </div>
                )}

                {activeTab === 'insights' && (
                <div className="space-y-6">
                    <InsightsPanel insights={insights} />
                </div>
                )}
            </div>
            </>
        )}
        </div>
    );
    }
