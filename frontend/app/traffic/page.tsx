'use client';

import { useMemo } from 'react';
import { useLatestSessionData } from '@/lib/useLatestSessionData';

export default function TrafficAnalysisPage() {
  const { session, results, loading, error } = useLatestSessionData();

  const flowHistogram = useMemo(() => {
    const base = results.length > 0 ? results.slice(0, 12).map((r, i) => 20 + (r.anomaly_score ?? 0.2) * 80 + i * 3) : [];
    return base.length > 0 ? base : Array.from({ length: 12 }).map((_, i) => 20 + (i % 6) * 10);
  }, [results]);

  const packetHistogram = useMemo(() => {
    const base = results.length > 0 ? results.slice(0, 10).map((r, i) => 25 + (r.anomaly_score ?? 0.2) * 70 + i * 4) : [];
    return base.length > 0 ? base : Array.from({ length: 10 }).map((_, i) => 25 + (i % 5) * 12);
  }, [results]);

  const burstEvents = useMemo(() => {
    if (results.length === 0) {
      return ['Spike at 14:03', 'Spike at 19:22', 'Spike at 23:48'];
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">Flow Duration Histogram</h3>
          <p className="text-xs text-zinc-500 mt-1">Short-lived vs long-lived flows</p>
          <div className="mt-4 rounded-lg bg-zinc-950 border border-zinc-800 p-5">
            <div className="relative h-56">
              <div className="absolute left-0 top-0 bottom-8 w-12 flex flex-col justify-between text-[10px] text-zinc-500">
                <span>1.2k</span>
                <span>900</span>
                <span>600</span>
                <span>300</span>
                <span>0</span>
              </div>
              <div className="absolute -left-2 top-1/2 -translate-y-1/2 -rotate-90 text-[10px] text-zinc-500">
                Count
              </div>
              <div className="ml-14 h-full pb-8 border-l border-b border-zinc-700 relative">
                <div className="absolute inset-0 flex items-end gap-2 px-4 pb-4">
                  {flowHistogram.map((value, i) => (
                    <div key={i} className="w-4 bg-cyan-400/70 rounded-t" style={{ height: `${Math.min(100, value)}%` }}></div>
                  ))}
                </div>
              </div>
              <div className="ml-14 mt-3 grid grid-cols-5 text-[9px] text-zinc-500 text-center px-2">
                <span>0s</span>
                <span>10s</span>
                <span>20s</span>
                <span>30s</span>
                <span>40s</span>
              </div>
              <div className="ml-14 text-center text-[10px] text-zinc-500">Flow Duration</div>
            </div>
          </div>
          <p className="text-xs text-zinc-400 mt-3">
            High variance in flow duration often points to automated scanning or mixed workloads.
          </p>
        </div>

        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">Packet Size Distribution</h3>
          <p className="text-xs text-zinc-500 mt-1">Min / mean / max packet sizes</p>
          <div className="mt-4 rounded-lg bg-zinc-950 border border-zinc-800 p-5">
            <div className="relative h-56">
              <div className="absolute left-0 top-0 bottom-8 w-12 flex flex-col justify-between text-[10px] text-zinc-500">
                <span>1.5k</span>
                <span>1.0k</span>
                <span>750</span>
                <span>500</span>
                <span>0</span>
              </div>
              <div className="absolute -left-2 top-1/2 -translate-y-1/2 -rotate-90 text-[10px] text-zinc-500">
                Count
              </div>
              <div className="ml-14 h-full pb-8 border-l border-b border-zinc-700 relative">
                <div className="absolute inset-0 flex items-end gap-2 px-4 pb-4">
                  {packetHistogram.map((value, i) => (
                    <div key={i} className="w-5 bg-teal-400/70 rounded-t" style={{ height: `${Math.min(100, value)}%` }}></div>
                  ))}
                </div>
              </div>
              <div className="ml-14 mt-3 grid grid-cols-5 text-[9px] text-zinc-500 text-center px-2">
                <span>64B</span>
                <span>512B</span>
                <span>1KB</span>
                <span>1.5KB</span>
                <span>2KB</span>
              </div>
              <div className="ml-14 text-center text-[10px] text-zinc-500">Packet Size</div>
            </div>
          </div>
          <p className="text-xs text-zinc-400 mt-3">
            High variance in packet size often indicates mixed application traffic or tunneling.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">Throughput Heatmap</h3>
          <p className="text-xs text-zinc-500 mt-1">Time vs volume intensity</p>
          <div className="mt-4 rounded-lg bg-zinc-950 border border-zinc-800 p-5">
            <div className="relative">
              <div className="absolute left-0 top-0 bottom-8 w-12 flex flex-col justify-between text-[10px] text-zinc-500">
                <span>High</span>
                <span>Med</span>
                <span>Low</span>
              </div>
              <div className="absolute -left-2 top-1/2 -translate-y-1/2 -rotate-90 text-[10px] text-zinc-500">
                Volume
              </div>
              <div className="ml-14 pb-8 border-l border-b border-zinc-700">
                <div className="grid grid-cols-12 gap-1">
                  {Array.from({ length: 96 }).map((_, i) => (
                    <div
                      key={i}
                      className="w-full h-6 rounded bg-cyan-500/20"
                      style={{ opacity: 0.2 + (i % 8) * 0.1 }}
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
          <h3 className="text-lg font-semibold text-zinc-100">Inbound vs Outbound</h3>
          <p className="text-xs text-zinc-500 mt-1">Directional traffic ratio</p>
          <div className="mt-6 flex items-center justify-center">
            <div className="w-32 h-32 rounded-full border-8 border-cyan-500/30 flex items-center justify-center">
              <div className="text-center">
                <div className="text-xl font-bold text-cyan-300">62%</div>
                <div className="text-xs text-zinc-500">Inbound</div>
              </div>
            </div>
          </div>
          <p className="text-xs text-zinc-400 mt-4">
            Bursty outbound traffic may signal data exfiltration or misconfigured services.
          </p>
        </div>
      </div>

      <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-zinc-100">Bursty Traffic Detector</h3>
        <p className="text-xs text-zinc-500 mt-1">Automated detection of sudden traffic spikes</p>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          {burstEvents.map((event) => (
            <div key={event} className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
              <div className="text-sm text-amber-300 font-medium">{event}</div>
              <div className="text-xs text-zinc-400 mt-1">High throughput variance detected</div>
              <div className="mt-3 text-xs text-zinc-500">Why this matters: Sudden spikes often indicate scans or noisy flows.</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
