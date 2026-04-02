import { useState, useCallback } from 'react';
import { Users, RefreshCw, ChevronDown, Plus, Trash2, AlertCircle } from 'lucide-react';
import PitchFormation from './PitchFormation';
import { positionToClass } from '../utils/colorScale';

const FORMATIONS = ['4-4-2', '4-3-3', '3-5-2', '4-2-3-1', '5-3-2', '4-1-4-1'];

const POSITIONS = ['GK', 'RB', 'CB', 'LB', 'CDM', 'CM', 'CAM', 'RM', 'LM', 'RW', 'LW', 'CF', 'ST'];

const EMPTY_PLAYER = () => ({
  name: '',
  position: 'CM',
  jersey_no: '',
  goals_season: 0,
  xg_per90: 0.2,
  recent_form_goals: 0,
  penalty_taker: false,
  player_id: '',
});

function PlayerRow({ player, index, onChange, onRemove, isCompact = false, injury = null }) {
  return (
    <div className="flex items-center gap-1.5 group">
      {/* Jersey # */}
      <input
        type="number"
        min="1" max="99"
        placeholder="#"
        value={player.jersey_no}
        onChange={(e) => onChange(index, 'jersey_no', e.target.value)}
        className="w-8 h-8 bg-bg-elevated rounded px-1 py-1 text-sm text-center text-text-primary border border-[#2D3748] focus:border-accent-green/50 outline-none"
      />

      {/* Name + Injury Indicator */}
      <div className="flex-1 min-w-[140px] relative flex items-center">
        <input
          type="text"
          placeholder={`Player ${index + 1}`}
          value={player.name}
          onChange={(e) => onChange(index, 'name', e.target.value)}
          className={`w-full h-8 bg-bg-elevated rounded px-2.5 py-1 text-sm text-text-primary border border-[#2D3748] focus:border-accent-green/50 outline-none ${injury ? 'pr-7 border-danger/30' : ''}`}
        />
        {injury && (
          <div className="absolute right-2 text-danger" title={`${injury.type}: ${injury.reason}`}>
            <AlertCircle className="w-3.5 h-3.5 fill-danger/10" />
          </div>
        )}
      </div>

      {/* Position */}
      <select
        value={player.position}
        onChange={(e) => onChange(index, 'position', e.target.value)}
        className="w-12 h-8 bg-bg-elevated rounded px-1 py-1 text-[11px] text-text-primary border border-[#2D3748] focus:border-accent-green/50 outline-none appearance-none text-center"
      >
        {POSITIONS.map((p) => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>

      {/* Goals */}
      {!isCompact && (
        <input
          type="number"
          min="0"
          placeholder="G"
          value={player.goals_season}
          onChange={(e) => onChange(index, 'goals_season', Number(e.target.value))}
          className="w-9 h-8 bg-bg-elevated rounded px-1 py-1 text-sm text-center text-text-primary border border-[#2D3748] focus:border-accent-green/50 outline-none"
        />
      )}

      {/* xG */}
      {!isCompact && (
        <input
          type="number"
          min="0" max="2" step="0.01"
          placeholder="xG"
          value={player.xg_per90}
          onChange={(e) => onChange(index, 'xg_per90', Number(e.target.value))}
          className="w-11 h-8 bg-bg-elevated rounded px-1 py-1 text-sm text-center text-text-primary border border-[#2D3748] focus:border-accent-green/50 outline-none"
        />
      )}

      {/* Remove */}
      <button
        onClick={() => onRemove(index)}
        className="opacity-0 group-hover:opacity-100 text-text-muted hover:text-danger transition-all"
      >
        <Trash2 className="w-3 h-3" />
      </button>
    </div>
  );
}

export default function LineupSelector({
  side = 'home',
  teamName = '',
  teamId = null,
  onLineupChange,
  onFetchSquad,
  loadingSquad = false,
  injuries = []
}) {
  const [formation, setFormation] = useState('4-4-2');
  const [starters, setStarters] = useState(
    Array.from({ length: 11 }, (_, i) => ({ ...EMPTY_PLAYER(), jersey_no: i + 1 }))
  );
  const [subs, setSubs] = useState(
    Array.from({ length: 7 }, (_, i) => ({ ...EMPTY_PLAYER(), jersey_no: i + 12 }))
  );
  const [showPitch, setShowPitch] = useState(true);
  const [showSubs, setShowSubs] = useState(false);

  const updateStarter = useCallback((index, field, value) => {
    setStarters((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      if (onLineupChange) onLineupChange(next, subs, side);
      return next;
    });
  }, [subs, onLineupChange, side]);

  const updateSub = useCallback((index, field, value) => {
    setSubs((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      if (onLineupChange) onLineupChange(starters, next, side);
      return next;
    });
  }, [starters, onLineupChange, side]);

  const removeSub = useCallback((index) => {
    setSubs((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const addSub = () => {
    setSubs((prev) => [...prev, { ...EMPTY_PLAYER(), jersey_no: prev.length + 12 }]);
  };

  const handleFetchSquad = async () => {
    if (!onFetchSquad || !teamId) return;
    const data = await onFetchSquad(teamId, side);
    if (data?.players) {
      const xi = data.players.slice(0, 11).map((p, i) => ({
        ...p,
        jersey_no: p.jersey_no || i + 1,
      }));
      const subsData = data.players.slice(11, 18).map((p, i) => ({
        ...p,
        jersey_no: p.jersey_no || i + 12,
      }));
      setStarters(xi);
      setSubs(subsData);
      if (onLineupChange) onLineupChange(xi, subsData, side);
    }
  };

  const isHome = side === 'home';
  const accentColor = isHome ? '#3B82F6' : '#EF4444';
  const sideLabel = isHome ? '🏠 Home' : '✈️ Away';

  return (
    <div className="prediction-card space-y-3 h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-xs text-text-muted uppercase tracking-widest mb-0.5">{sideLabel}</div>
          <h2 className="font-heading font-black text-xl text-text-primary tracking-tight">
            {teamName || (isHome ? 'Home Team' : 'Away Team')}
          </h2>
        </div>
        <div className="flex items-center gap-2">
          {teamId && (
            <button
              onClick={handleFetchSquad}
              disabled={loadingSquad}
              title="Auto-fetch squad from API"
              className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg bg-bg-elevated hover:bg-[#2D3748] text-text-secondary border border-[#2D3748] transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingSquad ? 'animate-spin' : ''}`} />
              {loadingSquad ? 'Loading…' : 'Fetch'}
            </button>
          )}
          <button
            onClick={() => setShowPitch(!showPitch)}
            className="text-sm px-3 py-1.5 rounded-lg bg-bg-elevated hover:bg-[#2D3748] text-text-secondary border border-[#2D3748] transition-all"
          >
            {showPitch ? 'List' : 'Pitch'}
          </button>
        </div>
      </div>

      {/* Formation */}
      <div className="flex items-center gap-3 py-2 border-y border-[#2D3748]/50 mb-4">
        <span className="text-sm font-bold text-text-muted uppercase tracking-tighter">Formation</span>
        <div className="flex gap-1.5 flex-wrap">
          {FORMATIONS.map((f) => (
            <button
              key={f}
              onClick={() => setFormation(f)}
              className={`text-[11px] font-bold px-2.5 py-1 rounded-md transition-all ${
                formation === f
                  ? 'bg-accent-green text-bg-primary shadow-[0_0_12px_rgba(0,255,135,0.25)]'
                  : 'bg-bg-elevated text-text-secondary hover:text-text-primary hover:bg-[#2D3748]'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Pitch view */}
      {showPitch && (
        <div className="flex justify-center mb-6">
          <div className="w-full max-w-[280px] animate-fade-in">
            <PitchFormation
              players={starters}
              formation={formation}
              isAway={!isHome}
            />
          </div>
        </div>
      )}

      {/* Starters */}
      <div className="space-y-3">
        <div className="text-sm font-bold text-text-primary uppercase tracking-widest flex items-center gap-2 border-l-2 border-accent-green pl-2">
          <Users className="w-4 h-4 text-accent-green" />
          Starting XI
        </div>
        <div className="space-y-1.5">
          {/* Column headers */}
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-text-muted px-1 mb-1">
            <span className="w-8 text-center ml-0.5">#</span>
            <span className="flex-1">PLAYER NAME</span>
            <span className="w-12 text-center">POS</span>
            {!showPitch && <span className="w-9 text-center">G</span>}
            {!showPitch && <span className="w-11 text-center">xG</span>}
            <span className="w-4" />
          </div>
          {starters.map((p, i) => {
            const injury = injuries.find(inj => 
              inj.player.id === p.player_id || 
              (p.name && inj.player.name.toLowerCase().includes(p.name.toLowerCase()))
            );
            return (
              <PlayerRow
                key={i}
                player={p}
                index={i}
                onChange={updateStarter}
                onRemove={() => {}}
                injury={injury}
              />
            );
          })}
        </div>
      </div>

      {/* Substitutes */}
      <div className="pt-4 border-t border-[#2D3748]/50 mt-2">
        <button
          className="flex items-center gap-2 text-sm font-bold text-text-secondary mb-3 uppercase tracking-widest w-full hover:text-text-primary transition-colors focus:outline-none"
          onClick={() => setShowSubs(!showSubs)}
        >
          <ChevronDown className={`w-4 h-4 transition-transform duration-300 ${showSubs ? 'rotate-180' : ''}`} />
          Substitutes ({subs.length})
        </button>
        {showSubs && (
          <div className="space-y-1.5">
            {subs.map((p, i) => {
               const injury = injuries.find(inj => 
                 inj.player.id === p.player_id || 
                 (p.name && inj.player.name.toLowerCase().includes(p.name.toLowerCase()))
               );
               return (
                <PlayerRow
                  key={i}
                  player={p}
                  index={i}
                  onChange={updateSub}
                  onRemove={removeSub}
                  isCompact
                  injury={injury}
                />
               );
            })}
            {subs.length < 9 && (
              <button
                onClick={addSub}
                className="flex items-center gap-2 text-sm font-medium text-text-muted hover:text-accent-green transition-all mt-3 px-3 py-2 rounded-lg border border-dashed border-[#2D3748] hover:border-accent-green/50 w-full justify-center bg-bg-elevated/20"
              >
                <Plus className="w-4 h-4" /> Add substitute
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
