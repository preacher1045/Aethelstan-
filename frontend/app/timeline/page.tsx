'use client';

import { useMemo } from 'react';
import { useLatestSessionData } from '@/lib/useLatestSessionData';

export default function TimelinePage() {
  const { results, insights, trafficWindows, loading, error } = useLatestSessionData();

  const eventMarkers = useMemo(() => {
    if (insights.length === 0) {
      return [];
    }
    return insights
      .filter((i) => i.insight_type === 'alert')
      .map((i) => ({
        timestamp: new Date(i.created_at).toLocaleTimeString(),
        event_type: i.alert_type ?? 'Unknown',
        description: i.summary,
        severity: i.severity ?? 'medium',
      }));
  }, [insights]);

  const windowStats = useMemo(() => {
    if (trafficWindows.length === 0) {
      return [];
    }
    return trafficWindows.slice(0, 10).map((window) => ({
      window: window.window_id,
      packets: window.packet_count?.toLocaleString() ?? 'N/A',
      bytes: window.total_bytes ? `${(window.total_bytes / 1024 / 1024).toFixed(2)} MB` : 'N/A',
      anomaly: results.find(r => r.window_id === window.window_id)?.is_anomaly ? 'Yes' : 'No',
    }));
  }, [trafficWindows, results]);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-zinc-100">Timeline & Forensics</h1>
        <p className="text-sm text-zinc-400 mt-1">Investigate when and how events occurred</p>
      </div>

      {error && (
        <div className="bg-red-950/40 border border-red-900/40 rounded-lg px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {loading && (
        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg px-4 py-3 text-sm text-zinc-400">
          Loading timeline data from latest session...
        </div>
      )}

      <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-zinc-100">Interactive Timeline Scrubber</h3>
        <p className="text-xs text-zinc-500 mt-1">Hover over spikes to inspect anomalies</p>
        <div className="mt-4 h-16 rounded-lg border border-zinc-700/50 flex items-center justify-center">
          <p className="text-zinc-500 text-sm">No timeline data available</p>
        </div>
        <div className="mt-3 flex justify-between text-xs text-zinc-500">
          <span>00:00</span>
          <span>06:00</span>
          <span>12:00</span>
          <span>18:00</span>
          <span>24:00</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">Event Markers</h3>
          {eventMarkers.length > 0 ? (
          <div className="mt-4 space-y-3">
            {eventMarkers.map((event, idx) => {
              const severityColor = event.severity === 'high' ? 'text-red-400' : 
                                   event.severity === 'medium' ? 'text-amber-400' : 'text-yellow-400';
              return (
                <div key={`${event.timestamp}-${idx}`} className="flex items-start gap-3 bg-zinc-950 border border-zinc-800 rounded-lg p-4">
                  <span className={severityColor}>●</span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <div className="text-sm text-zinc-200 font-medium">{event.event_type}</div>
                      <div className="text-xs text-zinc-500">{event.timestamp}</div>
                    </div>
                    <div className="text-xs text-zinc-400 mt-1">{event.description}</div>
                    <div className="text-xs text-zinc-600 mt-1">Severity: {event.severity}</div>
                  </div>
                </div>
              );
            })}
          </div>
          ) : (
          <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
            <p className="text-zinc-500 text-sm">No event markers available</p>
            <p className="text-zinc-600 text-xs mt-1">Anomaly detection required</p>
          </div>
          )}
        </div>

        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">Time-Window Statistics</h3>
          {windowStats.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-zinc-500 uppercase border-b border-zinc-800">
                <tr>
                  <th className="py-2">Window</th>
                  <th className="py-2">Packets</th>
                  <th className="py-2">Bytes</th>
                  <th className="py-2">Anomaly</th>
                </tr>
              </thead>
              <tbody className="text-zinc-300">
                {windowStats.map((row) => (
                  <tr key={row.window} className="border-b border-zinc-800">
                    <td className="py-2">{row.window}</td>
                    <td className="py-2">{row.packets}</td>
                    <td className="py-2">{row.bytes}</td>
                    <td className="py-2 text-amber-300">{row.anomaly}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          ) : (
          <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
            <p className="text-zinc-500 text-sm">No window statistics available</p>
            <p className="text-zinc-600 text-xs mt-1">Traffic analysis required</p>
          </div>
          )}
        </div>
      </div>

      <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-zinc-100">Filter Controls</h3>
        <p className="text-xs text-zinc-500 mt-1">Filter by time range, IP, protocol, and severity</p>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-4">
          {['Time Range', 'IP Address', 'Protocol', 'Severity'].map((label) => (
            <div key={label} className="bg-zinc-950 border border-zinc-800 rounded-lg p-3">
              <div className="text-xs text-zinc-500 uppercase">{label}</div>
              <div className="text-sm text-zinc-300 mt-1">Select...</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
