import { useState } from 'react';
import { PredictionCard, ProbBar, PredictionCardSkeleton } from '../components/PredictionCard';
import CorrectScoreGrid from '../components/CorrectScoreGrid';
import GoalIntervalChart from '../components/GoalIntervalChart';
import PlayerScorerList from '../components/PlayerScorerList';
import ErrorBoundary from '../components/ErrorBoundary';
import { toPercent, toDecimalOdds } from '../utils/oddsConverter';
import { probToColor } from '../utils/colorScale';
import { useLiveFeed } from '../hooks/useLiveFeed';
import { normalizeTeamName } from '../utils/dateUtils';
import { Activity, Zap, Target, TrendingUp, BarChart2, Star } from 'lucide-react';

const TABS = [
  { id: 'result',   label: 'Match Result' },
  { id: 'goals',    label: 'Goals' },
  { id: 'score',    label: 'Score' },
  { id: 'specials', label: 'Specials' },
  { id: 'scorers',  label: 'Scorers' },
  { id: 'live',     label: 'Live Centre' },
];

function EmptyState() {
  return (
    <div className="h-full flex flex-col items-center justify-center text-center py-16 space-y-6 animate-fade-in">
      <div className="relative">
        <div className="text-7xl opacity-10 select-none">⚽</div>
        <div className="absolute inset-0 animate-ping-slow opacity-5 text-7xl select-none">⚽</div>
      </div>
      <div className="space-y-2">
        <h3 className="font-heading font-bold text-2xl text-text-secondary">
          Ready to Predict?
        </h3>
        <p className="text-sm text-text-muted max-w-xs mx-auto leading-relaxed">
          Select a league and match above, then press{' '}
          <span className="text-accent-green font-semibold">Run Predictions</span>{' '}
          to generate AI-powered odds across 10+ markets.
        </p>
      </div>
      {/* Feature pills */}
      <div className="flex flex-wrap gap-2 justify-center max-w-xs">
        {['1X2 Odds', 'Correct Score', 'BTTS', 'Over/Under', 'Goal Intervals', 'Player Scorers'].map(feat => (
          <span key={feat}
            className="text-[10px] px-2 py-1 rounded-full bg-bg-elevated
                       border border-[#2D3748] text-text-muted">
            {feat}
          </span>
        ))}
      </div>
    </div>
  );
}

function MatchResultTab({ data }) {
  const mr = data.match_result || {};
  const dc = data.double_chance || {};
  const conf = data.model_confidence || 0;

  return (
    <div className="space-y-4 animate-slide-up">
      <PredictionCard title="1×2 — Match Result" confidence={conf}>
        <div className="space-y-3">
          {[
            { label: 'Home Win (1)', prob: mr.home },
            { label: 'Draw (X)',     prob: mr.draw },
            { label: 'Away Win (2)', prob: mr.away },
          ].map(({ label, prob }) => (
            <ProbBar key={label} label={label} prob={prob} />
          ))}
        </div>
      </PredictionCard>

      <PredictionCard title="Double Chance">
        <div className="space-y-3">
          {[
            { label: '1X — Home or Draw',  prob: dc['1X'] },
            { label: '12 — Home or Away',  prob: dc['12'] },
            { label: 'X2 — Draw or Away',  prob: dc['X2'] },
          ].map(({ label, prob }) => (
            <ProbBar key={label} label={label} prob={prob} />
          ))}
        </div>
      </PredictionCard>
    </div>
  );
}

function GoalsTab({ data }) {
  const btts = data.btts || {};
  const tg = data.total_goals || {};
  const ou = tg.over_under || {};
  const conf = data.model_confidence || 0;

  const ouRows = [
    { label: 'Over 0.5',  over: ou.over_0_5,  under: ou.under_0_5 },
    { label: 'Over 1.5',  over: ou.over_1_5,  under: ou.under_1_5 },
    { label: 'Over 2.5',  over: ou.over_2_5,  under: ou.under_2_5 },
    { label: 'Over 3.5',  over: ou.over_3_5,  under: ou.under_3_5 },
    { label: 'Over 4.5',  over: ou.over_4_5,  under: ou.under_4_5 },
  ];

  return (
    <div className="space-y-4 animate-slide-up">
      <PredictionCard title="Both Teams To Score" confidence={conf}>
        <div className="space-y-3">
          <ProbBar label="Yes — BTTS" prob={btts.yes} />
          <ProbBar label="No — BTTS" prob={btts.no} />
        </div>
      </PredictionCard>

      <PredictionCard title="Total Goals Prediction">
        <div className="grid grid-cols-3 gap-2 mb-4">
          {[
            { label: 'Total', val: tg.predicted },
            { label: 'Home',  val: tg.home_predicted },
            { label: 'Away',  val: tg.away_predicted },
          ].map(({ label, val }) => (
            <div key={label} className="bg-bg-elevated rounded-lg p-2 text-center">
              <div className="text-xs text-text-muted">{label}</div>
              <div className="font-heading font-bold text-xl text-accent-green">
                {val?.toFixed(2) ?? '—'}
              </div>
            </div>
          ))}
        </div>
        <div className="space-y-2">
          {ouRows.map(({ label, over, under }) => (
            <div key={label} className="flex items-center gap-2">
              <span className="text-xs text-text-muted w-16">{label}</span>
              <div className="flex-1 space-y-0.5">
                <ProbBar label={`Over · ${toPercent(over)}`} prob={over} />
              </div>
            </div>
          ))}
        </div>
      </PredictionCard>
    </div>
  );
}

function ScoreTab({ data }) {
  return (
    <div className="animate-slide-up">
      <PredictionCard title="Correct Score Predictions">
        <CorrectScoreGrid
          correctScores={data.correct_scores || []}
          scoreDraw={data.score_draw || {}}
        />
      </PredictionCard>
    </div>
  );
}

function SpecialsTab({ data }) {
  const eo  = data.total_even_odd || {};
  const gbh = data.goal_both_halves || {};
  const gi  = data.goal_interval || {};
  const conf = data.model_confidence || 0;

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="grid grid-cols-2 gap-4">
        <PredictionCard title="Total Even / Odd" confidence={conf}>
          <div className="space-y-3">
            <ProbBar label="Even Goals" prob={eo.even} />
            <ProbBar label="Odd Goals"  prob={eo.odd} />
          </div>
        </PredictionCard>

        <PredictionCard title="Goal Both Halves">
          <div className="space-y-3">
            <ProbBar label="Yes" prob={gbh.yes} />
            <ProbBar label="No"  prob={gbh.no} />
          </div>
        </PredictionCard>
      </div>

      <PredictionCard title="Goal Interval Probability">
        <GoalIntervalChart goalInterval={gi} />
      </PredictionCard>
    </div>
  );
}

function ScorersTab({ data }) {
  return (
    <div className="animate-slide-up">
      <PredictionCard title="Player Scoring Probability">
        <PlayerScorerList playerScorers={data.player_scorers || []} />
      </PredictionCard>
    </div>
  );
}

function LiveTab({ matchId, homeTeam, awayTeam, activeTab }) {
  const { liveMatches, matchStats, loading, lastUpdated } = useLiveFeed(matchId, activeTab);

  // Search for the match by ID or fuzzy name match
  const activeLiveMatch = liveMatches.find(m => {
     if (matchId && m.fixture.id === matchId) return true;
     const h = normalizeTeamName(homeTeam);
     const a = normalizeTeamName(awayTeam);
     const mh = normalizeTeamName(m.teams.home.name);
     const ma = normalizeTeamName(m.teams.away.name);
     return (mh.includes(h) || h.includes(mh)) && (ma.includes(a) || a.includes(ma));
  });

  // Extract real xG from matchStats (Sportmonks structure)
  const extractXG = () => {
    if (!matchStats?.statistics) return { home: 0, away: 0 };
    const stats = matchStats.statistics;
    const homeXG = stats.find(s => s.type?.code === 'expected_goals' && s.participant_id === matchStats.participants?.[0]?.id)?.value || 0;
    const awayXG = stats.find(s => s.type?.code === 'expected_goals' && s.participant_id === matchStats.participants?.[1]?.id)?.value || 0;
    return { home: homeXG, away: awayXG };
  };

  const xg = extractXG();
  const hasXG = xg.home > 0 || xg.away > 0;

  return (
    <div className="space-y-4 animate-slide-up">
      <PredictionCard title="Real-time Match Centre">
        {!activeLiveMatch ? (
           <div className="text-center py-12 text-text-muted">
             <Activity className="w-10 h-10 mx-auto mb-2 opacity-20" />
             <p className="text-sm font-semibold">Match is not currently live</p>
             <p className="text-[10px] mt-1 opacity-60">Scanning for {homeTeam} vs {awayTeam}...</p>
           </div>
        ) : (
          <div className="space-y-6">
             {/* Score / Time */}
             <div className="flex items-center justify-between bg-bg-primary rounded-xl p-4 border border-[#2D3748]">
                <div className="flex-1 text-center">
                   <div className="text-2xl font-black text-text-primary">{activeLiveMatch.goals.home}</div>
                   <div className="text-[10px] text-text-muted mt-0.5 truncate uppercase tracking-tighter">
                      {activeLiveMatch.teams.home.name}
                   </div>
                </div>
                <div className="px-4 text-center">
                   <div className="bg-accent-green/20 text-accent-green px-2 py-0.5 rounded text-[10px] font-bold animate-pulse">
                      {activeLiveMatch.fixture.status.elapsed}'
                   </div>
                </div>
                <div className="flex-1 text-center">
                   <div className="text-2xl font-black text-text-primary">{activeLiveMatch.goals.away}</div>
                   <div className="text-[10px] text-text-muted mt-0.5 truncate uppercase tracking-tighter">
                      {activeLiveMatch.teams.away.name}
                   </div>
                </div>
             </div>

             {/* Live xG / Stats */}
             <div className="space-y-3">
                <div className="text-[10px] font-bold text-text-muted uppercase tracking-widest flex items-center justify-between">
                   <span className="flex items-center gap-1.5"><Target className="w-3 h-3" /> Live xG</span>
                   {!hasXG && <span className="normal-case opacity-40 font-normal">Waiting for data...</span>}
                </div>
                <div className="space-y-4">
                   <div>
                      <div className="flex items-center justify-between mb-1">
                         <span className="text-[9px] text-text-secondary uppercase">Home xG</span>
                         <span className="text-xs font-bold text-accent-green">{xg.home || '—'}</span>
                      </div>
                      <div className="h-1 w-full bg-bg-elevated rounded-full overflow-hidden">
                         <div 
                            className="h-full bg-accent-green transition-all duration-1000 shadow-[0_0_8px_rgba(0,255,135,0.4)]" 
                            style={{ width: `${Math.min(100, (xg.home / 3) * 100)}%` }} 
                         />
                      </div>
                   </div>
                   <div>
                      <div className="flex items-center justify-between mb-1">
                         <span className="text-[9px] text-text-secondary uppercase">Away xG</span>
                         <span className="text-xs font-bold text-accent-blue">{xg.away || '—'}</span>
                      </div>
                      <div className="h-1 w-full bg-bg-elevated rounded-full overflow-hidden">
                         <div 
                            className="h-full bg-accent-blue transition-all duration-1000 shadow-[0_0_8px_rgba(59,130,246,0.4)]" 
                            style={{ width: `${Math.min(100, (xg.away / 3) * 100)}%` }} 
                         />
                      </div>
                   </div>
                </div>
             </div>

             {/* Pressure/Momentum (Mocked for demo but stylized) */}
             <div className="pt-2 border-t border-[#2D3748]/50">
                <div className="text-[10px] text-text-muted uppercase mb-3 flex items-center justify-between">
                   <span className="flex items-center gap-1.5"><TrendingUp className="w-3 h-3" /> Match Momentum</span>
                   <span className="text-accent-green text-[9px] font-bold">LIVE</span>
                </div>
                <div className="h-16 flex items-end gap-1 px-1">
                   {[40, 55, 75, 45, 30, 60, 85, 95, 70, 50, 65, 80, 55, 40].map((h, i) => (
                      <div 
                         key={i} 
                         className={`flex-1 rounded-sm transition-all duration-500 ${
                           i > 10 ? 'bg-accent-green animate-pulse' : 'bg-bg-elevated'
                         }`}
                         style={{ 
                            height: `${h}%`,
                            opacity: 0.3 + (i / 14) * 0.7,
                            background: i > 10 ? 'var(--accent-green)' : 'rgba(255,255,255,0.05)'
                         }}
                      />
                   ))}
                </div>
             </div>
          </div>
        )}
      </PredictionCard>
    </div>
  );
}

import BatchResultsTable from '../components/BatchResultsTable';

export default function Dashboard({ 
  predictions, 
  loading, 
  homeTeam, 
  awayTeam,
  batchMode = false,
  batchResults = [],
  onExportBatch = () => {},
  batchExportLoading = false
}) {
  console.log('Dashboard Props:', { batchMode, resultsCount: batchResults?.length, loading });
  const [activeTab, setActiveTab] = useState('result');

  if (batchMode) {
    return (
      <div className="h-full">
        {batchResults.length === 0 && !loading ? (
          <EmptyState />
        ) : (
          <BatchResultsTable 
            results={batchResults} 
            onExport={onExportBatch} 
            loading={loading} 
            exporting={batchExportLoading}
          />
        )}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-4 h-full">
        <div className="flex gap-1 border-b border-[#1F2937] pb-0">
          {TABS.map((t) => (
            <div key={t.id} className="skeleton h-8 w-24 rounded-t-lg" />
          ))}
        </div>
        <PredictionCardSkeleton />
        <PredictionCardSkeleton />
      </div>
    );
  }

  if (!predictions) return <EmptyState />;

  const TAB_COMPONENTS = {
    result:   <ErrorBoundary componentName="Match Result"><MatchResultTab data={predictions} /></ErrorBoundary>,
    goals:    <ErrorBoundary componentName="Goals"><GoalsTab data={predictions} /></ErrorBoundary>,
    score:    <ErrorBoundary componentName="Score Grid"><ScoreTab data={predictions} /></ErrorBoundary>,
    specials: <ErrorBoundary componentName="Specials"><SpecialsTab data={predictions} /></ErrorBoundary>,
    scorers:  <ErrorBoundary componentName="Player Scorers"><ScorersTab data={predictions} /></ErrorBoundary>,
    live:     <ErrorBoundary componentName="Live Centre"><LiveTab 
                matchId={predictions.fixture_id_map?.api_football} 
                homeTeam={homeTeam} 
                awayTeam={awayTeam}
                activeTab={activeTab}
              /></ErrorBoundary>,
  };

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Match banner */}
      <div className="bg-bg-elevated rounded-xl px-4 py-3 border border-[#1F2937] animate-fade-in">
        <div className="flex items-center justify-between">
          <div className="text-center flex-1">
            <div className="font-heading font-bold text-lg text-text-primary">
              {homeTeam || 'Home Team'}
            </div>
            <div className="text-[10px] text-text-muted uppercase tracking-widest">Home</div>
          </div>
          <div className="px-4 text-center">
            <div className="font-heading font-black text-2xl text-accent-green tracking-wider">VS</div>
            <div className="text-[10px] text-text-muted">
              Confidence:{' '}
              <span className="text-accent-green font-semibold">
                {toPercent(predictions.model_confidence, 0)}
              </span>
            </div>
          </div>
          <div className="text-center flex-1">
            <div className="font-heading font-bold text-lg text-text-primary">
              {awayTeam || 'Away Team'}
            </div>
            <div className="text-[10px] text-text-muted uppercase tracking-widest">Away</div>
          </div>
        </div>

        {/* Quick odds strip */}
        {predictions.match_result && (
          <div className="flex gap-2 mt-3">
            {[
              { label: 'Home', prob: predictions.match_result.home },
              { label: 'Draw', prob: predictions.match_result.draw },
              { label: 'Away', prob: predictions.match_result.away },
            ].map(({ label, prob }) => (
              <div
                key={label}
                className="flex-1 rounded-lg p-2 text-center"
                style={{ background: 'rgba(255,255,255,0.04)' }}
              >
                <div className="text-[10px] text-text-muted">{label}</div>
                <div className="font-heading font-bold text-sm" style={{ color: probToColor(prob) }}>
                  {toPercent(prob)}
                </div>
                <div className="text-[10px] font-mono text-text-muted">{toDecimalOdds(prob)}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#1F2937] overflow-x-auto shrink-0">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-2 text-xs font-semibold uppercase tracking-wide whitespace-nowrap transition-all ${
              activeTab === tab.id ? 'tab-active' : 'tab-inactive'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {TAB_COMPONENTS[activeTab]}
      </div>
    </div>
  );
}
