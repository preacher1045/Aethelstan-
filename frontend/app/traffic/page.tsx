'use client';

import { useMemo } from 'react';
import { useLatestSessionData } from '@/lib/useLatestSessionData';

type HistogramData = {
  values: number[];
  max: number;
  labels: string[];
};

export default function TrafficAnalysisPage() {
  const { session, results, trafficWindows, loading, error } = useLatestSessionData();

  const flowHistogram = useMemo<HistogramData | null>(() => {
    if (trafficWindows.length === 0) {
      return null;
    }

    // Aggregate flow duration distribution across all windows
    const bucketKeys = ["0-5", "5-10", "10-20", "20-30", "30+"] as const;
    const aggregated = { "0-5": 0, "5-10": 0, "10-20": 0, "20-30": 0, "30+": 0 };

    trafficWindows.forEach(w => {
      if (w.flow_duration_distribution) {
        try {
          const dist = typeof w.flow_duration_distribution === 'string' 
            ? JSON.parse(w.flow_duration_distribution)
            : w.flow_duration_distribution;

          bucketKeys.forEach(key => {
            aggregated[key] += dist[key] || 0;
          });
        } catch (e) {
          console.error('Failed to parse flow_duration_distribution:', e);
        }
      }
    });

    const values = bucketKeys.map(key => aggregated[key]);
    const max = Math.max(...values, 1);
    const labels = ["0-5s", "5-10s", "10-20s", "20-30s", "30s+"];
    return { values, max, labels };
  }, [trafficWindows]);

  const packetHistogram = useMemo<HistogramData | null>(() => {
    if (trafficWindows.length === 0) {
      return null;
    }

    // Aggregate packet size distribution across all windows
    const bucketKeys = ["64", "128", "256", "512", "1024", "1500"] as const;
    const aggregated = { "64": 0, "128": 0, "256": 0, "512": 0, "1024": 0, "1500": 0 };

    trafficWindows.forEach(w => {
      if (w.packet_size_distribution) {
        try {
          const dist = typeof w.packet_size_distribution === 'string' 
            ? JSON.parse(w.packet_size_distribution)
            : w.packet_size_distribution;

          bucketKeys.forEach(key => {
            aggregated[key] += dist[key] || 0;
          });
        } catch (e) {
          console.error('Failed to parse packet_size_distribution:', e);
        }
      }
    });

    const values = bucketKeys.map(key => aggregated[key]);
    const max = Math.max(...values, 1);
    const labels = ["<=64B", "<=128B", "<=256B", "<=512B", "<=1024B", ">1024B"];
    return { values, max, labels };
  }, [trafficWindows]);

  const heatmapData = useMemo<number[] | null>(() => {
    if (trafficWindows.length === 0) {
      return null;
    }
    // Map bytes_per_sec to heatmap intensities (normalize to 0-1 range)
    const throughputs = trafficWindows.map(w => w.bytes_per_sec ?? 0);
    const maxThroughput = Math.max(...throughputs, 1);
    return throughputs.map(t => t / maxThroughput);
  }, [trafficWindows]);

  const burstEvents = useMemo(() => {
    if (results.length === 0) {
      return [];
    }
    return results
      .filter((item) => item.is_anomaly)
      .slice(0, 3)
      .map((item, idx) => `Spike at window #${item.window_id ?? idx + 1}`);
  }, [results]);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-zinc-100">Traffic Analysis</h1>
        <p className="text-sm text-zinc-400 mt-1">Behavioral performance and throughput diagnostics</p>
      </div>

      {error && (
        <div className="bg-red-950/40 border border-red-900/40 rounded-lg px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {loading && (
        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg px-4 py-3 text-sm text-zinc-400">
          Loading traffic analytics from latest session...
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">Flow Duration Histogram</h3>
          <p className="text-xs text-zinc-500 mt-1">Short-lived vs long-lived flows</p>
          {flowHistogram ? (
          <div className="mt-4 rounded-lg bg-zinc-950 border border-zinc-800 p-5">
            <div className="relative h-56">
              <div className="absolute left-0 top-0 bottom-8 w-12 flex flex-col justify-between text-[10px] text-zinc-500">
                {[1, 0.75, 0.5, 0.25, 0].map((pct) => (
                  <span key={pct}>{Math.round(flowHistogram.max * pct).toLocaleString()}</span>
                ))}
              </div>
              <div className="absolute -left-2 top-1/2 -translate-y-1/2 -rotate-90 text-[10px] text-zinc-500">
                Count
              </div>
              <div className="ml-14 h-full pb-8 border-l border-b border-zinc-700 relative">
                <div className="absolute inset-0 flex items-end gap-2 px-4 pb-4">
                  {flowHistogram.values.map((value, i) => (
                    <div
                      key={flowHistogram.labels[i]}
                      className="w-4 bg-cyan-400/70 rounded-t group relative cursor-pointer hover:bg-cyan-300 transition-colors"
                      style={{ height: `${Math.min(100, (value / Math.max(flowHistogram.max, 1)) * 100)}%` }}
                    >
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-zinc-900 border border-cyan-500/50 rounded text-[10px] text-zinc-100 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                        <div className="font-semibold">{flowHistogram.labels[i]}</div>
                        <div>{value.toLocaleString()} flows</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="ml-14 mt-3 grid grid-cols-5 text-[9px] text-zinc-500 text-center px-2">
                {flowHistogram.labels.map((label) => (
                  <span key={label}>{label}</span>
                ))}
              </div>
              <div className="ml-14 text-center text-[10px] text-zinc-500">Flow Duration</div>
            </div>
          </div>
          ) : (
          <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
            <p className="text-zinc-500 text-sm">No flow duration data available</p>
            <p className="text-zinc-600 text-xs mt-1">Traffic window metrics required</p>
          </div>
          )}
          <p className="text-xs text-zinc-400 mt-3">
            High variance in flow duration often points to automated scanning or mixed workloads.
          </p>
        </div>

        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">Packet Size Distribution</h3>
          <p className="text-xs text-zinc-500 mt-1">Min / mean / max packet sizes</p>
          {packetHistogram ? (
          <div className="mt-4 rounded-lg bg-zinc-950 border border-zinc-800 p-5">
            <div className="relative h-56">
              <div className="absolute left-0 top-0 bottom-8 w-12 flex flex-col justify-between text-[10px] text-zinc-500">
                {[1, 0.75, 0.5, 0.25, 0].map((pct) => (
                  <span key={pct}>{Math.round(packetHistogram.max * pct).toLocaleString()}</span>
                ))}
              </div>
              <div className="absolute -left-2 top-1/2 -translate-y-1/2 -rotate-90 text-[10px] text-zinc-500">
                Count
              </div>
              <div className="ml-14 h-full pb-8 border-l border-b border-zinc-700 relative">
                <div className="absolute inset-0 flex items-end gap-2 px-4 pb-4">
                  {packetHistogram.values.map((value, i) => (
                    <div
                      key={packetHistogram.labels[i]}
                      className="flex-1 bg-teal-400/70 rounded-t group relative cursor-pointer hover:bg-teal-300 transition-colors"
                      style={{ height: `${Math.min(100, (value / Math.max(packetHistogram.max, 1)) * 100)}%` }}
                    >
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-zinc-900 border border-teal-500/50 rounded text-[10px] text-zinc-100 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                        <div className="font-semibold">{packetHistogram.labels[i]}</div>
                        <div>{value.toLocaleString()} packets</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="ml-14 mt-3 grid grid-cols-5 text-[9px] text-zinc-500 text-center px-2">
                {packetHistogram.labels.map((label) => (
                  <span key={label}>{label}</span>
                ))}
              </div>
              <div className="ml-14 text-center text-[10px] text-zinc-500">Packet Size</div>
            </div>
          </div>
          ) : (
          <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
            <p className="text-zinc-500 text-sm">No packet size data available</p>
            <p className="text-zinc-600 text-xs mt-1">Traffic window metrics required</p>
          </div>
          )}
          <p className="text-xs text-zinc-400 mt-3">
            High variance in packet size often indicates mixed application traffic or tunneling.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        <div className="lg:col-span-3 bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">Throughput Heatmap</h3>
          <p className="text-xs text-zinc-500 mt-1">Time vs volume intensity</p>
          {heatmapData ? (
          <div className="mt-4 rounded-lg bg-zinc-950 border border-zinc-800 p-5">
            <div className="grid grid-cols-24 gap-1">
              {heatmapData.map((intensity, idx) => {
                const hue = 200 - (intensity * 80); // Blue (200) to cyan (120)
                const saturation = 70 + (intensity * 30); // 70% to 100%
                const lightness = 30 + (intensity * 40); // 30% to 70%
                return (
                  <div
                    key={idx}
                    className="aspect-square rounded"
                    style={{
                      backgroundColor: `hsl(${hue}, ${saturation}%, ${lightness}%)`,
                    }}
                    title={`Window ${idx + 1}: ${(intensity * 100).toFixed(1)}% of max throughput`}
                  />
                );
              })}
            </div>
            <div className="mt-3 flex items-center gap-3 text-xs text-zinc-500">
              <span>Low</span>
              <div className="flex-1 h-3 rounded" style={{
                background: 'linear-gradient(to right, hsl(200, 70%, 30%), hsl(180, 85%, 50%), hsl(120, 100%, 70%))'
              }}></div>
              <span>High</span>
            </div>
          </div>
          ) : (
          <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
            <p className="text-zinc-500 text-sm">No throughput heatmap data available</p>
            <p className="text-zinc-600 text-xs mt-1">Traffic window time-series data required</p>
          </div>
          )}
        </div>
      </div>

      <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-zinc-100">Bursty Traffic Detector</h3>
        <p className="text-xs text-zinc-500 mt-1">Automated detection of sudden traffic spikes</p>
        {burstEvents.length > 0 ? (
        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          {burstEvents.map((event) => (
            <div key={event} className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
              <div className="text-sm text-amber-300 font-medium">{event}</div>
              <div className="text-xs text-zinc-400 mt-1">High throughput variance detected</div>
              <div className="mt-3 text-xs text-zinc-500">Why this matters: Sudden spikes often indicate scans or noisy flows.</div>
            </div>
          ))}
        </div>
        ) : (
        <div className="mt-4 rounded-lg border border-zinc-700/50 p-12 text-center">
          <p className="text-zinc-500 text-sm">No burst events detected</p>
          <p className="text-zinc-600 text-xs mt-1">Analyze traffic to detect anomalous spikes</p>
        </div>
        )}
      </div>
    </div>
  );
}
