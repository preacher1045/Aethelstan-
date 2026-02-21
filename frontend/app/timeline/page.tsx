'use client';

import { useMemo, useState } from 'react';
import { useLatestSessionData } from '@/lib/useLatestSessionData';
import Pagination from '@/components/Pagination';

export default function TimelinePage() {
  const { results, insights, trafficWindows, loading, error } = useLatestSessionData();
  const [hoveredWindow, setHoveredWindow] = useState<number | null>(null);
  const [timeFilter, setTimeFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [debugExpanded, setDebugExpanded] = useState<boolean>(false);
  const [statsPage, setStatsPage] = useState(1);
  const statsPerPage = 10;
  const [eventsPage, setEventsPage] = useState(1);
  const eventsPerPage = 6;

  // Debug logging
  console.log('Timeline Debug:', {
    trafficWindowsCount: trafficWindows.length,
    resultsCount: results.length,
    loading,
    sampleWindow: trafficWindows[0],
    sampleResult: results[0]
  });

  const eventMarkers = useMemo(() => {
    if (insights.length === 0) {
      return [];
    }
    return insights
      .filter((i) => i.insight_type === 'alert')
      .map((i) => {
        const severity = (i.severity ?? 'medium').toLowerCase();
        
        const severityColor = severity === 'critical' ? 'text-red-400 bg-red-950/40' :
                             severity === 'high' ? 'text-orange-400 bg-orange-950/40' :
                             severity === 'medium' ? 'text-amber-400 bg-amber-950/40' : 'text-yellow-400 bg-yellow-950/40';
        
        const severityBorder = severity === 'critical' ? 'border-red-900/50' :
                              severity === 'high' ? 'border-orange-900/50' :
                              severity === 'medium' ? 'border-amber-900/50' : 'border-yellow-900/50';
        
        const severityDot = severity === 'critical' ? 'bg-red-500' :
                           severity === 'high' ? 'bg-orange-500' :
                           severity === 'medium' ? 'bg-amber-500' : 'bg-yellow-500';
        
        // Extract window_id from details or metadata
        let windowId: number | null = null;
        let metrics: Record<string, string | number> = {};
        let recommendation = '';
        
        try {
          // Try to parse details for window_id and metrics
          const detailStr = i.details ? String(i.details) : '';
          const windowMatch = detailStr.match(/[Ww]indow\s*(\d+)/);
          if (windowMatch) {
            windowId = parseInt(windowMatch[1]);
          }
          
          // Extract traffic metrics
          const packets = detailStr.match(/(\d+(?:,\d+)*)\s*packets/i)?.[1];
          const bytes = detailStr.match(/(\d+(?:,\d+)*)\s*bytes/i)?.[1];
          const bytesPerSec = detailStr.match(/(\d+(?:,\d+)*)\s*bytes[\\\/]s/i)?.[1];
          const confidence = detailStr.match(/(\d+(?:\.\d+)?)\s*%/)?.[1];
          const ports = detailStr.match(/(\d+)\s*(?:different\s+)?ports/i)?.[1];
          
          if (packets) metrics.packets = packets;
          if (bytes) metrics.bytes = bytes;
          if (bytesPerSec) metrics['bytes/sec'] = bytesPerSec;
          if (confidence) metrics.confidence = `${confidence}%`;
          if (ports) metrics.ports = ports;
        } catch (e) {
          // Silently fail
        }
        
        // Get anomaly score if window matches
        let anomalyScore = '';
        if (windowId !== null) {
          const result = results.find(r => r.window_id === windowId);
          if (result) {
            anomalyScore = (result.anomaly_score ?? 0).toFixed(3);
          }
        }
        
        // Generate recommendations based on event type and severity
        const eventTypeLower = (i.alert_type ?? '').toLowerCase();
        if (eventTypeLower.includes('port') || eventTypeLower.includes('scan')) {
          recommendation = severity === 'critical' ? 'Block source IP immediately' : 
                          severity === 'high' ? 'Investigate source and monitor traffic' : 
                          'Review access logs';
        } else if (eventTypeLower.includes('volume') || eventTypeLower.includes('traffic')) {
          recommendation = severity === 'critical' ? 'Check for DDoS or data exfiltration' :
                          severity === 'high' ? 'Analyze traffic patterns' :
                          'Monitor for sustained high volume';
        } else if (eventTypeLower.includes('protocol') || eventTypeLower.includes('anomal')) {
          recommendation = severity === 'critical' ? 'Capture and analyze packets' :
                          severity === 'high' ? 'Review protocol compliance' :
                          'Log for future analysis';
        } else {
          recommendation = 'Review alert details and take appropriate action';
        }
        
        return {
          timestamp: new Date(i.created_at).toLocaleTimeString(),
          event_type: i.alert_type ?? 'Alert',
          description: i.summary,
          detail: i.details ? String(i.details) : undefined,
          severity,
          severityColor,
          severityBorder,
          severityDot,
          windowId,
          metrics,
          anomalyScore,
          recommendation,
        };
      });
  }, [insights, results]);


  const paginatedEvents = useMemo(() => {
    const start = (eventsPage - 1) * eventsPerPage;
    const end = start + eventsPerPage;
    return eventMarkers.slice(start, end);
  }, [eventMarkers, eventsPage, eventsPerPage]);

  const timelineData = useMemo(() => {
    if (trafficWindows.length === 0) {
      return [];
    }
    return trafficWindows.map((window) => {
      const result = results.find(r => r.window_id === window.window_id);
      return {
        windowId: window.window_id,
        packets: window.packet_count ?? 0,
        bytes: window.total_bytes ?? 0,
        isAnomaly: result?.is_anomaly ?? false,
        severity: result?.severity_level ?? 'low',
        score: result?.anomaly_score ?? 0,
      };
    });
  }, [trafficWindows, results]);

  const filteredTimelineData = useMemo(() => {
    let filtered = [...timelineData];

    // Apply severity filter
    if (severityFilter !== 'all') {
      const severityLevels = ['low', 'medium', 'high', 'critical'];
      const filterIndex = severityLevels.indexOf(severityFilter);
      
      filtered = filtered.filter(d => {
        if (!d.isAnomaly) return false; // Only show anomalies when filtering by severity
        const dataSeverity = severityLevels.indexOf(d.severity);
        // For "critical" filter (index 3), only show critical
        // For others, show that level and above
        if (severityFilter === 'critical') {
          return dataSeverity === 3;
        } else {
          return dataSeverity >= filterIndex;
        }
      });
    }

    // Apply time filter
    if (timeFilter === 'first-half') {
      filtered = filtered.slice(0, Math.ceil(filtered.length / 2));
    } else if (timeFilter === 'second-half') {
      filtered = filtered.slice(Math.floor(filtered.length / 2));
    } else if (timeFilter === 'recent') {
      filtered = filtered.slice(-10);
    }

    return filtered;
  }, [timelineData, timeFilter, severityFilter]);

  const maxPackets = filteredTimelineData.length > 0 ? Math.max(...filteredTimelineData.map(d => d.packets), 1) : 1;

  const windowStats = useMemo(() => {
    if (trafficWindows.length === 0) {
      return [];
    }
    return trafficWindows.map((window) => ({
      window: window.window_id,
      packets: window.packet_count?.toLocaleString() ?? 'N/A',
      bytes: window.total_bytes ? `${(window.total_bytes / 1024 / 1024).toFixed(2)} MB` : 'N/A',
      anomaly: results.find(r => r.window_id === window.window_id)?.is_anomaly ? 'Yes' : 'No',
    }));
  }, [trafficWindows, results]);

  const paginatedStats = useMemo(() => {
    const start = (statsPage - 1) * statsPerPage;
    const end = start + statsPerPage;
    return windowStats.slice(start, end);
  }, [windowStats, statsPage, statsPerPage]);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-zinc-100">Timeline & Forensics</h1>
        <p className="text-sm text-zinc-400 mt-1">Investigate when and how events occurred</p>
      </div>

      {!loading && trafficWindows.length > 0 && (
        <div className="bg-cyan-950/20 border border-cyan-900/40 rounded-lg px-4 py-2 text-xs text-cyan-300">
          Loaded {trafficWindows.length} traffic windows, {results.length} analysis results
        </div>
      )}

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
        <p className="text-xs text-zinc-500 mt-1">Hover over bars to inspect window details</p>
        
        {/* Debug info */}
        <div className="mt-2 bg-zinc-950 border border-zinc-700 rounded text-xs overflow-hidden">
          <button
            onClick={() => setDebugExpanded(!debugExpanded)}
            className="w-full px-2 py-1.5 flex items-center justify-between hover:bg-zinc-900 transition-colors"
          >
            <span className="text-cyan-400 font-semibold">Debug Info</span>
            <span className="text-zinc-500">{debugExpanded ? '▼' : '▶'}</span>
          </button>
          {debugExpanded && (
            <div className="p-2 pt-0 text-zinc-400 border-t border-zinc-800">
              <div>Traffic Windows Loaded: <span className="text-white font-mono">{trafficWindows.length}</span></div>
              <div>Timeline Data Points: <span className="text-white font-mono">{timelineData.length}</span></div>
              <div>After Filters: <span className="text-white font-mono">{filteredTimelineData.length}</span></div>
              <div>Max Packets: <span className="text-white font-mono">{maxPackets.toLocaleString()}</span></div>
              <div>Sample Heights: <span className="text-white font-mono">
                {filteredTimelineData.slice(0, 3).map((d, i) => 
                  `${((d.packets / maxPackets) * 100).toFixed(1)}%`
                ).join(', ')}
              </span></div>
              <div>Loading: <span className="text-white font-mono">{loading.toString()}</span></div>
              <div className="mt-1 text-amber-400">
                {trafficWindows.length === 0 && "⚠ No PCAP data loaded - upload a file on the home page"}
                {trafficWindows.length > 0 && filteredTimelineData.length === 0 && "⚠ All windows filtered out - reset filters to 'All'"}
                {filteredTimelineData.length > 0 && "✓ Ready to display"}
              </div>
            </div>
          )}
        </div>

        {loading ? (
          <div className="mt-4 h-16 rounded-lg border border-zinc-700/50 flex items-center justify-center">
            <p className="text-zinc-500 text-sm">Loading...</p>
          </div>
        ) : trafficWindows.length === 0 ? (
          <div className="mt-4 h-16 rounded-lg border border-zinc-700/50 flex items-center justify-center">
            <p className="text-zinc-500 text-sm">No timeline data available - upload a PCAP file to analyze</p>
          </div>
        ) : filteredTimelineData.length === 0 ? (
          <div className="mt-4 h-16 rounded-lg border border-zinc-700/50 flex items-center justify-center">
            <p className="text-zinc-500 text-sm">No windows match the selected filters (try "All" filters)</p>
          </div>
        ) : (
        <div className="mt-4">
          <div className="relative h-32 rounded-lg bg-zinc-950 border border-zinc-800 p-4">
            <div className="absolute inset-4 flex items-end justify-between gap-0.5">
              {filteredTimelineData.map((data, i) => {
                const height = (data.packets / maxPackets) * 100;
                const barColor = data.isAnomaly 
                  ? (data.severity === 'high' || data.severity === 'critical' ? 'bg-red-500' : 'bg-amber-500')
                  : 'bg-cyan-500/70';
                return (
                  <div
                    key={`${data.windowId}-${i}`}
                    className="flex-1 h-full group relative cursor-pointer flex flex-col justify-end"
                    onMouseEnter={() => setHoveredWindow(i)}
                    onMouseLeave={() => setHoveredWindow(null)}
                  >
                    <div
                      className={`w-full rounded-t transition-all ${barColor} ${hoveredWindow === i ? 'opacity-100 scale-105' : 'opacity-80'}`}
                      style={{ height: `${Math.max(height, 3)}%` }}
                    />
                    {hoveredWindow === i && (
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-zinc-900 border border-cyan-500/50 rounded text-[10px] text-zinc-100 whitespace-nowrap z-10 pointer-events-none">
                        <div className="font-semibold">Window {data.windowId}</div>
                        <div>{data.packets.toLocaleString()} packets</div>
                        <div>{(data.bytes / 1024 / 1024).toFixed(2)} MB</div>
                        {data.isAnomaly && (
                          <div className="text-red-400 mt-1">
                            ⚠ {data.severity} anomaly
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
          <div className="mt-3 flex justify-between text-xs text-zinc-500">
            <span>Start</span>
            <span>Window {Math.floor(filteredTimelineData.length / 4)}</span>
            <span>Window {Math.floor(filteredTimelineData.length / 2)}</span>
            <span>Window {Math.floor(filteredTimelineData.length * 3 / 4)}</span>
            <span>End</span>
          </div>
          <div className="mt-2 text-xs text-zinc-500 text-center">
            Showing {filteredTimelineData.length} of {timelineData.length} windows
          </div>
        </div>
        )}
      </div>

      <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-zinc-100">Filter Controls</h3>
        <p className="text-xs text-zinc-500 mt-1">Filter timeline view by time range and severity</p>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-3">
            <label className="text-xs text-zinc-500 uppercase block mb-2">Time Range</label>
            <select
              value={timeFilter}
              onChange={(e) => setTimeFilter(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Windows</option>
              <option value="first-half">First Half</option>
              <option value="second-half">Second Half</option>
              <option value="recent">Recent 10</option>
            </select>
          </div>
          <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-3">
            <label className="text-xs text-zinc-500 uppercase block mb-2">Severity</label>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical Only</option>
              <option value="high">High & Above</option>
              <option value="medium">Medium & Above</option>
              <option value="low">Low & Above</option>
            </select>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-2 text-xs">
          <span className="text-zinc-500">Active Filters:</span>
          <span className="px-2 py-1 bg-cyan-500/10 text-cyan-300 rounded border border-cyan-500/30">
            {timeFilter === 'all' ? 'All Time' : timeFilter.replace('-', ' ')}
          </span>
          <span className="px-2 py-1 bg-cyan-500/10 text-cyan-300 rounded border border-cyan-500/30">
            {severityFilter === 'all' ? 'All Severity' : severityFilter}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">Event Markers</h3>
          <p className="text-xs text-zinc-500 mt-1">Timeline alerts and anomaly events</p>
          {eventMarkers.length > 0 ? (
          <div className="mt-4">
            <div className="space-y-2">
            {paginatedEvents.map((event, idx) => {
              const severityBgClass = event.severity === 'critical' ? 'bg-red-950/20' :
                                    event.severity === 'high' ? 'bg-orange-950/20' :
                                    event.severity === 'medium' ? 'bg-amber-950/20' : 'bg-yellow-950/20';
              return (
              <div key={`${event.timestamp}-${idx}`} className={`border rounded-lg p-3 ${event.severityBorder} ${severityBgClass} hover:border-opacity-100 transition-colors`}>
                <div className="flex items-start gap-3">
                  <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${event.severityDot}`} />
                  <div className="flex-1 min-w-0">
                    {/* Header row */}
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className={`text-xs font-semibold uppercase px-1.5 py-0.5 rounded ${event.severityColor} line-clamp-1`}>
                          {event.severity}
                        </span>
                        <span className="text-xs text-zinc-400 font-mono">{event.timestamp}</span>
                        {event.windowId !== null && (
                          <span className="text-xs text-cyan-400 font-mono bg-cyan-500/10 px-1.5 py-0.5 rounded">
                            W{event.windowId}
                          </span>
                        )}
                      </div>
                    </div>
                    
                    {/* Event type and description */}
                    <div className="text-sm font-medium text-zinc-200 mb-1">{event.event_type}</div>
                    <div className="text-xs text-zinc-400 leading-relaxed mb-2">{event.description}</div>
                    
                    {/* Metrics grid */}
                    {Object.keys(event.metrics).length > 0 && (
                      <div className="grid grid-cols-2 gap-2 mb-2 text-xs">
                        {Object.entries(event.metrics).map(([key, value]) => (
                          <div key={`metric-${key}`} className="text-zinc-500">
                            <span className="capitalize">{key}:</span>
                            <span className="text-cyan-400 font-mono ml-1">{String(value)}</span>
                          </div>
                        ))}
                        {event.anomalyScore && (
                          <div className="text-zinc-500">
                            <span>Confidence:</span>
                            <span className="text-cyan-400 font-mono ml-1">{event.anomalyScore}</span>
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* Full details */}
                    {event.detail && (
                      <div className="text-xs text-zinc-500 italic border-l-2 border-zinc-700 pl-2 mb-2">
                        {event.detail}
                      </div>
                    )}
                    
                    {/* Recommendation */}
                    <div className="flex items-start gap-2 pt-2 border-t border-zinc-700/50 mt-2">
                      <span className="text-xs text-amber-400 font-semibold">Action:</span>
                      <span className="text-xs text-amber-200">{event.recommendation}</span>
                    </div>
                  </div>
                </div>
              </div>
              );
            })}
            </div>
            <Pagination
              currentPage={eventsPage}
              totalItems={eventMarkers.length}
              itemsPerPage={eventsPerPage}
              onPageChange={setEventsPage}
            />
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
          <div className="mt-4">
            <div className="overflow-x-auto">
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
                {paginatedStats.map((row) => (
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
            <Pagination
              currentPage={statsPage}
              totalItems={windowStats.length}
              itemsPerPage={statsPerPage}
              onPageChange={setStatsPage}
            />
          </div>
          ) : (
          <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
            <p className="text-zinc-500 text-sm">No window statistics available</p>
            <p className="text-zinc-600 text-xs mt-1">Traffic analysis required</p>
          </div>
          )}
        </div>
      </div>
    </div>
  );
}
