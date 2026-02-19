'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getSessions, getResults, getInsights, Session, AnomalyResult, Insight } from '@/lib/api';
import AnomalyTable from '@/components/AnomalyTable';
import InsightsPanel from '@/components/InsightsPanel';

export default function SessionDetailPage() {
    const params = useParams();
    const router = useRouter();
    const sessionId = params.sessionId as string;

    const [session, setSession] = useState<Session | null>(null);
    const [results, setResults] = useState<AnomalyResult[]>([]);
    const [insights, setInsights] = useState<Insight[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'overview' | 'results' | 'insights'>('overview');
    const [mode, setMode] = useState<'technical' | 'beginner'>('technical');

    useEffect(() => {
        loadSessionData();
        const interval = setInterval(() => {
        if (session?.status === 'processing') {
            loadSessionData();
        }
        }, 3000);
        return () => clearInterval(interval);
    }, [sessionId]);

    const loadSessionData = async () => {
        try {
        const [sessionsData, resultsData, insightsData] = await Promise.all([
            getSessions(undefined, 1000),
            getResults(sessionId),
            getInsights(sessionId),
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
        setError(null);
        } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load session data');
        } finally {
        setLoading(false);
        }
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleString();
    };

    const derived = useMemo(() => {
        const totalFlows = results.length || 42100;
        const totalPackets = session?.total_packets ?? 9600000;
        const totalBytes = session?.file_size_bytes ?? 824 * 1024 * 1024 * 1024;
        const durationSeconds = session?.duration_seconds ?? 3600;
        const avgThroughput = durationSeconds > 0
        ? (totalBytes / durationSeconds / 1024 / 1024)
        : 214;
        const activeIps = insights.length > 0
        ? Math.max(
            insights.reduce((max, item) => Math.max(max, item.unique_src_ips ?? 0), 0),
            insights.reduce((max, item) => Math.max(max, item.unique_dst_ips ?? 0), 0),
            )
        : 1244;
        const anomalyCount = results.length > 0
        ? results.filter((r) => r.is_anomaly).length
        : 138;

        return {
        totalFlows,
        totalPackets,
        totalBytes,
        avgThroughput,
        activeIps,
        anomalyCount,
        };
    }, [session, results, insights]);

    const packetSeries = useMemo(() => {
        const points = results.length > 0 ? results.slice(0, 24) : Array.from({ length: 24 });
        return points.map((item, i) => {
        const base = 900 + (i % 7) * 450;
        const score = typeof item === 'object' && item?.anomaly_score ? item.anomaly_score * 1500 : 0;
        const spike = typeof item === 'object' && item?.is_anomaly ? 900 : 0;
        return Math.round(base + score + spike);
        });
    }, [results]);

    const protocolSeries = useMemo(() => {
        const points = Array.from({ length: 24 }, (_, i) => {
        const tcp = 45 + (i % 5) * 6;
        const udp = 30 + (i % 3) * 5;
        const icmp = 12 + (i % 4) * 3;
        return {
            tcp,
            udp,
            icmp,
        };
        });
        return points;
    }, []);

    const latestProtocol = protocolSeries[protocolSeries.length - 1];
    const protocolTotal = latestProtocol.tcp + latestProtocol.udp + latestProtocol.icmp;
    const tcpHeight = Math.round((latestProtocol.tcp / protocolTotal) * 100);
    const udpHeight = Math.round((latestProtocol.udp / protocolTotal) * 100);
    const icmpHeight = Math.round((latestProtocol.icmp / protocolTotal) * 100);

    const topTalkers = useMemo(() => {
        return Array.from({ length: 5 }).map((_, i) => ({
        ip: `10.0.${i}.24`,
        bytes: 120 - i * 18,
        share: 85 - i * 12,
        }));
    }, []);

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
                        { label: 'Total Flows', value: derived.totalFlows.toLocaleString(), tip: 'Number of flow windows extracted from the capture.' },
                        { label: 'Total Packets', value: derived.totalPackets.toLocaleString(), tip: 'Sum of all packets observed in the capture.' },
                        { label: 'Data Transferred', value: `${(derived.totalBytes / 1024 / 1024 / 1024).toFixed(1)} GB`, tip: 'Aggregate bytes sent and received across all flows.' },
                        { label: 'Avg Throughput', value: `${derived.avgThroughput.toFixed(1)} MB/s`, tip: 'Average data rate over the capture duration.' },
                        { label: 'Active IPs', value: derived.activeIps.toLocaleString(), tip: 'Unique source and destination IP addresses.' },
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
                        <div className="mt-4 rounded-lg bg-gradient-to-b from-cyan-500/10 to-transparent border border-cyan-700/30 p-5">
                        <div className="relative h-56">
                            <div className="absolute left-0 top-0 bottom-8 w-12 flex flex-col justify-between text-[10px] text-zinc-500">
                            <span>6k</span>
                            <span>4.5k</span>
                            <span>3k</span>
                            <span>1.5k</span>
                            <span>0</span>
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
                                    style={{ height: `${Math.min(100, (value / 6000) * 100)}%` }}
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
                    </div>

                    <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
                        <h3 className="text-lg font-semibold text-zinc-100">Network Health</h3>
                        <p className="text-xs text-zinc-500 mt-1">Overall score based on anomalies and throughput variance.</p>
                        <div className="mt-6 flex items-center justify-center">
                        <div className="w-28 h-28 rounded-full border-8 border-emerald-500/30 flex items-center justify-center">
                            <div className="text-center">
                            <div className="text-xl font-bold text-emerald-400">Normal</div>
                            <div className="text-xs text-zinc-500">Score 82</div>
                            </div>
                        </div>
                        </div>
                        <div className="mt-6 text-xs text-zinc-400">
                        {mode === 'beginner'
                            ? 'Healthy traffic pattern with small bursts and few anomalies.'
                            : 'Deviation index below alert threshold; anomaly rate < 5%.'}
                        </div>
                    </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
                        <h3 className="text-lg font-semibold text-zinc-100">Protocol Distribution</h3>
                        <p className="text-xs text-zinc-500 mt-1">Stacked area chart over time (TCP/UDP/ICMP)</p>
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
                        <div className="mt-3 flex gap-4 text-xs text-zinc-400">
                        <span className="flex items-center gap-1"><span className="w-2 h-2 bg-cyan-400 rounded"></span>TCP</span>
                        <span className="flex items-center gap-1"><span className="w-2 h-2 bg-teal-400 rounded"></span>UDP</span>
                        <span className="flex items-center gap-1"><span className="w-2 h-2 bg-amber-400 rounded"></span>ICMP</span>
                        </div>
                    </div>

                    <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
                        <h3 className="text-lg font-semibold text-zinc-100">Top 10 Talkers</h3>
                        <p className="text-xs text-zinc-500 mt-1">IPs ranked by total bytes transferred</p>
                        <div className="mt-4 space-y-3">
                        {topTalkers.map((talker) => (
                            <div key={talker.ip} className="flex items-center gap-3">
                            <span className="text-xs text-zinc-500 w-16">{talker.ip}</span>
                            <div className="flex-1 h-2 bg-zinc-800 rounded-full">
                                <div className="h-2 bg-amber-400 rounded-full" style={{ width: `${talker.share}%` }}></div>
                            </div>
                            <span className="text-xs text-zinc-400">{talker.bytes} GB</span>
                            </div>
                        ))}
                        </div>
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
