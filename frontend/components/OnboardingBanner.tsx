'use client';

import { useState, useEffect } from 'react';

const STORAGE_KEY = 'snta_onboarding_dismissed';

export default function OnboardingBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const dismissed = localStorage.getItem(STORAGE_KEY);
    if (!dismissed) {
      setVisible(true);
    }
  }, []);

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, 'true');
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="mb-6 bg-linear-to-r from-cyan-950/40 to-blue-950/40 border border-cyan-800/50 rounded-xl p-6 relative">
      <button
        onClick={dismiss}
        className="absolute top-3 right-3 text-zinc-500 hover:text-zinc-300 transition-colors text-lg leading-none"
        aria-label="Dismiss"
      >
        ✕
      </button>

      <h2 className="text-lg font-bold text-cyan-200 mb-2">Welcome to the Smart Network Traffic Analyzer</h2>
      <p className="text-sm text-zinc-300 mb-4 max-w-3xl">
        Upload a PCAP file to get started. The system will automatically extract features, run ML anomaly detection, and present interactive visualisations of your network traffic.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
        <div className="bg-zinc-900/60 rounded-lg p-3 border border-zinc-800">
          <span className="text-cyan-400 font-semibold block mb-1">1. Upload</span>
          <span className="text-zinc-400">Drag & drop a .pcap / .pcapng file</span>
        </div>
        <div className="bg-zinc-900/60 rounded-lg p-3 border border-zinc-800">
          <span className="text-cyan-400 font-semibold block mb-1">2. Analyse</span>
          <span className="text-zinc-400">ML models detect anomalies automatically</span>
        </div>
        <div className="bg-zinc-900/60 rounded-lg p-3 border border-zinc-800">
          <span className="text-cyan-400 font-semibold block mb-1">3. Explore</span>
          <span className="text-zinc-400">Use filters, timeline & protocol views</span>
        </div>
        <div className="bg-zinc-900/60 rounded-lg p-3 border border-zinc-800">
          <span className="text-cyan-400 font-semibold block mb-1">4. Export</span>
          <span className="text-zinc-400">Download anomaly & flow data as CSV</span>
        </div>
      </div>

      <p className="text-[10px] text-zinc-600 mt-3">
        Toggle Beginner Mode on any dashboard page for plain-language explanations. This banner won&apos;t appear again after dismissal.
      </p>
    </div>
  );
}
