import { createFileRoute } from '@tanstack/react-router';
import { useState } from 'react';
import { motion } from 'framer-motion';
import { useTheme } from '@/lib/theme';

export const Route = createFileRoute('/settings')({
  component: SettingsPage,
  head: () => ({
    meta: [
      { title: 'Settings — Insurance Risk Analyzer AI' },
      { name: 'description', content: 'Configure the AI risk analyzer settings.' },
    ],
  }),
});

function SettingsPage() {
  const { theme, toggle } = useTheme();
  const [similarity, setSimilarity] = useState(0.7);
  const [riskThreshold, setRiskThreshold] = useState(0.5);
  const [model, setModel] = useState('bert-base');

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Configure analysis parameters and preferences</p>
      </div>

      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="glass-card divide-y divide-border">
        {/* Theme */}
        <div className="p-5 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-foreground">Appearance</p>
            <p className="text-xs text-muted-foreground mt-0.5">Toggle between light and dark mode</p>
          </div>
          <button
            onClick={toggle}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              theme === 'dark' ? 'bg-primary' : 'bg-border'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 rounded-full bg-primary-foreground transition-transform ${
                theme === 'dark' ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Model */}
        <div className="p-5">
          <p className="text-sm font-medium text-foreground">NLP Model</p>
          <p className="text-xs text-muted-foreground mt-0.5 mb-3">Select the classification model</p>
          <div className="flex gap-2">
            {['bert-base', 'bert-large', 'roberta'].map((m) => (
              <button
                key={m}
                onClick={() => setModel(m)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  model === m
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-accent text-muted-foreground hover:text-foreground'
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        {/* Similarity Threshold */}
        <div className="p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-sm font-medium text-foreground">Cosine Similarity Threshold</p>
              <p className="text-xs text-muted-foreground mt-0.5">Minimum similarity for contradiction detection</p>
            </div>
            <span className="text-sm font-mono text-foreground">{similarity.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={similarity}
            onChange={(e) => setSimilarity(parseFloat(e.target.value))}
            className="w-full accent-primary"
          />
        </div>

        {/* Risk Threshold */}
        <div className="p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-sm font-medium text-foreground">Risk Level Threshold</p>
              <p className="text-xs text-muted-foreground mt-0.5">Score above this is considered high risk</p>
            </div>
            <span className="text-sm font-mono text-foreground">{riskThreshold.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={riskThreshold}
            onChange={(e) => setRiskThreshold(parseFloat(e.target.value))}
            className="w-full accent-primary"
          />
        </div>
      </motion.div>

      <div className="flex gap-3">
        <button className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors">
          Save Settings
        </button>
        <button className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
          Reset Defaults
        </button>
      </div>
    </div>
  );
}
