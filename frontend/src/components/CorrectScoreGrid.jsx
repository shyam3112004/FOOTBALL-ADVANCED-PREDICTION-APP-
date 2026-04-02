import { useState } from 'react';
import { probToHeatColor, probToColor } from '../utils/colorScale';
import { toPercent, toDecimalOdds } from '../utils/oddsConverter';

const SCORES = [0, 1, 2, 3, 4, 5];
const MEDALS = ['🥇', '🥈', '🥉', '4th', '5th'];

export default function CorrectScoreGrid({ correctScores = [], scoreDraw = {} }) {
  const [activeCell, setActiveCell] = useState(null);

  // Build lookup map: "h-a" → probability
  const probMap = {};
  let maxProb = 0.01;
  correctScores.forEach((s) => {
    probMap[s.score] = s.probability;
    if (s.probability > maxProb) maxProb = s.probability;
  });

  const top5 = correctScores.slice(0, 5);

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Grid */}
      <div>
        {/* Column headers (away goals) */}
        <div className="flex items-center gap-1 mb-1 ml-8">
          <span className="text-[10px] text-text-muted w-5 text-center">↑ Away</span>
          {SCORES.map((a) => (
            <div
              key={a}
              className="flex-1 text-center text-xs font-bold text-text-secondary"
            >
              {a}
            </div>
          ))}
        </div>

        {/* Rows (home goals) */}
        {SCORES.map((h) => (
          <div key={h} className="flex items-center gap-1 mb-1">
            {/* Row label */}
            <div className="w-8 text-center text-xs font-bold text-text-secondary">{h}</div>
            {SCORES.map((a) => {
              const key = `${h}-${a}`;
              const prob = probMap[key] || 0;
              const isActive = activeCell === key;
              const isTop = top5.some((s) => s.score === key);
              return (
                <button
                  key={key}
                  className="score-cell flex-1 p-1 relative"
                  style={{
                    background: isActive
                      ? 'linear-gradient(135deg, #00FF87, #00CC6A)'
                      : probToHeatColor(prob, maxProb),
                    outline: isActive ? '2px solid #00FF87' : 'none',
                    color: isActive || prob > maxProb * 0.6 ? '#fff' : '#9CA3AF',
                  }}
                  onClick={() => setActiveCell(isActive ? null : key)}
                  title={`${key} — ${toPercent(prob)}`}
                >
                  <span className="text-[10px] font-bold block leading-tight">
                    {prob > 0.005 ? toPercent(prob, 0) : ''}
                  </span>
                  {isTop && !isActive && (
                    <span
                      className="absolute top-0 right-0 text-[8px] leading-none"
                      style={{ color: '#FCD34D' }}
                    >
                      ★
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ))}

        {/* Row label axis */}
        <div className="ml-8 mt-0.5">
          <span className="text-[10px] text-text-muted">Home →</span>
        </div>
      </div>

      {/* Active cell tooltip */}
      {activeCell && (
        <div className="flex items-center gap-3 bg-bg-elevated rounded-lg px-3 py-2 border border-accent-green/30 animate-slide-up">
          <span className="font-heading font-bold text-2xl text-accent-green">{activeCell}</span>
          <div>
            <div className="text-xs text-text-secondary">Probability</div>
            <div
              className="font-bold text-sm"
              style={{ color: probToColor(probMap[activeCell] || 0) }}
            >
              {toPercent(probMap[activeCell] || 0)}
            </div>
          </div>
          <div className="ml-auto">
            <div className="text-xs text-text-secondary">Implied Odds</div>
            <div className="odds-badge text-sm">{toDecimalOdds(probMap[activeCell] || 0)}</div>
          </div>
        </div>
      )}

      {/* Top 5 Predicted Scores */}
      <div>
        <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
          Top Predicted Scores
        </h4>
        <div className="space-y-1.5">
          {top5.map((s, i) => (
            <div
              key={s.score}
              className="flex items-center gap-3 bg-bg-elevated rounded-lg px-3 py-2 cursor-pointer hover:border-accent-green/30 border border-transparent transition-colors"
              onClick={() => setActiveCell(s.score === activeCell ? null : s.score)}
            >
              <span className="text-base w-6 text-center">{MEDALS[i] || `${i + 1}th`}</span>
              <span className="font-heading font-bold text-lg text-text-primary flex-1">
                {s.score}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold" style={{ color: probToColor(s.probability) }}>
                  {toPercent(s.probability)}
                </span>
                <span className="odds-badge">{toDecimalOdds(s.probability)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Score Draw Market */}
      {scoreDraw?.probability > 0 && (
        <div className="space-y-2">
          <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-[0.2em] px-1">
            Score Draw Market
          </h4>
          <div className="grid grid-cols-2 gap-3">
            {/* YES */}
            <div className="bg-bg-elevated border border-accent-blue/30 rounded-xl p-3 relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-1">
                <div className="w-1.5 h-1.5 rounded-full bg-accent-blue shadow-[0_0_8px_rgba(59,130,246,0.6)]" />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-black text-accent-blue uppercase tracking-widest">YES (Score Draw)</span>
                <div className="flex items-end justify-between">
                  <span className="text-xl font-black text-text-primary">
                    {toPercent(scoreDraw.probability)}
                  </span>
                  <span className="odds-badge bg-accent-blue/10 text-accent-blue border-accent-blue/20">
                    {toDecimalOdds(scoreDraw.probability)}
                  </span>
                </div>
              </div>
              <div className="mt-2 text-[9px] text-text-muted italic border-t border-accent-blue/10 pt-1.5">
                {(scoreDraw.likely_scores || []).join(' · ')}
              </div>
            </div>

            {/* NO */}
            <div className="bg-bg-elevated border border-gray-700/50 rounded-xl p-3 relative overflow-hidden flex flex-col justify-center">
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-black text-text-muted uppercase tracking-widest">NO (Any Other)</span>
                <div className="flex items-end justify-between">
                  <span className="text-xl font-black text-text-primary">
                    {toPercent(1 - scoreDraw.probability)}
                  </span>
                  <span className="odds-badge">
                    {toDecimalOdds(1 - scoreDraw.probability)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
