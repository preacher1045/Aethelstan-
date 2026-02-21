'use client';

import { useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useSessionData } from '@/lib/useSessionData';
import Pagination from '@/components/Pagination';

interface FlowData {
  id: number;
  src: string;
  dst: string;
  protocol: string;
  duration: string;
  packets: number;
  bytes: number;
}

interface PortUsageData {
  port: number;
  service: string;
  protocol: string;
  percentage: number;
  count: number;
}

interface SuspiciousPattern {
  title: string;
  detail: string;
}

export default function ProtocolFlowPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('sessionId');
  const { session, results, trafficWindows, flows, portStats, loading, error } = useSessionData(sessionId);
  const [flowsPage, setFlowsPage] = useState(1);
  const [portsPage, setPortsPage] = useState(1);
  const flowsPerPage = 4;
  const portsPerPage = 4;

  const topFlows = useMemo<FlowData[]>(() => {
    if (flows.length === 0) {
      return [];
    }

    return flows.map((flow) => {
      const duration = flow.duration_seconds !== undefined
        ? `${flow.duration_seconds.toFixed(2)}s`
        : 'N/A';
      return {
        id: flow.id,
        src: flow.src_ip,
        dst: flow.dst_ip,
        protocol: flow.protocol,
        duration,
        packets: flow.packet_count,
        bytes: flow.total_bytes,
      };
    });
  }, [flows]);

  const paginatedFlows = useMemo(() => {
    const start = (flowsPage - 1) * flowsPerPage;
    const end = start + flowsPerPage;
    return topFlows.slice(start, end);
  }, [topFlows, flowsPage, flowsPerPage]);

  const portUsage = useMemo<PortUsageData[]>(() => {
    if (portStats.length === 0) {
      return [];
    }

    const aggregated = new Map<string, { port: number; protocol: string; service: string; count: number }>();

    portStats.forEach((stat) => {
      const key = `${stat.port}-${stat.protocol}`;
      const existing = aggregated.get(key);
      if (existing) {
        existing.count += stat.packet_count;
      } else {
        aggregated.set(key, {
          port: stat.port,
          protocol: stat.protocol,
          service: stat.service_name || 'Unknown',
          count: stat.packet_count,
        });
      }
    });

    const aggregatedList = Array.from(aggregated.values()).sort((a, b) => b.count - a.count);
    const totalPackets = aggregatedList.reduce((sum, stat) => sum + stat.count, 0) || 1;
    return aggregatedList.map((stat) => ({
      port: stat.port,
      service: stat.service,
      protocol: stat.protocol,
      percentage: (stat.count / totalPackets) * 100,
      count: stat.count,
    }));
  }, [portStats]);

  const paginatedPorts = useMemo(() => {
    const start = (portsPage - 1) * portsPerPage;
    const end = start + portsPerPage;
    return portUsage.slice(start, end);
  }, [portUsage, portsPage, portsPerPage]);

  const tcpHealthMetrics = useMemo(() => {
    if (trafficWindows.length === 0) {
      return null;
    }

    // Aggregate TCP health metrics across all windows
    const totals = trafficWindows.reduce((acc, w) => ({
      syn: acc.syn + (w.tcp_syn_count ?? 0),
      ack: acc.ack + (w.tcp_ack_count ?? 0),
      rst: acc.rst + (w.tcp_rst_count ?? 0),
      fin: acc.fin + (w.tcp_fin_count ?? 0),
      retrans: acc.retrans + (w.tcp_retransmissions ?? 0),
      totalTcp: acc.totalTcp + (w.tcp_count ?? 0),
    }), { syn: 0, ack: 0, rst: 0, fin: 0, retrans: 0, totalTcp: 0 });

    if (totals.totalTcp === 0) {
      return null;
    }

    return {
      synAckRatio: totals.syn > 0 ? (totals.ack / totals.syn).toFixed(2) : 'N/A',
      rstRate: ((totals.rst / totals.totalTcp) * 100).toFixed(2) + '%',
      retransmissionRate: ((totals.retrans / totals.totalTcp) * 100).toFixed(2) + '%',
      totalFlags: { syn: totals.syn, ack: totals.ack, rst: totals.rst, fin: totals.fin },
    };
  }, [trafficWindows]);

  const suspiciousPatterns = useMemo<SuspiciousPattern[]>(() => {
    const patterns: SuspiciousPattern[] = [];

    const anomalyCount = results.filter((r) => r.is_anomaly).length;
    if (anomalyCount > 0) {
      patterns.push({
        title: 'Anomaly windows detected',
        detail: `${anomalyCount} windows flagged by the model. Review top flows and TCP health metrics.`,
      });
    }

    if (tcpHealthMetrics && tcpHealthMetrics.synAckRatio !== 'N/A') {
      const synAck = Number(tcpHealthMetrics.synAckRatio);
      if (!Number.isNaN(synAck) && synAck < 0.8) {
        patterns.push({
          title: 'Handshake imbalance',
          detail: `SYN/ACK ratio is ${tcpHealthMetrics.synAckRatio}. Possible failed handshakes or scans.`,
        });
      }
    }

    if (tcpHealthMetrics) {
      const rstRate = Number(tcpHealthMetrics.rstRate.replace('%', ''));
      if (!Number.isNaN(rstRate) && rstRate > 2) {
        patterns.push({
          title: 'High reset activity',
          detail: `RST rate is ${tcpHealthMetrics.rstRate}. Indicates unstable connections or resets.`,
        });
      }
      const retransRate = Number(tcpHealthMetrics.retransmissionRate.replace('%', ''));
      if (!Number.isNaN(retransRate) && retransRate > 1) {
        patterns.push({
          title: 'Retransmissions detected',
          detail: `Retransmission rate is ${tcpHealthMetrics.retransmissionRate}. Potential packet loss.`,
        });
      }
    }

    if (portUsage.length > 0) {
      const topPort = portUsage[0];
      patterns.push({
        title: 'Dominant port activity',
        detail: `${topPort.service} (port ${topPort.port}) accounts for ${topPort.percentage.toFixed(1)}% of traffic.`,
      });
    }

    return patterns.slice(0, 4);
  }, [results, tcpHealthMetrics, portUsage]);
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
        {topFlows.length > 0 ? (
        <div className="mt-4">
          <div className="overflow-x-auto">
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
              {paginatedFlows.map((flow) => (
                <tr key={flow.id} className="border-b border-zinc-800">
                  <td className="py-2">{flow.src}</td>
                  <td className="py-2">{flow.dst}</td>
                  <td className="py-2">{flow.protocol}</td>
                  <td className="py-2">{flow.duration}</td>
                  <td className="py-2">{flow.packets.toLocaleString()}</td>
                  <td className="py-2">{(flow.bytes / 1024 / 1024).toFixed(2)} MB</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          <Pagination
            currentPage={flowsPage}
            totalItems={topFlows.length}
            itemsPerPage={flowsPerPage}
            onPageChange={setFlowsPage}
          />
        </div>
        ) : (
        <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
          <p className="text-zinc-500 text-sm">No flow data available</p>
          <p className="text-zinc-600 text-xs mt-1">IP-level flow tracking required</p>
        </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">TCP Health Metrics</h3>
          {tcpHealthMetrics ? (
          <div className="mt-4 space-y-4">
            <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-400">SYN/ACK Ratio</span>
                <span className="text-lg font-semibold text-cyan-400">{tcpHealthMetrics.synAckRatio}</span>
              </div>
              <p className="text-xs text-zinc-500 mt-1">Normal ≈ 1.0 (balanced handshakes)</p>
            </div>
            
            <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-400">RST Rate</span>
                <span className="text-lg font-semibold text-amber-400">{tcpHealthMetrics.rstRate}</span>
              </div>
              <p className="text-xs text-zinc-500 mt-1">Connection resets (high = instability)</p>
            </div>
            
            <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-400">Retransmission Rate</span>
                <span className="text-lg font-semibold text-teal-400">{tcpHealthMetrics.retransmissionRate}</span>
              </div>
              <p className="text-xs text-zinc-500 mt-1">Packet loss indicator</p>
            </div>

            <div className="mt-3 text-xs text-zinc-600">
              <div className="grid grid-cols-2 gap-2">
                <div>SYN: {tcpHealthMetrics.totalFlags.syn.toLocaleString()}</div>
                <div>ACK: {tcpHealthMetrics.totalFlags.ack.toLocaleString()}</div>
                <div>RST: {tcpHealthMetrics.totalFlags.rst.toLocaleString()}</div>
                <div>FIN: {tcpHealthMetrics.totalFlags.fin.toLocaleString()}</div>
              </div>
            </div>
          </div>
          ) : (
          <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
            <p className="text-zinc-500 text-sm">No TCP health metrics available</p>
            <p className="text-zinc-600 text-xs mt-1">Upload a PCAP file to see TCP analysis</p>
          </div>
          )}
        </div>

        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">Port Usage Distribution</h3>
          <p className="text-xs text-zinc-500 mt-1">Top services by port activity</p>
          {portUsage.length > 0 ? (
          <div className="mt-4">
            <div className="space-y-3">
            {paginatedPorts.map((port) => (
              <div key={`${port.port}-${port.protocol}`} className="flex items-center gap-3">
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-zinc-300">{port.service} ({port.port}/{port.protocol})</span>
                    <span className="text-xs text-zinc-500">{port.percentage.toFixed(1)}%</span>
                  </div>
                  <div className="h-2 bg-zinc-800 rounded-full overflow-hidden mt-1">
                    <div className="h-full bg-cyan-500/70" style={{ width: `${Math.min(100, port.percentage)}%` }} />
                  </div>
                </div>
                <div className="text-xs text-zinc-500 w-20 text-right">{port.count.toLocaleString()}</div>
              </div>
            ))}
            </div>
            <Pagination
              currentPage={portsPage}
              totalItems={portUsage.length}
              itemsPerPage={portsPerPage}
              onPageChange={setPortsPage}
            />
          </div>
          ) : (
          <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
            <p className="text-zinc-500 text-sm">No port usage data available</p>
            <p className="text-zinc-600 text-xs mt-1">Traffic flow analysis required</p>
          </div>
          )}
        </div>
      </div>

      <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-zinc-100">Suspicious Patterns</h3>
        {suspiciousPatterns.length > 0 ? (
        <div className="mt-4 space-y-3">
          {suspiciousPatterns.map((pattern) => (
            <div key={pattern.title} className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
              <div className="text-sm text-amber-300 font-medium">{pattern.title}</div>
              <div className="text-xs text-zinc-400 mt-1">{pattern.detail}</div>
            </div>
          ))}
        </div>
        ) : (
        <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
          <p className="text-zinc-500 text-sm">No suspicious patterns detected</p>
          <p className="text-zinc-600 text-xs mt-1">Pattern analysis on protocol behaviors coming soon</p>
        </div>
        )}
      </div>
    </div>
  );
}
