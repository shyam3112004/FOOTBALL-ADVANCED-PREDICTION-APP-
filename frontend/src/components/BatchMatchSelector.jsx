import React, { useState, useMemo } from 'react';
import { Search, CheckCircle2, ListFilter, X, CheckSquare, Square, Loader2, Globe, Calendar, RotateCcw, Zap } from 'lucide-react';
import { formatMatchDate } from '../utils/dateUtils';
import usePredictionStore from '../store/predictionStore';

export default function BatchMatchSelector({ 
  loading, 
}) {
  const [search, setSearch] = useState('');
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  });
  const [endDate, setEndDate] = useState('');

  const { 
    batchSelectedIds, setBatchSelectedIds, 
    batchFixtures, batchComps, removeBatchComp,
    batchLoadingFixtures 
  } = usePredictionStore();

  const filteredFixtures = useMemo(() => {
    return batchFixtures.filter(f => {
      const matchText = `${f.home_team} ${f.away_team} ${f._compName || ''}`.toLowerCase().includes(search.toLowerCase());
      
      let matchDate = true;
      if (startDate || endDate) {
        const fDate = new Date(f.date).setHours(0, 0, 0, 0);
        if (startDate) {
          const start = new Date(startDate).setHours(0, 0, 0, 0);
          if (fDate < start) matchDate = false;
        }
        if (endDate) {
          const end = new Date(endDate).setHours(0, 0, 0, 0);
          if (fDate > end) matchDate = false;
        }
      }

      return matchText && matchDate;
    });
  }, [batchFixtures, search, startDate, endDate]);

  // Group by league for display
  const groupedFixtures = useMemo(() => {
    const groups = {};
    filteredFixtures.forEach(f => {
      const key = f._compCode || 'unknown';
      if (!groups[key]) groups[key] = { name: f._compName || key, emblem: f._compEmblem, fixtures: [] };
      groups[key].fixtures.push(f);
    });
    return Object.entries(groups);
  }, [filteredFixtures]);

  const toggleSelect = (id) => {
    const idx = batchSelectedIds.indexOf(id);
    if (idx >= 0) {
      setBatchSelectedIds(batchSelectedIds.filter(x => x !== id));
    } else {
      setBatchSelectedIds([...batchSelectedIds, id]);
    }
  };

  const selectAll = () => {
    const ids = filteredFixtures.map(f => f.match_id);
    setBatchSelectedIds(ids);
  };

  const deselectAll = () => {
    setBatchSelectedIds([]);
  };

  return (
    <div className="bg-bg-elevated rounded-2xl border border-[#2D3748] shadow-2xl flex flex-col h-full overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="p-4 border-b border-[#2D3748] bg-bg-elevated/50 backdrop-blur-md">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="font-heading font-black text-xl text-text-primary flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-accent-green" />
              Batch Match Selector
            </h3>
            <p className="text-[10px] text-text-muted uppercase tracking-widest mt-1">
              Select leagues above, then pick matches
            </p>
          </div>
          <div className="flex items-center gap-2">
             <button 
               onClick={selectAll}
               className="text-[11px] px-2 py-1 rounded bg-bg-primary border border-[#2D3748] text-text-secondary hover:text-accent-green transition-all"
             >
               Select All
             </button>
             <button 
               onClick={deselectAll}
               className="text-[11px] px-2 py-1 rounded bg-bg-primary border border-[#2D3748] text-text-secondary hover:text-danger transition-all"
             >
               Clear All
             </button>
          </div>
        </div>

        {/* Selected Leagues Chips */}
        {batchComps.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {batchComps.map(comp => (
              <div key={comp.code} className="flex items-center gap-1 bg-accent-green/10 border border-accent-green/30 rounded-lg px-2 py-1 text-[10px] font-bold text-accent-green">
                {comp.emblem && <img src={comp.emblem} alt="" className="w-3.5 h-3.5 object-contain" />}
                <span className="truncate max-w-[100px]">{comp.name}</span>
                <button 
                  onClick={() => removeBatchComp(comp.code)}
                  className="ml-0.5 hover:text-danger transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Search Bar & Date Filters */}
        <div className="space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="text"
              placeholder="Search teams..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-bg-primary border border-[#2D3748] rounded-xl py-2.5 pl-10 pr-4 text-sm text-text-primary focus:border-accent-green/50 outline-none transition-all placeholder:text-text-muted/50"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex-1 min-w-[120px] relative">
              <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted pointer-events-none" />
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full bg-bg-primary border border-[#2D3748] rounded-lg py-1.5 pl-8 pr-2 text-[11px] text-text-primary focus:border-accent-green/30 outline-none transition-all [color-scheme:dark]"
              />
              <span className="absolute -top-2 left-2 px-1 bg-bg-elevated text-[9px] text-text-muted font-bold uppercase tracking-tighter">Start</span>
            </div>
            
            <div className="flex-1 min-w-[120px] relative">
              <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted pointer-events-none" />
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full bg-bg-primary border border-[#2D3748] rounded-lg py-1.5 pl-8 pr-2 text-[11px] text-text-primary focus:border-accent-green/30 outline-none transition-all [color-scheme:dark]"
              />
              <span className="absolute -top-2 left-2 px-1 bg-bg-elevated text-[9px] text-text-muted font-bold uppercase tracking-tighter">End</span>
            </div>

            {(startDate || endDate || search) && (
              <button
                onClick={() => {
                  setSearch('');
                  setStartDate('');
                  setEndDate('');
                }}
                className="p-1.5 rounded-lg bg-bg-primary border border-[#2D3748] text-text-muted hover:text-accent-green hover:border-accent-green/30 transition-all group"
                title="Reset Filters"
              >
                <RotateCcw className="w-4 h-4 group-hover:rotate-[-45deg] transition-transform" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Smart Filters (Shared with Results) */}
      <div className="px-4 py-3 bg-bg-primary/30 border-b border-[#2D3748] space-y-2">
         <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest">Smart Filters</span>
            <div className="flex items-center gap-1">
               <Zap className="w-3 h-3 text-accent-green" />
               <span className="text-[9px] text-accent-green font-bold uppercase">Synced</span>
            </div>
         </div>
         <div className="flex gap-2">
            <select 
              value={usePredictionStore(s => s.batchTargetMarket)}
              onChange={(e) => usePredictionStore.getState().setBatchTargetMarket(e.target.value)}
              className="flex-1 bg-bg-primary border border-[#2D3748] rounded-lg py-1.5 px-2 text-[11px] font-bold text-accent-green outline-none"
            >
              <option value="any">Any Market</option>
              <option value="home">Home Win</option>
              <option value="draw">Draw</option>
              <option value="away">Away Win</option>
              <option value="double_chance">Double Chance</option>
              <option value="btts">BTTS Yes</option>
              <option value="over25">Over 2.5</option>
            </select>
            <div className="w-16 relative">
               <input 
                 type="number"
                 value={usePredictionStore(s => s.batchMinProb)}
                 onChange={(e) => usePredictionStore.getState().setBatchMinProb(Number(e.target.value))}
                 className="w-full bg-bg-primary border border-[#2D3748] rounded-lg py-1.5 pl-2 pr-6 text-[11px] font-bold text-accent-green outline-none text-center"
               />
               <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-bold text-accent-green">%</span>
            </div>
         </div>
      </div>

      {/* Fixture List Grouped By League */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
        {batchLoadingFixtures && (
          <div className="flex items-center justify-center py-8 gap-2 text-text-muted">
            <Loader2 className="w-5 h-5 animate-spin text-accent-green" />
            <span className="text-sm">Loading fixtures...</span>
          </div>
        )}
        
        {!batchLoadingFixtures && batchFixtures.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-text-muted opacity-40">
             <Globe className="w-12 h-12 mb-3" />
             <p className="text-sm font-semibold">
               {batchComps.length > 0 ? 'Loading fixtures or none found' : 'No leagues selected'}
             </p>
             <p className="text-[10px] mt-1">
               {batchComps.length > 0 ? 'Wait a moment or select different leagues' : 'Select leagues from the dropdown above'}
             </p>
          </div>
        ) : !batchLoadingFixtures && filteredFixtures.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-text-muted opacity-40">
             <ListFilter className="w-12 h-12 mb-3" />
             <p className="text-sm font-semibold">No matches found</p>
             <p className="text-[10px] mt-1">Try adjusting your search or date filters</p>
          </div>
        ) : (
          groupedFixtures.map(([compCode, group]) => (
            <div key={compCode} className="mb-2">
              {/* League Header */}
              {batchComps.length > 1 && (
                <div className="flex items-center gap-2 px-2 py-1.5 mb-1 sticky top-0 bg-bg-elevated/90 backdrop-blur-sm z-10 rounded-lg">
                  {group.emblem && <img src={group.emblem} alt="" className="w-4 h-4 object-contain" />}
                  <span className="text-[10px] font-bold text-accent-green uppercase tracking-widest">{group.name}</span>
                  <span className="text-[9px] text-text-muted ml-auto">{group.fixtures.length} matches</span>
                </div>
              )}
              
              {group.fixtures.map(f => {
                const isSelected = batchSelectedIds.includes(f.match_id);
                return (
                  <div 
                    key={f.match_id}
                    onClick={() => toggleSelect(f.match_id)}
                    className={`group flex items-center gap-3 px-3 py-2.5 rounded-xl border transition-all cursor-pointer mb-1 ${
                      isSelected 
                        ? 'bg-accent-green/10 border-accent-green/30 ring-1 ring-accent-green/20' 
                        : 'bg-bg-primary/40 border-[#2D3748] hover:border-[#4A5568] hover:bg-bg-primary/60'
                    }`}
                  >
                    <div className={`shrink-0 transition-all ${isSelected ? 'text-accent-green scale-110' : 'text-text-muted opacity-40'}`}>
                      {isSelected ? <CheckSquare className="w-5 h-5" /> : <Square className="w-5 h-5" />}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                         <span className={`text-sm font-bold truncate ${isSelected ? 'text-text-primary' : 'text-text-secondary'}`}>
                           {f.home_team} vs {f.away_team}
                         </span>
                         <span className="text-[10px] text-text-muted shrink-0 font-mono">
                           {formatMatchDate(f.date)}
                         </span>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        {batchComps.length > 1 && f._compName && (
                          <span className="text-[9px] bg-accent-blue/10 text-accent-blue px-1.5 py-0.5 rounded font-semibold">
                            {f._compName}
                          </span>
                        )}
                        {f.venue && (
                          <span className="text-[10px] text-text-muted/60">{f.venue}</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ))
        )}
      </div>

      <div className="p-4 bg-bg-elevated/80 border-t border-[#2D3748] flex items-center justify-between">
        <div className="text-xs">
          <span className="font-bold text-accent-green">
            {batchSelectedIds.length}
          </span>
          <span className="text-text-muted ml-1">matches selected</span>
          {batchComps.length > 0 && (
            <span className="text-text-muted ml-1">
              · {batchComps.length} league{batchComps.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
