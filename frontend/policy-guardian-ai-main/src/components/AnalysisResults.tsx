import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, ShieldX, AlertTriangle, AlertOctagon, Search, ChevronDown, ChevronUp, Download, Clock, Zap } from 'lucide-react';
import type { AnalysisResponse, ClauseResult, HiddenCondition } from '@/lib/api';
import { getDownloadUrl } from '@/lib/api';
import { RiskGauge } from './RiskGauge';

interface AnalysisResultsProps {
  result: AnalysisResponse;
}

type TabKey = 'coverage' | 'exclusion' | 'conditions' | 'hidden';

export function AnalysisResults({ result }: AnalysisResultsProps) {
  const [activeTab, setActiveTab] = useState<TabKey>('coverage');
  const [searchQuery, setSearchQuery] = useState('');

  const tabs = [
    { key: 'coverage' as TabKey, label: 'Coverage', count: result.coverage_count, icon: ShieldCheck, color: 'text-coverage' },
    { key: 'exclusion' as TabKey, label: 'Exclusions', count: result.exclusion_count, icon: ShieldX, color: 'text-exclusion' },
    { key: 'conditions' as TabKey, label: 'Conditions', count: result.condition_count, icon: AlertTriangle, color: 'text-condition' },
    { key: 'hidden' as TabKey, label: 'Hidden Risks', count: result.hidden_conditions_total, icon: AlertOctagon, color: 'text-contradiction' },
  ];

  const getClauses = (): ClauseResult[] => {
    let items: ClauseResult[] = [];
    switch (activeTab) {
      case 'coverage': items = result.coverage_clauses; break;
      case 'exclusion': items = result.exclusion_clauses; break;
      case 'conditions': items = result.condition_clauses; break;
      default: return [];
    }
    if (searchQuery) {
      items = items.filter((c) => c.clause_text.toLowerCase().includes(searchQuery.toLowerCase()));
    }
    return items;
  };

  // Generate a summary from available data
  const aiSummary = `This policy presents ${result.risk_level.toUpperCase()} risk (score: ${(result.risk_score * 100).toFixed(0)}%). ` +
    `${result.contradiction_count} contradiction${result.contradiction_count !== 1 ? 's' : ''} detected between coverage and exclusion clauses. ` +
    `${result.hidden_conditions_total} hidden condition${result.hidden_conditions_total !== 1 ? 's' : ''} identified ` +
    `(${result.hidden_high_severity} high, ${result.hidden_medium_severity} medium, ${result.hidden_low_severity} low severity). ` +
    `Risk breakdown — Clause risk: ${(result.risk_breakdown.clause_risk_score * 100).toFixed(0)}%, ` +
    `Contradiction risk: ${(result.risk_breakdown.contradiction_risk_score * 100).toFixed(0)}%, ` +
    `Hidden risk: ${(result.risk_breakdown.hidden_risk_score * 100).toFixed(0)}%.`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Risk Overview + AI Insights */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-card p-6 flex flex-col items-center justify-center">
          <h3 className="text-sm font-semibold text-muted-foreground mb-4 uppercase tracking-wider">Risk Score</h3>
          <RiskGauge score={result.risk_score} level={result.risk_level} />
          <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" /> {result.processing_time_s}s
            </span>
            <span className="flex items-center gap-1">
              <Zap className="h-3 w-3" /> {result.total_clauses} clauses
            </span>
          </div>
        </div>

        <div className="glass-card p-6 flex flex-col">
          <h3 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wider flex items-center gap-2">
            <span className="inline-flex h-5 w-5 items-center justify-center rounded bg-primary/10">
              <AlertOctagon className="h-3 w-3 text-primary" />
            </span>
            AI Insights
          </h3>
          <p className="text-sm text-foreground leading-relaxed flex-1">{aiSummary}</p>

          {/* Risk Breakdown */}
          <div className="mt-4 grid grid-cols-3 gap-3">
            <div className="rounded-lg bg-accent p-3">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Clause Risk</p>
              <p className="text-lg font-bold text-foreground font-mono">{(result.risk_breakdown.clause_risk_score * 100).toFixed(0)}%</p>
            </div>
            <div className="rounded-lg bg-accent p-3">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Contradiction</p>
              <p className="text-lg font-bold text-contradiction font-mono">{(result.risk_breakdown.contradiction_risk_score * 100).toFixed(0)}%</p>
            </div>
            <div className="rounded-lg bg-accent p-3">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Hidden Risk</p>
              <p className="text-lg font-bold text-risk-high font-mono">{(result.risk_breakdown.hidden_risk_score * 100).toFixed(0)}%</p>
            </div>
          </div>

          {/* Download Report */}
          {result.report_txt_url && (
            <a
              href={getDownloadUrl(result.report_txt_url)}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 flex items-center justify-center gap-2 rounded-lg border border-border bg-accent px-4 py-2.5 text-sm font-medium text-foreground hover:bg-surface-hover transition-colors"
            >
              <Download className="h-4 w-4" />
              Download Risk Report
            </a>
          )}
        </div>
      </div>

      {/* Summary Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="glass-card p-4 text-center">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Coverage</p>
          <p className="text-xl font-bold text-coverage">{result.coverage_count}</p>
        </div>
        <div className="glass-card p-4 text-center">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Exclusions</p>
          <p className="text-xl font-bold text-exclusion">{result.exclusion_count}</p>
        </div>
        <div className="glass-card p-4 text-center">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Conditions</p>
          <p className="text-xl font-bold text-condition">{result.condition_count}</p>
        </div>
        <div className="glass-card p-4 text-center">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Contradictions</p>
          <p className="text-xl font-bold text-contradiction">{result.contradiction_count}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="glass-card">
        <div className="flex items-center gap-1 px-4 pt-4 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all whitespace-nowrap ${
                activeTab === tab.key
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent'
              }`}
            >
              <tab.icon className={`h-4 w-4 ${activeTab === tab.key ? tab.color : ''}`} />
              {tab.label}
              <span className={`text-[10px] rounded-full px-1.5 py-0.5 ${
                activeTab === tab.key ? 'bg-primary/20 text-primary' : 'bg-accent text-muted-foreground'
              }`}>
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="px-4 pt-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search clauses..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg bg-accent pl-10 pr-4 py-2 text-sm text-foreground placeholder:text-muted-foreground border-0 focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        {/* Content */}
        <div className="p-4 max-h-[500px] overflow-y-auto">
          <AnimatePresence mode="wait">
            {activeTab === 'hidden' ? (
              <motion.div
                key="hidden"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-3"
              >
                {result.hidden_conditions.length > 0 ? (
                  result.hidden_conditions.map((hc: HiddenCondition, i: number) => (
                    <HiddenConditionCard key={i} condition={hc} index={i} />
                  ))
                ) : (
                  <p className="text-center text-sm text-muted-foreground py-8">No hidden conditions detected.</p>
                )}
              </motion.div>
            ) : (
              <motion.div
                key={activeTab}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-2"
              >
                {getClauses().map((clause: ClauseResult, i: number) => (
                  <ClauseCard key={i} clause={clause} index={i} />
                ))}
                {getClauses().length === 0 && (
                  <p className="text-center text-sm text-muted-foreground py-8">No clauses found.</p>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}

function ClauseCard({ clause, index }: { clause: ClauseResult; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const labelColor = () => {
    switch (clause.label_name) {
      case 'Coverage': return 'bg-coverage/10 text-coverage border-coverage/20';
      case 'Exclusion': return 'bg-exclusion/10 text-exclusion border-exclusion/20';
      case 'Condition': return 'bg-condition/10 text-condition border-condition/20';
      default: return 'bg-muted text-muted-foreground border-border';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      className={`rounded-lg border bg-surface hover:bg-surface-hover transition-colors ${
        clause.is_contradiction ? 'border-contradiction/30' : 'border-border'
      }`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-3 p-3 text-left"
      >
        <div className="flex-1 min-w-0">
          <p className={`text-sm text-foreground ${expanded ? '' : 'line-clamp-2'}`}>
            {clause.clause_text}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {clause.is_contradiction && (
            <span className="inline-flex rounded border border-contradiction/20 bg-contradiction/10 px-1.5 py-0.5 text-[10px] font-semibold text-contradiction">
              ⚠ Contradiction
            </span>
          )}
          <span className={`inline-flex rounded border px-1.5 py-0.5 text-[10px] font-semibold ${labelColor()}`}>
            {clause.label_name}
          </span>
          {expanded ? <ChevronUp className="h-3 w-3 text-muted-foreground" /> : <ChevronDown className="h-3 w-3 text-muted-foreground" />}
        </div>
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 flex flex-wrap gap-4 text-xs text-muted-foreground">
              <span>Confidence: <span className="font-mono text-foreground">{(clause.confidence * 100).toFixed(1)}%</span></span>
              <span>Risk Weight: <span className="font-mono text-foreground">{clause.risk_weight}</span></span>
              <span>Page: <span className="font-mono text-foreground">{clause.page_number}</span></span>
              {clause.section_heading && <span>Section: <span className="text-foreground">{clause.section_heading}</span></span>}
              {clause.is_contradiction && (
                <span>Contradiction Score: <span className="font-mono text-contradiction">{(clause.contradiction_score * 100).toFixed(0)}%</span></span>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function HiddenConditionCard({ condition, index }: { condition: HiddenCondition; index: number }) {
  const severityColor = () => {
    switch (condition.severity) {
      case 'High': return 'bg-risk-high/15 text-risk-high';
      case 'Medium': return 'bg-risk-medium/15 text-risk-medium';
      case 'Low': return 'bg-risk-low/15 text-risk-low';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="rounded-lg border border-contradiction/30 bg-contradiction/5 p-4 space-y-3"
    >
      <div className="flex items-center gap-2 flex-wrap">
        <AlertOctagon className="h-4 w-4 text-contradiction" />
        <span className="text-xs font-semibold text-contradiction">{condition.detection_type}</span>
        <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${severityColor()}`}>
          {condition.severity}
        </span>
        <span className="ml-auto text-xs font-mono text-muted-foreground">
          Contradiction: {(condition.contradiction_score * 100).toFixed(0)}% · Similarity: {(condition.similarity_score * 100).toFixed(0)}%
        </span>
      </div>

      {condition.risk_reason && (
        <p className="text-xs text-foreground bg-accent rounded-lg p-2">
          💡 {condition.risk_reason}
        </p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="rounded-lg border border-coverage/20 bg-coverage/5 p-3">
          <div className="flex items-center gap-1.5 mb-1.5">
            <ShieldCheck className="h-3 w-3 text-coverage" />
            <span className="text-[10px] font-semibold text-coverage uppercase">Coverage</span>
          </div>
          <p className="text-xs text-foreground leading-relaxed">{condition.coverage_text}</p>
        </div>
        <div className="rounded-lg border border-exclusion/20 bg-exclusion/5 p-3">
          <div className="flex items-center gap-1.5 mb-1.5">
            <ShieldX className="h-3 w-3 text-exclusion" />
            <span className="text-[10px] font-semibold text-exclusion uppercase">Exclusion</span>
          </div>
          <p className="text-xs text-foreground leading-relaxed">{condition.exclusion_text}</p>
        </div>
      </div>
    </motion.div>
  );
}
