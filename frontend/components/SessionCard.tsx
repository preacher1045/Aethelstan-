'use client';

import { Session } from '@/lib/api';
import Link from 'next/link';

interface SessionCardProps {
    session: Session;
}

export default function SessionCard({ session }: SessionCardProps) {
    const getStatusColor = (status: string) => {
        switch (status) {
        case 'completed':
            return 'bg-green-100 text-green-800 dark:bg-green-950/20 dark:text-green-400';
        case 'processing':
            return 'bg-blue-100 text-blue-800 dark:bg-blue-950/20 dark:text-blue-400';
        case 'failed':
            return 'bg-red-100 text-red-800 dark:bg-red-950/20 dark:text-red-400';
        default:
            return 'bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-400';
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

    const formatDuration = (seconds?: number) => {
        if (!seconds) return 'N/A';
        if (seconds < 60) return `${seconds.toFixed(1)}s`;
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes}m ${secs}s`;
    };

    return (
        <Link href={`/sessions/${session.session_id}`}>
        <div className="block p-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg hover:shadow-lg transition-shadow cursor-pointer">
            <div className="flex items-start justify-between mb-3">
            <div className="flex-1">
                <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-1">
                {session.filename}
                </h3>
                <p className="text-xs text-zinc-500 font-mono">{session.session_id}</p>
            </div>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(session.status)}`}>
                {session.status}
            </span>
            </div>

            <div className="grid grid-cols-2 gap-4 mt-4">
            <div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">File Size</p>
                <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {formatBytes(session.file_size_bytes)}
                </p>
            </div>
            <div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">Total Packets</p>
                <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {session.total_packets?.toLocaleString() || 'N/A'}
                </p>
            </div>
            <div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">Duration</p>
                <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {formatDuration(session.duration_seconds)}
                </p>
            </div>
            <div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">Upload Date</p>
                <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {formatDate(session.created_at)}
                </p>
            </div>
            </div>

            {session.error_message && (
            <div className="mt-4 p-3 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded">
                <p className="text-xs text-red-800 dark:text-red-200">{session.error_message}</p>
            </div>
            )}
        </div>
        </Link>
    );
    }
