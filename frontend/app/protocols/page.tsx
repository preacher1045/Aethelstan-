'use client';

import { useMemo } from 'react';
import { useLatestSessionData } from '@/lib/useLatestSessionData';

export default function ProtocolFlowPage() {
  const { session, results, loading, error } = useLatestSessionData();

  const topFlows = useMemo(() => {
    if (results.length === 0) {
      return Array.from({ length: 5 }).map((_, i) => ({
        src: `10.0.${i}.24`,
        dst: `172.16.${i}.8`,
        protocol: 'TCP',
        duration: `${12 + i}s`,
        packets: 800 + i * 120,
        bytes: `${(3.2 + i * 0.4).toFixed(1)} MB`,
      }));
    }

    return results.slice(0, 5).map((item, i) => ({
      src: `10.0.${i}.24`,
      dst: `172.16.${i}.8`,
      protocol: item.anomaly_type ?? 'TCP',
      duration: `${10 + i}s`,
      packets: 600 + i * 140,
      bytes: `${(2.1 + i * 0.5).toFixed(1)} MB`,
    }));
  }, [results]);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-zinc-100">Protocol & Flow Insights</h1>
        <p className="text-sm text-zinc-400 mt-1">Deep dive into flow-level behavior and protocol health</p>
      </div>

      {error && (
        <div className="bg-red-950/40 border border-red-900/40 rounded-lg px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {loading && (
        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg px-4 py-3 text-sm text-zinc-400">
          Loading protocol insights from latest session...
        </div>
      )}

      <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-zinc-100">Top Flows</h3>
        <p className="text-xs text-zinc-500 mt-1">Src IP, Dst IP, protocol, duration, packets, bytes</p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-zinc-500 uppercase border-b border-zinc-800">
              <tr>
                <th className="py-2">Src IP</th>
                <th className="py-2">Dst IP</th>
                <th className="py-2">Protocol</th>
                <th className="py-2">Duration</th>
                <th className="py-2">Packets</th>
                <th className="py-2">Bytes</th>
              </tr>
            </thead>
            <tbody className="text-zinc-300">
              {topFlows.map((flow) => (
                <tr key={`${flow.src}-${flow.dst}`} className="border-b border-zinc-800">
                  <td className="py-2">{flow.src}</td>
                  <td className="py-2">{flow.dst}</td>
                  <td className="py-2">{flow.protocol}</td>
                  <td className="py-2">{flow.duration}</td>
                  <td className="py-2">{flow.packets}</td>
                  <td className="py-2">{flow.bytes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">TCP Health Metrics</h3>
          <div className="mt-4 space-y-3">
            {[
              { label: 'SYN / ACK Ratio', value: '1.08', note: 'Healthy connection setup' },
              { label: 'RST Rate', value: '2.4%', note: 'Moderate resets observed' },
              { label: 'Retransmission Rate', value: '0.9%', note: 'Low packet loss' },
            ].map((metric) => (
              <div key={metric.label} className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
                <div className="text-xs text-zinc-500 uppercase">{metric.label}</div>
                <div className="text-lg text-cyan-300 font-semibold mt-1">{metric.value}</div>
                <div className="text-xs text-zinc-400 mt-1">{metric.note}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">Port Usage Distribution</h3>
          <p className="text-xs text-zinc-500 mt-1">Top services by port activity</p>
          <div className="mt-4 space-y-3">
            {['443 (HTTPS)', '80 (HTTP)', '53 (DNS)', '22 (SSH)', '3389 (RDP)'].map((port, i) => (
              <div key={port} className="flex items-center gap-3">
                <span className="text-xs text-zinc-500 w-20">{port}</span>
                <div className="flex-1 h-2 bg-zinc-800 rounded-full">
                  <div className="h-2 bg-teal-400 rounded-full" style={{ width: `${90 - i * 12}%` }}></div>
                </div>
                <span className="text-xs text-zinc-400">{32 - i * 5}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-zinc-100">Suspicious Patterns</h3>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
            <div className="text-sm text-amber-300 font-medium">High SYN, Low ACK</div>
            <p className="text-xs text-zinc-400 mt-1">Potential SYN flood or scanning behavior detected.</p>
          </div>
          <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
            <div className="text-sm text-amber-300 font-medium">High Reset Rates</div>
            <p className="text-xs text-zinc-400 mt-1">Connections terminated abruptly, indicating possible disruptions.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
