import { useState, useRef, useEffect } from 'react';
import { Search, Target, Star } from 'lucide-react';
import { probToColor, positionToClass } from '../utils/colorScale';
import { toPercent, toDecimalOdds } from '../utils/oddsConverter';

const SCORER_BADGES = [
  { threshold: 0.6, label: 'Hot 🔥', class: 'badge-high' },
  { threshold: 0.4, label: 'Likely', class: 'badge-medium' },
  { threshold: 0.2, label: 'Possible', class: 'badge-low' },
  { threshold: 0,   label: 'Unlikely', class: 'confidence-badge bg-bg-elevated text-text-muted' },
];

function ScorerBadge({ prob }) {
  const badge = SCORER_BADGES.find((b) => prob >= b.threshold);
  return <span className={`confidence-badge ${badge.class}`}>{badge.label}</span>;
}

export default function PlayerScorerList({ playerScorers = [] }) {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');

  const filtered = playerScorers.filter((p) => {
    const matchSearch = p.name.toLowerCase().includes(search.toLowerCase());
    const matchFilter =
      filter === 'all' ? true :
      filter === 'home' ? p.team === 'home' :
      filter === 'away' ? p.team === 'away' :
      filter === 'hot' ? p.probability >= 0.4 : true;
    return matchSearch && matchFilter;
  });

  if (playerScorers.length === 0) {
    return (
      <div className="text-center text-text-muted text-sm py-8">
        <Target className="w-8 h-8 mx-auto mb-2 opacity-30" />
        Add player lineups to see scorer predictions
      </div>
    );
  }

  return (
    <div className="space-y-3 animate-fade-in">
      {/* Controls */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-36">
          <Search className="absolute left-2.5 top-2 w-3.5 h-3.5 text-text-muted" />
          <input
            type="text"
            placeholder="Search player..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-bg-elevated border border-[#2D3748] rounded-lg pl-8 pr-3 py-1.5 text-xs text-text-primary placeholder-text-muted outline-none focus:border-accent-green/50"
          />
        </div>
        <div className="flex gap-1">
          {['all', 'home', 'away', 'hot'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold capitalize transition-colors ${
                filter === f
                  ? 'bg-accent-green text-bg-primary'
                  : 'bg-bg-elevated text-text-secondary hover:text-text-primary'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Player list */}
      <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
        {filtered.length === 0 && (
          <div className="text-center text-text-muted text-xs py-4">No players match filter</div>
        )}
        {filtered.map((p, i) => (
          <div
            key={p.player_id || `${p.name}-${i}`}
            className="flex items-center gap-3 bg-bg-elevated rounded-lg px-3 py-2.5 border border-transparent hover:border-accent-green/20 transition-all"
          >
            {/* Rank */}
            <div className="text-xs font-bold text-text-muted w-5 text-center">
              {playerScorers.indexOf(p) + 1}
            </div>

            {/* Jersey */}
            <div className="w-7 h-7 rounded-full bg-[#1F2937] flex items-center justify-center text-xs font-bold text-text-secondary border border-[#2D3748] shrink-0">
              {p.jersey_no || '—'}
            </div>

            {/* Name & position */}
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-text-primary truncate">{p.name}</div>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className={`confidence-badge text-[10px] ${positionToClass(p.position)}`}>
                  {p.position}
                </span>
                <span className="text-[10px] text-text-muted capitalize">{p.team}</span>
                <span className="text-[10px] text-text-muted">
                  {p.goals_season}G · xG {p.xg_per90?.toFixed(2)}/90
                </span>
              </div>
            </div>

            {/* Probability bar */}
            <div className="w-24 shrink-0">
              <div className="flex items-center justify-between text-[10px] mb-0.5">
                <span className="font-bold" style={{ color: probToColor(p.probability) }}>
                  {toPercent(p.probability)}
                </span>
                <span className="text-text-muted font-mono">{toDecimalOdds(p.probability)}</span>
              </div>
              <div className="prob-bar-track h-1.5">
                <div
                  className="prob-bar-fill prob-high transition-all duration-700"
                  style={{
                    width: `${(p.probability * 100).toFixed(1)}%`,
                    background: probToColor(p.probability),
                  }}
                />
              </div>
            </div>

            {/* Badge */}
            <div className="shrink-0">
              <ScorerBadge prob={p.probability} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
