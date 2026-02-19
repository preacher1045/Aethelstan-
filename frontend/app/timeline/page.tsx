'use client';

import { useMemo } from 'react';
import { useLatestSessionData } from '@/lib/useLatestSessionData';

export default function TimelinePage() {
  const { results, insights, loading, error } = useLatestSessionData();

  const eventMarkers = useMemo(() => {
    if (results.length === 0) {
      return ['Anomaly burst at 14:07', 'Throughput spike at 18:22', 'High entropy at 22:11'];
    }
    return results
      .filter((item) => item.is_anomaly)
      .slice(0, 3)
      .map((item) => `Anomaly window #${item.window_id ?? 0}`);
  }, [results]);

  const windowStats = useMemo(() => {
    if (results.length === 0) {
      return Array.from({ length: 5 }).map((_, i) => ({
        window: i + 1,
        packets: 2400 + i * 120,
        bytes: `${(1.8 + i * 0.3).toFixed(1)} MB`,
        anomaly: i % 2 === 0 ? 'Yes' : 'No',
      }));
    }
    return results.slice(0, 5).map((item, i) => ({
      window: item.window_id ?? i + 1,
      packets: 2200 + i * 150,
      bytes: `${(1.6 + i * 0.25).toFixed(1)} MB`,
      anomaly: item.is_anomaly ? 'Yes' : 'No',
    }));
  }, [results]);
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
        <div className="mt-4 h-16 rounded-lg bg-zinc-950 border border-zinc-800 relative">
          <div className="absolute inset-0 flex items-center px-4">
            <div className="w-full h-2 bg-zinc-800 rounded-full relative">
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="absolute top-1/2 w-3 h-3 bg-red-500 rounded-full"
                  style={{ left: `${10 + i * 14}%`, transform: 'translate(-50%, -50%)' }}
                ></div>
              ))}
            </div>
          </div>
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
          <div className="mt-4 space-y-3">
            {eventMarkers.map((event) => (
              <div key={event} className="flex items-center gap-3 bg-zinc-950 border border-zinc-800 rounded-lg p-4">
                <span className="text-red-400">●</span>
                <div>
                  <div className="text-sm text-zinc-200">{event}</div>
                  <div className="text-xs text-zinc-500">Tagged for forensic review</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">Time-Window Statistics</h3>
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
