'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getSessions, getResults, getInsights, Session, AnomalyResult, Insight } from '@/lib/api';
import StatCard from '@/components/StatCard';
import AnomalyTable from '@/components/AnomalyTable';
import InsightsPanel from '@/components/InsightsPanel';
import DashboardCharts from '@/components/DashboardCharts';

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

    const formatBytes = (bytes?: number) => {
        if (!bytes) return 'N/A';
        const mb = bytes / 1024 / 1024;
        return `${mb.toFixed(2)} MB`;
    };

    const anomalyCount = results.filter(r => r.is_anomaly).length;
    const anomalyPercentage = results.length > 0 ? ((anomalyCount / results.length) * 100).toFixed(1) : '0';

    if (loading) {
        return (
        <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="text-zinc-600 dark:text-zinc-400 mt-4">Loading session data...</p>
        </div>
        );
    }

    if (error) {
        return (
        <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
            <p className="text-red-800 dark:text-red-200">{error}</p>
            <button
            onClick={() => router.push('/sessions')}
            className="mt-4 text-red-600 dark:text-red-400 hover:underline"
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
        {/* Header */}
        <div>
            <button
            onClick={() => router.push('/sessions')}
            className="text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 mb-4 flex items-center space-x-1"
            >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span>Back to Sessions</span>
            </button>
            <div className="flex items-start justify-between">
            <div>
                <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-100">
                {session.filename}
                </h1>
                <p className="text-sm text-zinc-500 font-mono mt-1">{session.session_id}</p>
                <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-2">
                Uploaded on {formatDate(session.created_at)}
                </p>
            </div>
            <div className="flex items-center space-x-3">
                <span className={`px-4 py-2 rounded-lg text-sm font-medium ${
                session.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-950/20 dark:text-green-400' :
                session.status === 'processing' ? 'bg-blue-100 text-blue-800 dark:bg-blue-950/20 dark:text-blue-400' :
                'bg-red-100 text-red-800 dark:bg-red-950/20 dark:text-red-400'
                }`}>
                {session.status}
                </span>
            </div>
            </div>
        </div>

        {/* Processing Message */}
        {session.status === 'processing' && (
            <div className="bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-center space-x-3">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                <p className="text-blue-800 dark:text-blue-200">
                Analysis in progress... This page will auto-update when complete.
                </p>
            </div>
            </div>
        )}

        {/* Error Message */}
        {session.error_message && (
            <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-red-800 dark:text-red-200">{session.error_message}</p>
            </div>
        )}

        {/* Stats Grid */}
        {session.status === 'completed' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
                title="Total Packets"
                value={session.total_packets?.toLocaleString() || 'N/A'}
            />
            <StatCard
                title="File Size"
                value={formatBytes(session.file_size_bytes)}
            />
            <StatCard
                title="Anomalies Detected"
                value={anomalyCount}
                subtitle={`${anomalyPercentage}% of windows`}
                trend={parseFloat(anomalyPercentage) > 10 ? 'up' : 'neutral'}
                trendValue={`${anomalyPercentage}%`}
            />
            <StatCard
                title="Analysis Windows"
                value={results.length}
                subtitle="Time windows analyzed"
            />
            </div>
        )}

        {/* Tabs */}
        {session.status === 'completed' && (
            <>
            <div className="border-b border-zinc-200 dark:border-zinc-800">
                <nav className="flex space-x-8">
                {['overview', 'results', 'insights'].map((tab) => (
                    <button
                    key={tab}
                    onClick={() => setActiveTab(tab as any)}
                    className={`py-4 px-1 border-b-2 font-medium text-sm capitalize transition-colors ${
                        activeTab === tab
                        ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                        : 'border-transparent text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100'
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
                    <DashboardCharts results={results} totalPackets={session.total_packets} />
                    <InsightsPanel insights={insights} />
                </div>
                )}

                {activeTab === 'results' && (
                <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg overflow-hidden">
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
