'use client';

import { useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useSessionData } from '@/lib/useSessionData';
import Pagination from '@/components/Pagination';
import { exportToCSV } from '@/lib/export';

export default function AnomaliesPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('sessionId');
  const { session, results, insights, trafficWindows, flows, portStats, loading, error } = useSessionData(sessionId);
  const [hoveredPoint, setHoveredPoint] = useState<number | null>(null);
  const [anomaliesPage, setAnomaliesPage] = useState(1);
  const anomaliesPerPage = 4;
  const [insightsPage, setInsightsPage] = useState(1);
  const insightsPerPage = 4;
  const [expandedAnomalyId, setExpandedAnomalyId] = useState<number | null>(null);
  const [severityFilter, setSeverityFilter] = useState('all');
  const [protocolFilter, setProtocolFilter] = useState('all');

  const scoreSeries = useMemo(() => {
    if (results.length === 0) {
      return [];
    }

    const ordered = [...results].sort((a, b) => (a.window_id ?? 0) - (b.window_id ?? 0));
    const sliceStart = Math.max(ordered.length - 28, 0);

    return ordered.slice(sliceStart).map((item) => ({
      value: item.anomaly_score ?? 0,
      isPeak: item.is_anomaly,
    }));
  }, [results]);

  const scoreRange = useMemo(() => {
    if (scoreSeries.length === 0) return { min: 0, max: 1 };
    const values = scoreSeries.map(p => p.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    // Add 10% padding to prevent points from touching edges
    const range = max - min || 1;
    return {
      min: min - range * 0.1,
      max: max + range * 0.1
    };
  }, [scoreSeries]);

  const maxScore = scoreRange.max;

  const anomalyCards = useMemo(() => {
    const anomalies = results.filter((item) => item.is_anomaly);
    if (anomalies.length === 0) {
      return [];
    }

    return anomalies.map((item) => {
      // Find corresponding traffic window data
      const windowData = trafficWindows.find(w => w.window_id === item.window_id);
      
      // Find top ports/protocols for this window
      const windowPorts = portStats.filter(p => p.window_id === item.window_id)
        .sort((a, b) => (b.packet_count ?? 0) - (a.packet_count ?? 0))
        .slice(0, 3);
      
      // Generate smart explanation based on available data
      const generateExplanation = () => {
        const reasons: string[] = [];
        
        // Check for port scanning patterns
        const uniquePorts = portStats.filter(p => p.window_id === item.window_id).length;
        if (uniquePorts > 10) {
          reasons.push(`${uniquePorts} different ports accessed`);
        }
        
        // Check for high volume
        const packets = windowData?.packet_count ?? 0;
        if (packets > 100000) {
          reasons.push('unusually high packet rate');
        }
        
        // Check for contributing features
        if (item.contributing_features) {
          try {
            const features = typeof item.contributing_features === 'string' 
              ? JSON.parse(item.contributing_features)
              : item.contributing_features;
            
            // Get top contributing feature
            const topFeature = Object.entries(features)
              .sort(([, a], [, b]) => Number(b) - Number(a))[0];
            
            if (topFeature) {
              const featureName = String(topFeature[0])
                .replace(/_/g, ' ')
                .replace(/avg|max|min/gi, match => match.toUpperCase());
              reasons.push(`abnormal ${featureName}`);
            }
          } catch (e) {
            // Silently fail if parsing issues
          }
        }
        
        // Check protocol patterns
        const tcpPorts = windowPorts.filter(p => p.protocol === 'TCP');
        if (tcpPorts.length === windowPorts.length && windowPorts.length >= 3) {
          const commonPorts = [22, 23, 80, 443, 3389];
          const hasCommonPorts = tcpPorts.some(p => commonPorts.includes(p.port ?? 0));
          if (!hasCommonPorts) {
            reasons.push('unusual TCP port usage');
          }
        }
        
        // Fallback based on severity
        if (reasons.length === 0) {
          if (item.severity_level === 'critical' || item.severity_level === 'high') {
            reasons.push('significant deviation from normal traffic patterns');
          } else {
            reasons.push('detected anomaly in traffic behavior');
          }
        }
        
        return reasons.slice(0, 2).join('; ');
      };
      
      return {
        windowId: item.window_id,
        severity: item.severity_level ?? 'medium',
        score: (item.anomaly_score ?? 0).toFixed(2),
        anomalyType: item.anomaly_type ?? 'Behavioral deviation',
        explanation: generateExplanation(),
        packets: windowData?.packet_count ?? 0,
        bytes: windowData?.total_bytes ?? 0,
        topPorts: windowPorts.map(p => `${p.protocol}/${p.port}`).join(', ') || 'N/A',
      };
    });
  }, [results, trafficWindows, portStats]);

  // Extract unique protocols from anomaly cards for filter dropdown
  const availableProtocols = useMemo(() => {
    const protocols = new Set<string>();
    anomalyCards.forEach(card => {
      if (card.topPorts && card.topPorts !== 'N/A') {
        card.topPorts.split(', ').forEach(p => {
          const proto = p.split('/')[0];
          if (proto) protocols.add(proto);
        });
      }
    });
    return Array.from(protocols).sort();
  }, [anomalyCards]);

  // Filter anomaly cards by severity and protocol
  const filteredAnomalyCards = useMemo(() => {
    let filtered = anomalyCards;

    if (severityFilter !== 'all') {
      const severityOrder = ['low', 'medium', 'high', 'critical'];
      const minIndex = severityOrder.indexOf(severityFilter);
      filtered = filtered.filter(card => severityOrder.indexOf(card.severity) >= minIndex);
    }

    if (protocolFilter !== 'all') {
      filtered = filtered.filter(card =>
        card.topPorts.toUpperCase().includes(protocolFilter.toUpperCase())
      );
    }

    return filtered;
  }, [anomalyCards, severityFilter, protocolFilter]);

  const paginatedAnomalies = useMemo(() => {
    const start = (anomaliesPage - 1) * anomaliesPerPage;
    const end = start + anomaliesPerPage;
    return filteredAnomalyCards.slice(start, end);
  }, [filteredAnomalyCards, anomaliesPage, anomaliesPerPage]);

  const insightCards = useMemo(() => {
    const allInsights = insights.filter((item) => item.insight_type === 'alert');
    if (allInsights.length === 0) {
      return [];
    }
    
    return allInsights.map((item) => {
      const severityMap: Record<string, string> = {
        'critical': 'critical',
        'high': 'high',
        'medium': 'medium',
        'low': 'low'
      };
      
      const severity = (item.severity ?? 'medium').toLowerCase();
      const normalizedSeverity = severityMap[severity] || 'medium';
      
      const severityColor = normalizedSeverity === 'critical' ? 'text-red-400 bg-red-950/40' :
                           normalizedSeverity === 'high' ? 'text-orange-400 bg-orange-950/40' :
                           normalizedSeverity === 'medium' ? 'text-amber-400 bg-amber-950/40' : 'text-yellow-400 bg-yellow-950/40';
      
      const severityBorder = normalizedSeverity === 'critical' ? 'border-red-900/50' :
                            normalizedSeverity === 'high' ? 'border-orange-900/50' :
                            normalizedSeverity === 'medium' ? 'border-amber-900/50' : 'border-yellow-900/50';
      
      // Parse metadata from details or raw object
      let metadata: Record<string, string | number> = {};
      try {
        if (typeof item.details === 'object' && item.details !== null) {
          metadata = item.details as Record<string, string | number>;
        } else if (typeof item.details === 'string') {
          // Try to extract key metrics from string details
          const detailStr = item.details;
          const packets = detailStr.match(/(\d+(?:,\d+)*)\s*packets/i)?.[1];
          const bytes = detailStr.match(/(\d+(?:,\d+)*)\s*bytes/i)?.[1];
          const confidence = detailStr.match(/(\d+(?:\.\d+)?)\s*%/)?.[1];
          
          if (packets) metadata.packets = packets;
          if (bytes) metadata.bytes = bytes;
          if (confidence) metadata.confidence = `${confidence}%`;
        }
      } catch (e) {
        // Silently fail
      }
      
      return {
        title: item.summary,
        detail: item.details ? String(item.details) : 'Review alert details for context.',
        severity: normalizedSeverity,
        severityColor,
        severityBorder,
        timestamp: item.created_at ? new Date(item.created_at).toLocaleTimeString() : 'N/A',
        metadata,
      };
    });
  }, [insights]);

  const paginatedInsights = useMemo(() => {
    const start = (insightsPage - 1) * insightsPerPage;
    const end = start + insightsPerPage;
    return insightCards.slice(start, end);
  }, [insightCards, insightsPage, insightsPerPage]);

  // Helper function to generate Wireshark display filter
  const generateWiresharkFilter = (windowId: number) => {
    // Try to find window by id, then by window_id
    let window = trafficWindows.find(w => w.id === windowId);
    if (!window) {
      window = trafficWindows.find(w => w.window_id === windowId);
    }
    
    // If still not found, create basic window object from anomaly data
    if (!window) {
      console.warn(`Window ${windowId} not found in trafficWindows. Using default time-based filter.`);
      // Get any anomaly result for this window to extract time info
      const anomalyResult = results.find(r => r.window_id === windowId || r.traffic_window_id === windowId);
      if (!anomalyResult) {
        return null;
      }
      // Create a basic window object with estimated timestamps
      window = {
        id: windowId,
        session_id: session?.session_id ?? '',
        window_id: windowId,
        window_start: (anomalyResult.created_at ? new Date(anomalyResult.created_at).getTime() / 1000 : 0),
        window_end: (anomalyResult.created_at ? new Date(anomalyResult.created_at).getTime() / 1000 + 60 : 60),
      };
    }

    // Get all flows that occurred during this window
    const windowFlows = flows.filter(f => {
      const timestamp = (f.start_timestamp ?? 0) * 1000; // Convert to ms if in seconds
      const windowStart = (window?.window_start ?? 0) * 1000;
      const windowEnd = (window?.window_end ?? 0) * 1000;
      return timestamp >= windowStart && timestamp <= windowEnd;
    });

    // Time window info (always available)
    const startTime = new Date((window?.window_start ?? 0) * 1000).toISOString();
    const endTime = new Date((window?.window_end ?? 0) * 1000).toISOString();
    const startTimestamp = window?.window_start ?? 0;
    const endTimestamp = window?.window_end ?? 0;

    // If no flows available, provide time-based filter as fallback
    if (windowFlows.length === 0) {
      // Extract protocol info from window stats
      const protocols = [];
      if ((window?.tcp_count ?? 0) > 0) protocols.push('tcp');
      if ((window?.udp_count ?? 0) > 0) protocols.push('udp');
      if ((window?.icmp_count ?? 0) > 0) protocols.push('icmp');
      
      const protocolArray = protocols.length > 0 ? protocols : [];
      
      // Time-based filter with protocol hints
      let filter = 'frame.time_epoch >= ' + startTimestamp + ' and frame.time_epoch <= ' + endTimestamp;
      if (protocolArray.length > 0 && protocolArray.length <= 3) {
        filter += ' && (' + protocolArray.join(' || ') + ')';
      }

      return {
        filter,
        startTime,
        endTime,
        ips: [],
        ports: [],
        protocols: protocolArray,
        flowCount: 0,
        isFallback: true,
        packetCount: window?.packet_count ?? 0,
        totalBytes: window?.total_bytes ?? 0
      };
    }

    // Extract unique IPs and ports from available flows
    const ips = new Set<string>();
    const ports = new Set<string>();
    let protocols = new Set<string>();

    windowFlows.forEach(f => {
      if (f.src_ip) ips.add(f.src_ip);
      if (f.dst_ip) ips.add(f.dst_ip);
      if (f.src_port) ports.add(f.src_port.toString());
      if (f.dst_port) ports.add(f.dst_port.toString());
      if (f.protocol) {
        protocols.add(f.protocol.toLowerCase());
      }
    });

    const ipArray = Array.from(ips);
    const portArray = Array.from(ports);
    const protocolArray = Array.from(protocols);

    // Build filter components
    let filters = [];

    // IP filter
    if (ipArray.length > 0) {
      if (ipArray.length === 1) {
        filters.push(`(ip.src == ${ipArray[0]} || ip.dst == ${ipArray[0]})`);
      } else {
        filters.push(`(ip.src in {${ipArray.join(", ")}} || ip.dst in {${ipArray.join(", ")}})`);
      }
    }

    // Protocol filter
    if (protocolArray.length > 0 && protocolArray.length < 5) {
      const protocolFilters = protocolArray.map(p => `${p.toUpperCase()}`);
      if (protocolFilters.length === 1) {
        filters.push(`${protocolFilters[0].toLowerCase()}`);
      } else {
        filters.push(`(${protocolFilters.map(p => p.toLowerCase()).join(' || ')})`);
      }
    }

    let filter = filters.join(' && ');
    if (!filter) filter = 'No filter available';

    return {
      filter,
      startTime,
      endTime,
      ips: ipArray,
      ports: portArray,
      protocols: protocolArray,
      flowCount: windowFlows.length,
      isFallback: false
    };
  };

  const featureContributions = useMemo(() => {
    // Find the most anomalous window with contributing_features data
    const anomalies = results
      .filter((item) => item.is_anomaly && item.contributing_features)
      .sort((a, b) => (a.anomaly_score ?? 0) - (b.anomaly_score ?? 0)); // Lower score = more anomalous
    
    if (anomalies.length === 0) {
      return [];
    }
    
    // Parse contributing_features from first (most anomalous) window
    try {
      const features = typeof anomalies[0].contributing_features === 'string' 
        ? JSON.parse(anomalies[0].contributing_features)
        : anomalies[0].contributing_features;
      
      // Convert to array format for display
      return Object.entries(features).map(([feature, importance]) => ({
        feature: feature.replace(/_/g, ' '), // Make readable
        importance: Number(importance)
      }));
    } catch (e) {
      console.error('Failed to parse contributing_features:', e);
      return [];
    }
  }, [results]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-zinc-100">Anomalies & ML Insights</h1>
          <p className="text-sm text-zinc-400 mt-1">Machine-detected unusual behavior and explainability</p>
        </div>
        <button
          onClick={() => {
            const rows = filteredAnomalyCards.map(c => ({
              window_id: c.windowId,
              severity: c.severity,
              anomaly_score: c.score,
              anomaly_type: c.anomalyType,
              explanation: c.explanation,
              packets: c.packets,
              bytes: c.bytes,
              top_ports: c.topPorts,
            }));
            exportToCSV(rows, `anomalies_${sessionId || 'latest'}`);
          }}
          disabled={filteredAnomalyCards.length === 0}
          className="px-4 py-2 text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-lg transition-colors"
        >
          ⬇ Export CSV
        </button>
      </div>

      {error && (
        <div className="bg-red-950/40 border border-red-900/40 rounded-lg px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {loading && (
        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg px-4 py-3 text-sm text-zinc-400">
          Loading anomaly analytics from latest session...
        </div>
      )}

      <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-zinc-100">Anomaly Score Timeline</h3>
        <p className="text-xs text-zinc-500 mt-1">Isolation Forest scores across time windows</p>
        {scoreSeries.length > 0 ? (
        <div className="mt-4  rounded-lg bg-zinc-950 border border-zinc-800 p-5">
          <div className="relative h-72">
            <div className="absolute left-0 top-0 bottom-8 w-12 flex flex-col justify-between text-[10px] text-zinc-500">
              <span>{scoreRange.max.toFixed(2)}</span>
              <span>{(scoreRange.min + (scoreRange.max - scoreRange.min) * 0.75).toFixed(2)}</span>
              <span>{(scoreRange.min + (scoreRange.max - scoreRange.min) * 0.5).toFixed(2)}</span>
              <span>{(scoreRange.min + (scoreRange.max - scoreRange.min) * 0.25).toFixed(2)}</span>
              <span>{scoreRange.min.toFixed(2)}</span>
            </div>

            <div className="absolute -left-2 top-1/2 -translate-y-1/2 -rotate-90 text-[10px] text-zinc-500">
              Anomaly Score
            </div>

            <div className="ml-14 h-full pb-8 border-l border-b border-zinc-700 relative">
              <div className="absolute top-0 left-0 right-0 bottom-8">
                <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
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
                  <polyline
                    points={scoreSeries
                      .map((point, i) => {
                        const denom = Math.max(scoreSeries.length - 1, 1);
                        const x = (i / denom) * 100;
                        const normalized = (point.value - scoreRange.min) / (scoreRange.max - scoreRange.min);
                        const y = 100 - normalized * 100;
                        return `${x},${y}`;
                      })
                      .join(' ')}
                    fill="none"
                    stroke="#22d3ee"
                    strokeWidth="2"
                    vectorEffect="non-scaling-stroke"
                  />
                </svg>
                <div className="absolute inset-0">
                  {scoreSeries.map((point, i) => {
                    const denom = Math.max(scoreSeries.length - 1, 1);
                    const x = (i / denom) * 100;
                    const normalized = (point.value - scoreRange.min) / (scoreRange.max - scoreRange.min);
                    const y = 100 - normalized * 100;
                    const sizeClass = point.isPeak ? 'w-2 h-2' : 'w-1.5 h-1.5';
                    const colorClass = point.isPeak ? 'bg-red-500' : 'bg-cyan-300';
                    const orderedResults = [...results].sort((a, b) => (a.window_id ?? 0) - (b.window_id ?? 0));
                    const sliceStart = Math.max(orderedResults.length - 28, 0);
                    const windowData = orderedResults.slice(sliceStart)[i];
                    
                    return (
                      <div
                        key={i}
                        className="absolute group"
                        style={{ left: `${x}%`, top: `${y}%`, transform: 'translate(-50%, -50%)' }}
                        onMouseEnter={() => setHoveredPoint(i)}
                        onMouseLeave={() => setHoveredPoint(null)}
                      >
                        <div className={`rounded-full ${sizeClass} ${colorClass} cursor-pointer transition-transform group-hover:scale-150`} />
                        {hoveredPoint === i && (
                          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-zinc-900 border border-cyan-500/50 rounded text-[10px] text-zinc-100 whitespace-nowrap z-10 pointer-events-none">
                            <div className="font-semibold">Window {windowData?.window_id ?? i}</div>
                            <div>Score: {point.value.toFixed(3)}</div>
                            <div className={point.isPeak ? 'text-red-400' : 'text-cyan-400'}>
                              {point.isPeak ? '⚠ Anomaly' : '✓ Normal'}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="ml-14 mt-3 grid grid-cols-5 text-[9px] text-zinc-500 text-center px-2">
              <span>00:00</span>
              <span>06:00</span>
              <span>12:00</span>
              <span>18:00</span>
              <span>24:00</span>
            </div>
            <div className="ml-14 text-center text-[10px] text-zinc-500">Time Window</div>
          </div>
        </div>
        ) : (
        <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
          <p className="text-zinc-500 text-sm">No anomaly score data available</p>
          <p className="text-zinc-600 text-xs mt-1">Run anomaly detection on a session first</p>
        </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* Filter Controls */}
        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6 lg:col-span-2">
          <h3 className="text-lg font-semibold text-zinc-100">Filter Controls</h3>
          <p className="text-xs text-zinc-500 mt-1">Narrow anomalies by severity and protocol</p>
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-3">
              <label className="text-xs text-zinc-500 uppercase block mb-2">Severity</label>
              <select
                value={severityFilter}
                onChange={(e) => { setSeverityFilter(e.target.value); setAnomaliesPage(1); }}
                className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-300 focus:outline-none focus:border-cyan-500"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical Only</option>
                <option value="high">High & Above</option>
                <option value="medium">Medium & Above</option>
                <option value="low">Low & Above</option>
              </select>
            </div>
            <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-3">
              <label className="text-xs text-zinc-500 uppercase block mb-2">Protocol</label>
              <select
                value={protocolFilter}
                onChange={(e) => { setProtocolFilter(e.target.value); setAnomaliesPage(1); }}
                className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-300 focus:outline-none focus:border-cyan-500"
              >
                <option value="all">All Protocols</option>
                {availableProtocols.map(proto => (
                  <option key={proto} value={proto}>{proto}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2 text-xs">
            <span className="text-zinc-500">Active Filters:</span>
            <span className="px-2 py-1 bg-cyan-500/10 text-cyan-300 rounded border border-cyan-500/30">
              {severityFilter === 'all' ? 'All Severity' : severityFilter}
            </span>
            <span className="px-2 py-1 bg-cyan-500/10 text-cyan-300 rounded border border-cyan-500/30">
              {protocolFilter === 'all' ? 'All Protocols' : protocolFilter}
            </span>
            <span className="text-zinc-600 ml-2">
              {filteredAnomalyCards.length} of {anomalyCards.length} anomalies
            </span>
          </div>
        </div>

        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">Anomalous Flows</h3>
          <p className="text-xs text-zinc-500 mt-1">Flagged windows by severity level</p>
          {anomalyCards.length > 0 ? (
          <div className="mt-4">
            <div className="space-y-3">
            {paginatedAnomalies.map((card, index) => {
              const severityColor = card.severity === 'critical' ? 'text-red-400' :
                                   card.severity === 'high' ? 'text-red-300' :
                                   card.severity === 'medium' ? 'text-amber-400' : 'text-yellow-400';
              return (
              <div key={`${card.windowId}-${index}`} className="bg-zinc-950 border border-zinc-800 rounded-lg p-4 hover:border-cyan-500/50 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-semibold uppercase ${severityColor}`}>{card.severity}</span>
                    <span className="text-xs text-zinc-600">|</span>
                    <span className="text-xs text-zinc-400">Window {card.windowId}</span>
                  </div>
                  <span className="text-xs text-zinc-500 font-mono">Score: {card.score}</span>
                </div>
                <div className="text-sm text-zinc-300 mb-1">{card.anomalyType}</div>
                <div className="text-xs text-amber-200/80 mb-3 italic">
                  Why: {card.explanation}
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="text-zinc-500">
                    <span className="text-cyan-400">{card.packets.toLocaleString()}</span> packets
                  </div>
                  <div className="text-zinc-500">
                    <span className="text-cyan-400">{(card.bytes / 1024 / 1024).toFixed(2)}</span> MB
                  </div>
                </div>
                <div className="mt-2 text-xs text-zinc-500">
                  Top ports: <span className="text-zinc-400 font-mono">{card.topPorts}</span>
                </div>
                
                {/* Wireshark Filter Section */}
                <div className="mt-3 pt-3 border-t border-zinc-800">
                  <button
                    onClick={() => setExpandedAnomalyId(expandedAnomalyId === card.windowId ? null : card.windowId)}
                    className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold transition-colors"
                  >
                    {expandedAnomalyId === card.windowId ? '▼' : '▶'} Verify in Wireshark
                  </button>
                  
                  {expandedAnomalyId === card.windowId && (() => {
                    const filterData = generateWiresharkFilter(card.windowId);
                    return filterData ? (
                      <div className="mt-2 space-y-2 bg-zinc-950/50 p-2 rounded border border-zinc-700/50">
                        <div className="text-[10px] text-zinc-400 space-y-1">
                          {filterData.ips.length > 0 && (
                            <div>
                              <span className="text-zinc-500">IPs:</span>
                              <span className="text-cyan-300 ml-1 font-mono">{filterData.ips.join(', ')}</span>
                            </div>
                          )}
                          {filterData.protocols.length > 0 && (
                            <div>
                              <span className="text-zinc-500">Protocols:</span>
                              <span className="text-amber-300 ml-1 font-mono uppercase">{filterData.protocols.join(', ')}</span>
                            </div>
                          )}
                          {filterData.ports && filterData.ports.length > 0 && (
                            <div>
                              <span className="text-zinc-500">Ports:</span>
                              <span className="text-purple-300 ml-1 font-mono">{filterData.ports.slice(0, 5).join(', ')}{filterData.ports.length > 5 ? ` +${filterData.ports.length - 5}` : ''}</span>
                            </div>
                          )}
                          <div>
                            <span className="text-zinc-500">Time Window:</span>
                            <span className="text-green-300 ml-1 font-mono">{new Date(filterData.startTime).toLocaleTimeString()}</span>
                          </div>
                        </div>
                        
                        {filterData.isFallback && (
                          <div className="mt-2 p-2 bg-orange-950/30 border border-orange-800/50 rounded text-[9px] text-orange-200">
                            <div className="font-semibold mb-1">⚠️ Limited Flow Data</div>
                            <div className="text-orange-300 mb-1">
                              Detailed flow information not available. Using time-based filter instead.
                            </div>
                            <div className="text-orange-300 text-[8px]">
                              Window stats: <span className="font-mono text-yellow-300">{filterData.packetCount} packets, {((filterData.totalBytes ?? 0) / 1024 / 1024).toFixed(2)} MB</span>
                            </div>
                          </div>
                        )}
                        
                        <div className="mt-2">
                          <div className="text-[10px] text-zinc-500 mb-1">Display Filter:</div>
                          <div className="bg-black/50 border border-zinc-700 rounded p-2 flex items-start gap-2">
                            <code className="text-[11px] text-cyan-300 font-mono flex-1 break-all">{filterData.filter}</code>
                            <button
                              onClick={() => {
                                navigator.clipboard.writeText(filterData.filter);
                              }}
                              className="text-[10px] px-2 py-1 bg-cyan-500 text-zinc-900 rounded hover:bg-cyan-400 transition-colors shrink-0 font-semibold"
                            >
                              Copy
                            </button>
                          </div>
                        </div>

                        {/* Protocol Layer Notes */}
                        {filterData.protocols.includes('udp') && (
                          <div className="mt-2 p-2 bg-blue-950/30 border border-blue-800/50 rounded text-[9px] text-blue-200">
                            <div className="font-semibold mb-1">📡 Protocol Note</div>
                            <div className="text-blue-300 mb-1">
                              UDP filters will also match <span className="font-semibold text-cyan-300">QUIC</span> traffic, since QUIC is an application-layer protocol that runs on top of UDP.
                            </div>
                            <div className="text-blue-300 mb-1">
                              In Wireshark, you might see packets labeled as <span className="font-mono text-purple-300">"QUIC"</span> even though the transport layer is UDP.
                            </div>
                            <div className="text-blue-300 text-[8px]">
                              💡 To filter <span className="font-semibold">QUIC only</span> (excluding plain UDP), use: <span className="font-mono text-green-300">quic</span>
                            </div>
                          </div>
                        )}

                        <div className="text-[9px] text-zinc-500 italic">
                          1. Open PCAP in Wireshark
                          <br />
                          2. Paste filter in Display Filter box
                          <br />
                          3. Review packets during anomaly window
                        </div>
                      </div>
                    ) : (
                      <div className="mt-2 text-[10px] text-zinc-500 bg-red-950/20 p-2 rounded">
                        Unable to generate filter for this window
                      </div>
                    );
                  })()}
                </div>
              </div>
              );
            })}
            </div>
            <Pagination
              currentPage={anomaliesPage}
              totalItems={filteredAnomalyCards.length}
              itemsPerPage={anomaliesPerPage}
              onPageChange={setAnomaliesPage}
            />
          </div>
          ) : (
          <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
            <p className="text-zinc-500 text-sm">No anomalies detected</p>
            <p className="text-zinc-600 text-xs mt-1">Normal traffic patterns</p>
          </div>
          )}
        </div>

        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">Feature Contribution</h3>
          <p className="text-xs text-zinc-500 mt-1">Why the model flagged these windows</p>
          {featureContributions.length > 0 ? (
          <div className="mt-4 space-y-3">
            {featureContributions.map((item) => (
              <div key={item.feature} className="flex items-center gap-3">
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-zinc-300 capitalize">{item.feature}</span>
                    <span className="text-xs text-zinc-500">{item.importance.toFixed(1)}%</span>
                  </div>
                  <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-linear-to-r from-cyan-500 to-teal-500 rounded-full"
                      style={{ width: `${item.importance}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
          ) : (
          <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
            <p className="text-zinc-500 text-sm">No feature contribution data available</p>
            <p className="text-zinc-600 text-xs mt-1">Run anomaly detection to see ML explainability</p>
          </div>
          )}
        </div>
      </div>

      <div className="bg-linear-to-r from-red-950/30 to-amber-950/30 border border-red-900/30 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-zinc-100">Insights</h3>
        <p className="text-xs text-zinc-500 mt-1">Alerts and recommendations from analysis</p>
        {insightCards.length > 0 ? (
        <div className="mt-4">
          <div className="space-y-3">
            {paginatedInsights.map((card, index) => {
              const severityBgClass = card.severity === 'critical' ? 'bg-red-950/20' :
                                     card.severity === 'high' ? 'bg-orange-950/20' :
                                     card.severity === 'medium' ? 'bg-amber-950/20' : 'bg-yellow-950/20';
              return (
              <div key={`${card.title}-${index}`} className={`border rounded-lg p-4 ${card.severityBorder} ${severityBgClass}`}>
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-semibold uppercase px-2 py-0.5 rounded ${card.severityColor}`}>
                      {card.severity}
                    </span>
                    <span className="text-xs text-zinc-500">{card.timestamp}</span>
                  </div>
                </div>
                <div className="text-sm font-medium text-zinc-200 mb-2">{card.title}</div>
                <p className="text-xs text-zinc-400 leading-relaxed mb-3">{card.detail}</p>
                {Object.keys(card.metadata).length > 0 && (
                  <div className="grid grid-cols-2 gap-2 pt-3 border-t border-zinc-700/50">
                    {Object.entries(card.metadata).map(([key, value]) => (
                      <div key={`${card.title}-${key}`} className="text-xs">
                        <span className="text-zinc-500 capitalize">{key.replace(/_/g, ' ')}:</span>
                        <span className="text-cyan-400 font-mono ml-1">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              );
            })}
          </div>
          <Pagination
            currentPage={insightsPage}
            totalItems={insightCards.length}
            itemsPerPage={insightsPerPage}
            onPageChange={setInsightsPage}
          />
        </div>
        ) : (
        <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
          <p className="text-zinc-500 text-sm">No alert insights available</p>
          <p className="text-zinc-600 text-xs mt-1">Alerts will appear here when detected</p>
        </div>
        )}
      </div>
    </div>
  );
}
