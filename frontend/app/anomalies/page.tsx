'use client';

import { useMemo } from 'react';
import { useLatestSessionData } from '@/lib/useLatestSessionData';

export default function AnomaliesPage() {
  const { session, results, insights, loading, error } = useLatestSessionData();

  const scoreSeries = useMemo(() => {
    if (results.length > 0) {
      return results.slice(0, 28).map((item) => ({
        value: item.anomaly_score ?? 0,
        isPeak: item.is_anomaly,
      }));
    }

    return [];
  }, [results]);

  const maxScore = scoreSeries.length > 0 ? Math.max(...scoreSeries.map((point) => point.value), 1) : 1;

  const anomalyCards = useMemo(() => {
    const anomalies = results.filter((item) => item.is_anomaly).slice(0, 4);
    if (anomalies.length === 0) {
      return [];
    }

    return anomalies.map((item) => ({
      label: `${item.severity_level ?? 'Anomaly'} window`,
      score: (item.anomaly_score ?? 0).toFixed(2),
      summary: item.anomaly_type ?? 'Behavioral deviation detected.',
    }));
  }, [results]);

  const insightCards = useMemo(() => {
    const alerts = insights.filter((item) => item.insight_type === 'alert').slice(0, 2);
    if (alerts.length > 0) {
      return alerts.map((item) => ({
        title: item.summary,
        detail: item.details ? String(item.details) : 'Review alert details for context.',
      }));
    }

    return [];
  }, [insights]);

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
      <div>
        <h1 className="text-3xl font-bold text-zinc-100">Anomalies & ML Insights</h1>
        <p className="text-sm text-zinc-400 mt-1">Machine-detected unusual behavior and explainability</p>
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
        <div className="mt-4 rounded-lg bg-zinc-950 border border-zinc-800 p-5">
          <div className="relative h-60">
            <div className="absolute left-0 top-0 bottom-8 w-12 flex flex-col justify-between text-[10px] text-zinc-500">
              <span>{maxScore.toFixed(2)}</span>
              <span>{(maxScore * 0.75).toFixed(2)}</span>
              <span>{(maxScore * 0.5).toFixed(2)}</span>
              <span>{(maxScore * 0.25).toFixed(2)}</span>
              <span>0.00</span>
            </div>

            <div className="absolute -left-2 top-1/2 -translate-y-1/2 -rotate-90 text-[10px] text-zinc-500">
              Anomaly Score
            </div>

            <div className="ml-14 h-full pb-8 border-l border-b border-zinc-700 relative">
              <svg className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
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
                      const x = (i / (scoreSeries.length - 1)) * 100;
                      const y = 100 - (point.value / maxScore) * 100;
                      return `${x},${y}`;
                    })
                    .join(' ')}
                  fill="none"
                  stroke="#22d3ee"
                  strokeWidth="2"
                  vectorEffect="non-scaling-stroke"
                />
                {scoreSeries.map((point, i) => {
                  const x = (i / (scoreSeries.length - 1)) * 100;
                  const y = 100 - (point.value / maxScore) * 100;
                  return (
                    <circle
                      key={i}
                      cx={`${x}%`}
                      cy={`${y}%`}
                      r={point.isPeak ? 4 : 2}
                      fill={point.isPeak ? '#ef4444' : '#67e8f9'}
                      stroke="#0b0f13"
                      strokeWidth="1"
                      vectorEffect="non-scaling-stroke"
                    />
                  );
                })}
              </svg>
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-zinc-100">Anomalous Flows</h3>
          <p className="text-xs text-zinc-500 mt-1">Top flagged windows by severity</p>
          {anomalyCards.length > 0 ? (
          <div className="mt-4 space-y-3">
            {anomalyCards.map((card, index) => (
              <div key={`${card.label}-${index}`} className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-200">{card.label}</span>
                  <span className="text-xs text-zinc-500">Score {card.score}</span>
                </div>
                <p className="text-xs text-zinc-400 mt-2">
                  {card.summary}
                </p>
              </div>
            ))}
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
                      className="h-full bg-gradient-to-r from-cyan-500 to-teal-500 rounded-full"
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

      <div className="bg-gradient-to-r from-red-950/30 to-amber-950/30 border border-red-900/30 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-zinc-100">Insights</h3>
        {insightCards.length > 0 ? (
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          {insightCards.map((card, index) => (
            <div key={`${card.title}-${index}`} className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
              <div className="text-sm text-amber-300 font-medium">{card.title}</div>
              <p className="text-xs text-zinc-400 mt-1">{card.detail}</p>
            </div>
          ))}
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
