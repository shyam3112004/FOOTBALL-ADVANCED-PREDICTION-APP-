import React, { useState, useMemo } from 'react';
import usePredictionStore from '../store/predictionStore';
import { 
  Download, Filter, ChevronDown, ChevronUp, AlertCircle, 
  TrendingUp, TrendingDown, Minus, ArrowRight, Expand, Shrink, 
  Trophy, Target, Zap, Loader2
} from 'lucide-react';
import { toPercent } from '../utils/oddsConverter';
import { probToColor } from '../utils/colorScale';

// Format date for display: "Apr 04" or "04/04/2026"
function formatDateShort(dateStr) {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
  } catch {
    return dateStr;
  }
}

export default function BatchResultsTable({ results, onExport, loading, exporting }) {
  const { 
    batchMinProb: minProb, setBatchMinProb: setMinProb,
    batchTargetMarket: targetMarket, setBatchTargetMarket: setTargetMarket 
  } = usePredictionStore();

  const [sortField, setSortField] = useState('home_prob');
  const [sortDir, setSortDir] = useState('desc');
  const [filter, setFilter] = useState('all'); // all, home, draw, away
  const [expandedId, setExpandedId] = useState(null);

  const getFavored = (mr) => {
    if (!mr) return 'none';
    const max = Math.max(mr.home, mr.draw, mr.away);
    if (max === mr.home) return 'home';
    if (max === mr.draw) return 'draw';
    return 'away';
  };

  const sortedResults = useMemo(() => {
    return [...results]
      .filter(r => {
        if (!r.success) return true; // Keep errors visible
        
        // 1. Basic Outcome Filter (existing)
        if (filter !== 'all' && getFavored(r.match_result) !== filter) return false;

        // 2. Smart Probability Filter
        const probThreshold = minProb / 100;
        const mr = r.match_result || {};
        const dc = r.double_chance || {};
        const btts = r.btts || {};
        const ou = r.total_goals?.over_under || {};

        if (targetMarket === 'any') {
           const maxVal = Math.max(
             mr.home || 0, mr.draw || 0, mr.away || 0,
             dc['1X'] || 0, dc['12'] || 0, dc['X2'] || 0,
             btts.yes || 0, ou.over_2_5 || 0
           );
           if (maxVal < probThreshold) return false;
        } else if (targetMarket === 'home') {
          if ((mr.home || 0) < probThreshold) return false;
        } else if (targetMarket === 'draw') {
          if ((mr.draw || 0) < probThreshold) return false;
        } else if (targetMarket === 'away') {
          if ((mr.away || 0) < probThreshold) return false;
        } else if (targetMarket === 'double_chance') {
          const maxDC = Math.max(dc['1X'] || 0, dc['12'] || 0, dc['X2'] || 0);
          if (maxDC < probThreshold) return false;
        } else if (targetMarket === 'btts') {
          if ((btts.yes || 0) < probThreshold) return false;
        } else if (targetMarket === 'over25') {
          if ((ou.over_2_5 || 0) < probThreshold) return false;
        }

        return true;
      })
      .sort((a, b) => {
        const valA = a.match_result?.[sortField.replace('_prob', '')] || 0;
        const valB = b.match_result?.[sortField.replace('_prob', '')] || 0;
        return sortDir === 'desc' ? valB - valA : valA - valB;
      });
  }, [results, sortField, sortDir, filter, minProb, targetMarket]);

  const summary = useMemo(() => {
    const counts = { home: 0, draw: 0, away: 0, failed: 0 };
    results.forEach(r => {
      if (!r.success) counts.failed++;
      else counts[getFavored(r.match_result)]++;
    });
    return counts;
  }, [results]);

  if (loading && results.length === 0) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-20 bg-bg-elevated rounded-2xl border border-[#2D3748]" />
        <div className="h-[400px] bg-bg-elevated rounded-2xl border border-[#2D3748]" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Summary Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Home Wins', count: summary.home, color: 'text-accent-green', bg: 'bg-accent-green/10' },
          { label: 'Draws Likely', count: summary.draw, color: 'text-warning', bg: 'bg-warning/10' },
          { label: 'Away Wins', count: summary.away, color: 'text-accent-blue', bg: 'bg-accent-blue/10' },
          { label: 'Failed/Errors', count: summary.failed, color: 'text-danger', bg: 'bg-danger/10' },
        ].map(item => (
          <div key={item.label} className={`flex items-center justify-between p-4 rounded-2xl border border-[#2D3748] ${item.bg}`}>
            <div>
              <div className="text-[10px] font-bold text-text-muted uppercase tracking-widest">{item.label}</div>
              <div className={`text-2xl font-black ${item.color}`}>{item.count}</div>
            </div>
            <ActivityIcon label={item.label} />
          </div>
        ))}
      </div>

      {/* Table Interface */}
      <div className="bg-bg-elevated rounded-2xl border border-[#2D3748] shadow-2xl overflow-hidden">
        <div className="p-4 border-b border-[#2D3748] flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
             <div className="bg-accent-green/20 p-2 rounded-lg">
                <Target className="w-5 h-5 text-accent-green" />
             </div>
             <div>
                <h3 className="font-heading font-black text-lg text-text-primary">Batch Analysis</h3>
                <p className="text-[10px] text-text-muted tracking-widest uppercase">Sort & Filter results</p>
             </div>
          </div>
          
          <div className="flex items-center justify-end gap-3 flex-1 sm:flex-none">
            {/* Filter Toggle */}
            <div className="flex bg-bg-primary p-1 rounded-xl border border-[#2D3748]">
              {['all', 'home', 'draw', 'away'].map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all ${
                    filter === f ? 'bg-bg-elevated text-accent-green shadow-sm' : 'text-text-muted hover:text-text-secondary'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
            
            {/* NEW: Smart Filters */}
            <div className="flex items-center gap-2 bg-bg-primary p-1 rounded-xl border border-[#2D3748]">
              <select 
                value={targetMarket}
                onChange={(e) => setTargetMarket(e.target.value)}
                className="bg-transparent text-[10px] font-bold text-accent-green uppercase outline-none px-2 py-1 cursor-pointer"
              >
                <option value="any">Any Market</option>
                <option value="home">Home Win</option>
                <option value="draw">Draw</option>
                <option value="away">Away Win</option>
                <option value="double_chance">Double Chance</option>
                <option value="btts">BTTS Yes</option>
                <option value="over25">Over 2.5</option>
              </select>
              <div className="w-px h-4 bg-[#2D3748]" />
              <div className="flex items-center gap-1.5 px-2">
                <span className="text-[9px] text-text-muted font-bold">MIN</span>
                <input 
                  type="number"
                  min="0"
                  max="100"
                  value={minProb}
                  onChange={(e) => setMinProb(Number(e.target.value))}
                  className="w-8 bg-transparent text-[10px] font-bold text-accent-green outline-none text-center"
                />
                <span className="text-[10px] font-bold text-accent-green">%</span>
              </div>
            </div>

            <button
              onClick={() => onExport({ minProb: minProb / 100, market: targetMarket })}
              disabled={exporting || results.length === 0}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-heading font-bold transition-all ${
                exporting 
                  ? 'bg-bg-primary text-text-muted cursor-wait border border-[#2D3748]' 
                  : (minProb >= 70 ? 'bg-accent-green text-bg-primary animate-glow shadow-[0_0_15px_rgba(0,255,135,0.2)]' : 'bg-accent-blue text-bg-primary')
              } hover:scale-[1.02]`}
            >
              {exporting ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> EXPORTING...</>
              ) : (
                <><Download className="w-4 h-4" /> {minProb > 0 || targetMarket !== 'any' ? 'EXPORT FILTERED' : 'EXPORT ALL'}</>
              )}
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-bg-primary/50 text-[10px] font-bold text-text-muted uppercase tracking-widest">
                <th className="px-3 py-4">Date</th>
                <th className="px-3 py-4">League</th>
                <th className="px-6 py-4">Match</th>
                <th className="px-4 py-4 cursor-pointer hover:text-text-primary" onClick={() => setSortField('home_prob')}>Home Win</th>
                <th className="px-4 py-4 cursor-pointer hover:text-text-primary" onClick={() => setSortField('draw_prob')}>Draw</th>
                <th className="px-4 py-4 cursor-pointer hover:text-text-primary" onClick={() => setSortField('away_prob')}>Away Win</th>
                <th className="px-4 py-4">BTTS</th>
                <th className="px-4 py-4">O2.5</th>
                <th className="px-4 py-4">Top Score</th>
                <th className="px-6 py-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#2D3748]">
              {sortedResults.map((r, i) => (
                <ResultRow 
                  key={r.prediction_id || i}
                  row={r} 
                  isExpanded={expandedId === r.prediction_id}
                  onToggle={() => setExpandedId(expandedId === r.prediction_id ? null : r.prediction_id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ResultRow({ row, isExpanded, onToggle }) {
  if (!row.success) {
    return (
      <tr className="bg-danger/5">
        <td className="px-3 py-4 text-[10px] text-text-muted font-mono">{formatDateShort(row.match_date)}</td>
        <td className="px-3 py-4">
          <span className="text-[9px] bg-accent-blue/10 text-accent-blue px-1.5 py-0.5 rounded font-semibold">
            {row.competition_code || '—'}
          </span>
        </td>
        <td className="px-6 py-4">
          <div className="flex items-center gap-3">
             <AlertCircle className="w-4 h-4 text-danger" />
             <div className="text-sm font-bold text-text-primary line-through opacity-50">{row.home_team} vs {row.away_team}</div>
          </div>
        </td>
        <td colSpan="7" className="px-4 py-4">
           <div className="text-xs text-danger font-medium italic">Prediction error: {row.error}</div>
        </td>
      </tr>
    );
  }

  const mr = row.match_result || {};
  const ou = row.total_goals?.over_under || {};
  const topScore = row.correct_scores?.[0] || {};

  return (
    <>
      <tr 
        onClick={onToggle}
        className={`group transition-all cursor-pointer ${isExpanded ? 'bg-accent-green/5' : 'hover:bg-bg-primary/40'}`}
      >
        <td className="px-3 py-4">
          <div className="text-[10px] font-mono text-text-muted whitespace-nowrap">{formatDateShort(row.match_date)}</div>
        </td>
        <td className="px-3 py-4">
          <span className="text-[9px] bg-accent-blue/10 text-accent-blue px-1.5 py-0.5 rounded font-semibold whitespace-nowrap">
            {row.competition_code || '—'}
          </span>
        </td>
        <td className="px-6 py-4">
          <div className="flex flex-col">
            <div className={`text-sm font-bold tracking-tight transition-colors ${isExpanded ? 'text-accent-green' : 'text-text-primary'}`}>
              {row.home_team} <span className="opacity-40 font-normal">v</span> {row.away_team}
            </div>
            <div className="text-[10px] text-text-muted mt-0.5">Confidence: {(row.model_confidence * 100).toFixed(0)}%</div>
          </div>
        </td>
        <td className="px-4 py-4">
           <ProbBadge prob={mr.home} />
        </td>
        <td className="px-4 py-4">
           <ProbBadge prob={mr.draw} />
        </td>
        <td className="px-4 py-4">
           <ProbBadge prob={mr.away} />
        </td>
        <td className="px-4 py-4">
           <div className="text-xs font-mono text-text-secondary">{toPercent(row.btts?.yes)}</div>
        </td>
        <td className="px-4 py-4">
           <div className="text-xs font-mono text-text-secondary">{toPercent(ou.over_2_5)}</div>
        </td>
        <td className="px-4 py-4">
           <div className="flex flex-col">
             <span className="text-xs font-bold text-text-primary">{topScore.score}</span>
             <span className="text-[9px] text-text-muted">{(topScore.probability * 100).toFixed(1)}%</span>
           </div>
        </td>
        <td className="px-6 py-4 text-right">
           <div className={`inline-flex p-1.5 rounded-lg border border-[#2D3748] transition-all ${isExpanded ? 'bg-accent-green text-bg-primary border-accent-green' : 'bg-bg-primary text-text-muted group-hover:text-text-primary'}`}>
             {isExpanded ? <Shrink className="w-4 h-4" /> : <Expand className="w-4 h-4" />}
           </div>
        </td>
      </tr>
      
      {/* Expanded Mini Dashboard */}
      {isExpanded && (
        <tr>
          <td colSpan="10" className="px-6 py-4 bg-bg-primary/30 border-l border-r border-accent-green/20">
             <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-slide-up">
                {/* 1X2 Probabilities */}
                <div className="space-y-3">
                   <div className="text-[10px] font-bold text-text-muted uppercase tracking-widest flex items-center gap-1.5">
                      <Zap className="w-3 h-3 text-accent-green" /> Win Probabilities
                   </div>
                   <div className="space-y-4">
                      <ProbMiniBar label="Home" prob={mr.home} color="var(--accent-green)" />
                      <ProbMiniBar label="Draw" prob={mr.draw} color="var(--color-warning)" />
                      <ProbMiniBar label="Away" prob={mr.away} color="var(--accent-blue)" />
                   </div>
                </div>
                
                {/* Goals Forecast */}
                <div className="space-y-3">
                   <div className="text-[10px] font-bold text-text-muted uppercase tracking-widest flex items-center gap-1.5">
                      <Target className="w-3 h-3 text-accent-blue" /> Goals Analysis
                   </div>
                   <div className="grid grid-cols-2 gap-3">
                      <div className="bg-bg-elevated p-3 rounded-xl border border-[#2D3748]">
                         <div className="text-[9px] text-text-muted uppercase mb-1">Avg Total Goals</div>
                         <div className="text-xl font-heading font-black text-accent-green">{row.total_goals?.predicted?.toFixed(2)}</div>
                      </div>
                      <div className="bg-bg-elevated p-3 rounded-xl border border-[#2D3748]">
                         <div className="text-[9px] text-text-muted uppercase mb-1">BTTS Probability</div>
                         <div className="text-xl font-heading font-black text-accent-blue">{toPercent(row.btts?.yes)}</div>
                      </div>
                   </div>
                   <div className="space-y-2 mt-2">
                       <div className="flex justify-between text-[10px] text-text-muted mb-1 px-1">
                          <span>OVER 1.5</span>
                          <span>{(ou.over_1_5 * 100).toFixed(0)}%</span>
                       </div>
                       <div className="h-1 bg-bg-elevated rounded-full overflow-hidden">
                          <div className="h-full bg-accent-green/60" style={{ width: `${ou.over_1_5 * 100}%` }} />
                       </div>
                   </div>
                </div>

                {/* Score list */}
                <div className="space-y-3">
                   <div className="text-[10px] font-bold text-text-muted uppercase tracking-widest flex items-center gap-1.5">
                      <Trophy className="w-3 h-3 text-warning" /> Top Scorelines
                   </div>
                   <div className="grid grid-cols-2 gap-2">
                      {row.correct_scores?.slice(0, 4).map((score, idx) => (
                        <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-bg-elevated border border-[#2D3748]">
                           <span className="text-xs font-bold text-text-primary">{score.score}</span>
                           <span className="text-[10px] font-mono text-accent-green">{(score.probability * 100).toFixed(1)}%</span>
                        </div>
                      ))}
                   </div>
                </div>
             </div>
          </td>
        </tr>
      )}
    </>
  );
}

function ProbBadge({ prob }) {
  const color = probToColor(prob);
  return (
    <div 
      className="inline-flex flex-col min-w-[50px] px-2 py-1 rounded-lg border border-[#2D3748] items-center"
      style={{ background: `${color}15` }}
    >
       <span className="text-xs font-bold font-mono" style={{ color }}>{toPercent(prob)}</span>
       <span className="text-[8px] text-text-muted uppercase mt-0.5">Prob</span>
    </div>
  );
}

function ProbMiniBar({ label, prob, color }) {
  return (
    <div>
       <div className="flex justify-between text-[10px] text-text-secondary uppercase mb-1 font-bold">
          <span>{label}</span>
          <span style={{ color }}>{(prob * 100).toFixed(1)}%</span>
       </div>
       <div className="h-1.5 w-full bg-bg-elevated rounded-full overflow-hidden">
          <div 
             className="h-full rounded-full transition-all duration-700" 
             style={{ width: `${prob * 100}%`, backgroundColor: color }} 
          />
       </div>
    </div>
  );
}

function ActivityIcon({ label }) {
  if (label.includes('Home')) return <TrendingUp className="w-5 h-5 text-accent-green opacity-40 shrink-0" />;
  if (label.includes('Away')) return <TrendingDown className="w-5 h-5 text-accent-blue opacity-40 shrink-0" />;
  if (label.includes('Failed')) return <AlertCircle className="w-5 h-5 text-danger opacity-40 shrink-0" />;
  return <Minus className="w-5 h-5 text-warning opacity-40 shrink-0" />;
}
