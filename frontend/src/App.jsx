import { useState, useCallback, useEffect } from 'react';
import api from './services/apiClient';
import {
  Activity, Upload, Download, ChevronDown, Zap,
  AlertCircle, X, Trophy, Database, Loader2, History, Menu
} from 'lucide-react';

import Dashboard from './pages/Dashboard';
import LineupSelector from './components/LineupSelector';
import CSVUploader from './components/CSVUploader';
import SearchableSelect from './components/SearchableSelect';
import ErrorBoundary from './components/ErrorBoundary';
import MobileNav, { MatchSetupDrawer } from './components/MobileNav';
import PredictionHistory from './components/PredictionHistory';
import { usePredictions } from './hooks/usePredictions';
import { useSquad } from './hooks/useSquad';
import { toPercent } from './utils/oddsConverter';
import { formatMatchDate } from './utils/dateUtils';
import { useBatchPredictions } from './hooks/useBatchPredictions';
import BatchMatchSelector from './components/BatchMatchSelector';
import usePredictionStore from './store/predictionStore';

// ─── Header ──────────────────────────────────────────────────────────────────

function Header({
  competitions, selectedComp, onCompChange,
  fixtures, selectedFixture, onFixtureChange,
  onCSVUpload, loading, onExport, hasPredictions,
  loadingFixtures, isApiEnabled, onApiToggle, loadingCompetitions,
  csvStatus, fixtureError, onHistoryOpen, onMobileMatchSetup,
  mode, onModeChange, onRun, canRun,
  canSelectAll, onSelectAll
}) {
  const { csvStatus: storeStatus } = usePredictionStore();

  return (
    <header className="glass header-glow sticky top-0 z-50 px-4 py-3">
      <div className="max-w-screen-2xl mx-auto flex items-center gap-3 flex-wrap">
        {/* Logo */}
        <div className="flex items-center gap-2 mr-2">
          <div className="w-8 h-8 rounded-lg bg-accent-green flex items-center justify-center animate-glow">
            <span className="text-bg-primary text-lg font-bold leading-none">⚽</span>
          </div>
          <div>
            <div className="font-heading font-black text-lg leading-none text-text-primary tracking-wider">
              Predictor<span className="text-accent-green">Pro</span>
            </div>
            <div className="text-[9px] text-text-muted tracking-widest uppercase">
              ML Match Analysis
            </div>
          </div>
        </div>

        {/* Mobile: Match setup button (replaces full selectors on small screens) */}
        <button
          id="mobile-match-setup-btn"
          onClick={onMobileMatchSetup}
          className="md:hidden flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                     bg-bg-elevated border border-[#2D3748] text-text-secondary
                     hover:text-text-primary text-sm transition-all"
        >
          <Menu className="w-4 h-4" />
          {selectedFixture
            ? `${selectedFixture.home_team} vs ${selectedFixture.away_team}`
            : 'Select Match'}
        </button>

        {/* Desktop: API Toggle */}
        <div className="hidden md:flex items-center gap-2 bg-bg-elevated px-3 py-1.5 rounded-lg border border-[#2D3748]">
          <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest whitespace-nowrap">API Mode</span>
          <button
            id="api-toggle-btn"
            onClick={() => onApiToggle(!isApiEnabled)}
            className={`relative w-10 h-5 rounded-full p-0.5 transition-colors duration-200 outline-none ${
              isApiEnabled ? 'bg-accent-green' : 'bg-bg-primary border border-[#2D3748]'
            }`}
          >
            <div
              className={`w-4 h-4 rounded-full shadow-sm transform transition-transform duration-200 ${
                isApiEnabled ? 'translate-x-4 bg-bg-primary' : 'translate-x-0 bg-text-muted'
              }`}
            />
          </button>
        </div>

        {/* Mode Toggle */}
        <div className="flex bg-bg-elevated p-1 rounded-xl border border-[#2D3748] ml-2">
          {['single', 'batch'].map(m => (
            <button
              key={m}
              onClick={() => onModeChange(m)}
              className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all ${
                mode === m ? 'bg-bg-primary text-accent-green shadow-sm' : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              {m === 'single' ? 'Single' : 'Batch'}
            </button>
          ))}
        </div>

        {/* Desktop: Competition selector */}
        <div className="hidden md:block w-64 shrink-0">
          <SearchableSelect
            options={competitions}
            value={selectedComp}
            onChange={onCompChange}
            placeholder={isApiEnabled ? 'Select League' : 'API Disabled'}
            disabled={!isApiEnabled}
            loading={loadingCompetitions}
            iconKey="emblem"
            labelKey="name"
            valueKey="code"
            canSelectAll={canSelectAll}
            onSelectAll={onSelectAll}
          />
        </div>

        {/* Desktop: Fixture selector */}
        {mode === 'single' && (
          <div className="hidden md:block flex-1 min-w-[320px] max-w-[480px]">
            <SearchableSelect
              options={fixtures.map(f => ({
                ...f,
                label: `${f.home_team} vs ${f.away_team} · ${formatMatchDate(f.date)}`,
                icon: f.home_logo || f.emblem || ''
              }))}
              value={selectedFixture ? selectedFixture.match_id : ''}
              onChange={(val, opt) => onFixtureChange(opt)}
              placeholder={!isApiEnabled ? 'Select CSV' : loadingFixtures ? 'Loading Matches...' : 'Select Match'}
              disabled={!selectedComp || !isApiEnabled || loadingFixtures}
              labelKey="label"
              valueKey="match_id"
              iconKey="icon"
              emptyMessage={fixtureError || (selectedComp ? "No matches found for this league" : "Select a league first")}
            />
          </div>
        )}

        <div className="flex items-center gap-2 ml-auto">
          {/* History button */}
          <button
            id="history-btn"
            onClick={onHistoryOpen}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bg-elevated
                       border border-[#2D3748] text-text-secondary hover:text-text-primary
                       hover:border-accent-green/40 transition-all"
            title="View prediction history"
          >
            <History className="w-4 h-4" />
            <span className="hidden sm:inline text-sm">History</span>
          </button>

          {/* CSV Upload (desktop) */}
          <div className="relative hidden md:block">
            <CSVDropdown onCSVUpload={onCSVUpload} csvStatus={storeStatus} />
          </div>

          {/* Main Action Button (Moved to Top) */}
          {(mode === 'single' ? canRun : true) && (
            <button
              id="header-run-btn"
              onClick={onRun}
              disabled={loading || (mode === 'single' && !canRun)}
              className={`flex items-center gap-2 px-6 py-2 rounded-xl font-heading font-black text-sm tracking-wider transition-all duration-300 ${
                loading 
                  ? 'bg-bg-elevated text-text-muted cursor-wait' 
                  : 'bg-accent-green text-bg-primary hover:scale-[1.05] shadow-[0_0_20px_rgba(0,255,135,0.3)] animate-glow'
              }`}
            >
              {loading ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Analyzing...</>
              ) : (
                <><Zap className="w-4 h-4 fill-current" /> {mode === 'single' ? 'Run Prediction' : 'Predict All'}</>
              )}
            </button>
          )}

          {/* Export */}
          {hasPredictions && !loading && (
            <button
              id="export-btn"
              onClick={onExport}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-bg-elevated
                         border border-accent-blue/40 hover:border-accent-blue
                         text-sm text-accent-blue hover:text-accent-blue transition-all"
            >
              <Download className="w-4 h-4" />
              <span className="hidden sm:inline">Export</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

function CSVDropdown({ onCSVUpload, csvStatus }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        id="csv-upload-btn"
        onClick={() => setOpen(!open)}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bg-elevated border transition-all ${
          csvStatus === 'success'
            ? 'border-accent-green text-accent-green shadow-[0_0_10px_rgba(0,255,135,0.1)]'
            : csvStatus === 'error'
            ? 'border-danger text-danger'
            : 'border-[#2D3748] text-text-secondary hover:text-text-primary'
        }`}
      >
        <Upload className="w-4 h-4" />
        CSV {csvStatus === 'success' && '✅'}
      </button>
      {open && (
        <div className="absolute right-0 top-10 z-50 w-80 bg-bg-elevated border border-[#1F2937] rounded-xl shadow-2xl p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-semibold text-text-primary">Upload CSV Data</span>
            <button onClick={() => setOpen(false)}>
              <X className="w-4 h-4 text-text-muted" />
            </button>
          </div>
          <CSVUploader onDataLoaded={(data) => { onCSVUpload(data); setOpen(false); }} />
        </div>
      )}
    </div>
  );
}

// ─── Footer ──────────────────────────────────────────────────────────────────

function Footer({ modelStatus, dataSource, onRun, loading, canRun }) {
  return (
    <footer className="glass border-t border-[#1F2937] px-4 py-3 pb-safe md:pb-3">
      <div className="max-w-screen-2xl mx-auto flex items-center gap-4 flex-wrap">
        {/* Model status */}
        <div className="flex items-center gap-2 text-xs">
          <Activity className="w-3.5 h-3.5 text-accent-green" />
          <span className="text-text-muted">Model:</span>
          <span className={modelStatus.is_trained ? 'text-accent-green font-semibold' : 'text-warning font-semibold'}>
            {modelStatus.is_trained
              ? `XGBoost (${modelStatus.training_samples} matches)`
              : 'Heuristic fallback (upload CSV to train)'}
          </span>
        </div>

        {/* Metrics badge */}
        {modelStatus.is_trained && modelStatus.metrics?.home_win_accuracy && (
          <div className="hidden sm:flex items-center gap-2 text-xs">
            <Trophy className="w-3.5 h-3.5 text-warning" />
            <span className="text-text-muted">Acc:</span>
            <span className="text-warning font-semibold">
              {(modelStatus.metrics.home_win_accuracy * 100).toFixed(0)}%
            </span>
          </div>
        )}

        {/* Data source */}
        <div className="flex items-center gap-2 text-xs">
          <Database className="w-3.5 h-3.5 text-accent-blue" />
          <span className="text-text-muted">Source:</span>
          <span className="text-text-secondary font-semibold capitalize">{dataSource}</span>
        </div>

        {/* Run button */}
        <div className="ml-auto">
          <button
            id="run-predictions-btn"
            onClick={onRun}
            disabled={!canRun || loading}
            className="run-btn px-8 py-3 text-base disabled:opacity-40 disabled:animate-none disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Predicting…</>
            ) : (
              <><Zap className="w-4 h-4" /> Run Predictions</>
            )}
          </button>
        </div>
      </div>
    </footer>
  );
}

// ─── App ─────────────────────────────────────────────────────────────────────

export default function App() {
  const {
    predictions, loading, error,
    modelStatus, predictionId,
    runPredictions, exportExcel, fetchModelStatus,
    trainCompetition,
  } = usePredictions();

  const {
    batchResults, loading: batchLoading, 
    progress: batchProgress, runBatchPredictions, 
    exportBatchExcel, clearBatch, error: batchError,
    exportLoading: batchExportLoading
  } = useBatchPredictions();

  const {
    competitions, fixtures, squad,
    loadingSquad, loadingCompetitions, loadingFixtures,
    fetchCompetitions, fetchFixtures, fetchSquad,
    fetchMatchInjuries, injuries, error: squadError
  } = useSquad();

  const selectedComp = usePredictionStore(state => state.selectedComp);
  const selectedFixture = usePredictionStore(state => state.selectedFixture);
  const standings = usePredictionStore(state => state.standings);
  const isApiEnabled = usePredictionStore(state => state.isApiEnabled);
  const dataSource = usePredictionStore(state => state.dataSource);
  const csvData = usePredictionStore(state => state.csvData);
  const homeLineup = usePredictionStore(state => state.homeLineup);
  const homeSubs = usePredictionStore(state => state.homeSubs);
  const awayLineup = usePredictionStore(state => state.awayLineup);
  const awaySubs = usePredictionStore(state => state.awaySubs);
  const mobilePanel = usePredictionStore(state => state.mobilePanel);
  const matchSetupOpen = usePredictionStore(state => state.matchSetupOpen);
  const historyOpen = usePredictionStore(state => state.historyOpen);
  const mode = usePredictionStore(state => state.mode);
  const batchSelectedIds = usePredictionStore(state => state.batchSelectedIds);
  const batchFixtures = usePredictionStore(state => state.batchFixtures);
  const batchComps = usePredictionStore(state => state.batchComps);

  const setSelectedComp = usePredictionStore(state => state.setSelectedComp);
  const setSelectedFixture = usePredictionStore(state => state.setSelectedFixture);
  const setStandings = usePredictionStore(state => state.setStandings);
  const setApiEnabled = usePredictionStore(state => state.setApiEnabled);
  const setCsvData = usePredictionStore(state => state.setCsvData);
  const setHomeLineup = usePredictionStore(state => state.setHomeLineup);
  const setAwayLineup = usePredictionStore(state => state.setAwayLineup);
  const setMobilePanel = usePredictionStore(state => state.setMobilePanel);
  const setMatchSetupOpen = usePredictionStore(state => state.setMatchSetupOpen);
  const setHistoryOpen = usePredictionStore(state => state.setHistoryOpen);
  const setMode = usePredictionStore(state => state.setMode);
  const addBatchComp = usePredictionStore(state => state.addBatchComp);
  const addBatchFixtures = usePredictionStore(state => state.addBatchFixtures);
  const setBatchLoadingFixtures = usePredictionStore(state => state.setBatchLoadingFixtures);
  const clearBatchAll = usePredictionStore(state => state.clearBatchAll);

  // Load competitions on mount
  useEffect(() => {
    fetchCompetitions();
    fetchModelStatus();
  }, [fetchCompetitions, fetchModelStatus]);

  // Fetch fixtures and standings when competition changes
  const handleSelectAllLeagues = async (filteredComps) => {
    if (!filteredComps || filteredComps.length === 0) return;
    
    setBatchLoadingFixtures(true);
    try {
      // Use latest state from store to avoid stale closures
      const currentComps = usePredictionStore.getState().batchComps;
      
      const promises = filteredComps.map(async (comp) => {
        if (currentComps.some(c => c.code === comp.code)) return null;
        
        addBatchComp({ code: comp.code, name: comp.name, emblem: comp.emblem });
        try {
          const { data } = await api.get(`/api/competitions/${comp.code}/fixtures`);
          return (data.fixtures || []).filter(f => !f.is_error).map(f => ({
            ...f,
            _compCode: comp.code,
            _compName: comp.name,
            _compEmblem: comp.emblem,
          }));
        } catch (err) {
          console.error(`Failed to fetch fixtures for ${comp.code}:`, err);
          return null;
        }
      });

      const results = await Promise.all(promises);
      const allNewFixtures = results.filter(Boolean).flat();
      if (allNewFixtures.length > 0) {
        addBatchFixtures(allNewFixtures);
      }
      
      // Also trigger background training for each
      filteredComps.forEach(comp => trainCompetition(comp.code));
    } catch (e) {
      console.error('Failed to select all leagues:', e);
    } finally {
      setBatchLoadingFixtures(false);
    }
  };

  const handleCompChange = async (code) => {
    setSelectedComp(code);
    setStandings([]);
    if (code) {
      // In batch mode: add league fixtures to accumulated list
      if (mode === 'batch') {
        const comp = competitions.find(c => c.code === code);
        if (comp && !batchComps.some(c => c.code === code)) {
          addBatchComp({ code: comp.code, name: comp.name, emblem: comp.emblem });
          setBatchLoadingFixtures(true);
          try {
            const { data } = await api.get(`/api/competitions/${code}/fixtures`);
            const leagueFixtures = (data.fixtures || []).filter(f => !f.is_error).map(f => ({
              ...f,
              _compCode: comp.code,
              _compName: comp.name,
              _compEmblem: comp.emblem,
            }));
            addBatchFixtures(leagueFixtures);
          } catch (e) {
            console.error('Failed to fetch batch fixtures:', e);
          } finally {
            setBatchLoadingFixtures(false);
          }
        }
        trainCompetition(code);
      } else {
        fetchFixtures(code);
        trainCompetition(code);
        try {
          const { data } = await api.get(`/api/competitions/${code}/standings`);
          setStandings(data.standings || []);
        } catch {}
      }
    }
  };

  const handleFixtureChange = (fixture) => {
    setSelectedFixture(fixture);
    if (fixture?.match_id) {
      fetchMatchInjuries(fixture.match_id);
      if (fixture.home_team_id) fetchSquad(fixture.home_team_id, 'home');
      if (fixture.away_team_id) fetchSquad(fixture.away_team_id, 'away');
    }
  };

  const handleHomeLineup = useCallback((starters, subs) => {
    setHomeLineup(starters, subs);
  }, [setHomeLineup]);

  const handleAwayLineup = useCallback((starters, subs) => {
    setAwayLineup(starters, subs);
  }, [setAwayLineup]);

  const handleCSVUpload = (data) => {
    setCsvData(data);
    if (!isApiEnabled) usePredictionStore.setState({ dataSource: 'csv' });
  };

  const handleApiToggle = (val) => {
    setApiEnabled(val);
  };

  const canRun = Boolean(selectedFixture?.home_team && selectedFixture?.away_team);

  const handleRun = async () => {
    if (!selectedFixture) return;
    const findPos = (teamId) => standings.find(s => s.team_id === teamId)?.position || 10;
    const payload = {
      home_team: selectedFixture.home_team,
      away_team: selectedFixture.away_team,
      home_team_id: selectedFixture.home_team_id,
      away_team_id: selectedFixture.away_team_id,
      competition_code: selectedComp || 'PL',
      home_lineup: homeLineup.filter(p => p.name),
      away_lineup: awayLineup.filter(p => p.name),
      home_subs: homeSubs.filter(p => p.name),
      away_subs: awaySubs.filter(p => p.name),
      home_position: findPos(selectedFixture.home_team_id),
      away_position: findPos(selectedFixture.away_team_id),
      match_importance: 1.0,
      data_source: dataSource,
      csv_data: dataSource === 'csv' ? csvData : null,
      match_date: selectedFixture.date,
      venue: selectedFixture.venue,
    };
    await runPredictions(payload);
  };

  const handleBatchRun = async (selectedFixtures) => {
    const payloads = selectedFixtures.map(f => ({
      home_team: f.home_team,
      away_team: f.away_team,
      home_team_id: f.home_team_id,
      away_team_id: f.away_team_id,
      competition_code: f._compCode || selectedComp || 'PL',
      competition_name: f._compName || '',
      home_lineup: [], 
      away_lineup: [],
      home_subs: [],
      away_subs: [],
      home_position: 10,
      away_position: 10,
      match_importance: 1.0,
      data_source: dataSource,
      csv_data: dataSource === 'csv' ? csvData : null,
      match_date: f.date,
      venue: f.venue,
    }));
    await runBatchPredictions(payloads);
  };

  // ── Layout helpers ─────────────────────────────────────────────────────────
  const homeKey = mobilePanel === 'home' || undefined;
  const dashKey = mobilePanel === 'dashboard' || !['home', 'away', 'settings'].includes(mobilePanel);
  const awayKey = mobilePanel === 'away' || undefined;

  return (
    <div className="min-h-screen flex flex-col bg-bg-primary">
      <Header
        competitions={competitions}
        selectedComp={selectedComp}
        onCompChange={handleCompChange}
        fixtures={fixtures}
        selectedFixture={selectedFixture}
        onFixtureChange={handleFixtureChange}
        onCSVUpload={handleCSVUpload}
        loading={loading}
        onExport={exportExcel}
        hasPredictions={Boolean(predictionId)}
        loadingFixtures={loadingFixtures}
        loadingCompetitions={loadingCompetitions}
        isApiEnabled={isApiEnabled}
        onApiToggle={handleApiToggle}
        csvStatus={usePredictionStore.getState().csvStatus}
        fixtureError={squadError}
        onHistoryOpen={() => setHistoryOpen(true)}
        onMobileMatchSetup={() => setMatchSetupOpen(true)}
        mode={mode}
        onModeChange={(m) => { setMode(m); clearBatch(); clearBatchAll(); }}
        onRun={mode === 'single' ? handleRun : () => {
          // Read latest from store to avoid stale closure
          const store = usePredictionStore.getState();
          const currentIds = store.batchSelectedIds;
          const allFixtures = store.batchFixtures;
          const selected = allFixtures.filter(f => currentIds.includes(f.match_id));
          handleBatchRun(selected);
        }}
        canRun={mode === 'single' ? canRun : batchSelectedIds.length > 0}
        canSelectAll={mode === 'batch' && competitions.length > 0}
        onSelectAll={handleSelectAllLeagues}
      />

      {/* Error banner */}
      {(error || batchError) && (
        <div className="max-w-screen-2xl mx-auto w-full px-4 pt-3">
          <div className="flex items-center gap-2 bg-danger/10 border border-danger/30 rounded-lg px-4 py-2 text-sm text-danger">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error || batchError}
          </div>
        </div>
      )}

      {/* Main 3-column layout (desktop) / 1-column (mobile via tabs) */}
      <main className="flex-1 max-w-screen-2xl mx-auto w-full px-4 py-4 pb-20 md:pb-4
                        grid grid-cols-1 md:h-[calc(100vh-80px)] overflow-hidden
                        md:grid-cols-[320px_1fr] xl:grid-cols-[380px_1fr_380px] gap-6">

        {/* Left: Home Lineup / Batch Selector */}
        <div className={`h-full overflow-hidden ${mobilePanel !== 'home' ? 'hidden md:block' : 'block'}`}>
          {mode === 'single' ? (
            <ErrorBoundary componentName="Home Lineup">
              <LineupSelector
                side="home"
                teamName={selectedFixture?.home_team || ''}
                teamId={selectedFixture?.home_team_id}
                onLineupChange={handleHomeLineup}
                onFetchSquad={fetchSquad}
                loadingSquad={loadingSquad.home}
                injuries={injuries.filter(i => i.team?.name === (selectedFixture?.home_team || ''))}
              />
            </ErrorBoundary>
          ) : (
            <BatchMatchSelector 
               loading={batchLoading}
            />
          )}
        </div>

        {/* Center: Dashboard */}
        <div className={`h-full overflow-hidden ${mobilePanel !== 'dashboard' && ['home', 'away', 'settings'].includes(mobilePanel) ? 'hidden md:block' : 'block'}`}>
          <Dashboard
            predictions={predictions}
            loading={loading || batchLoading}
            homeTeam={selectedFixture?.home_team}
            awayTeam={selectedFixture?.away_team}
            batchMode={mode === 'batch'}
            batchResults={batchResults}
            onExportBatch={exportBatchExcel}
            batchExportLoading={batchExportLoading}
          />
        </div>

        {/* Right: Away Lineup — hidden on mobile when not away panel, and in batch mode */}
        <div className={`${mode === 'batch' ? 'hidden' : (mobilePanel !== 'away' ? 'hidden xl:block' : 'block')} h-full overflow-hidden`}>
          <ErrorBoundary componentName="Away Lineup">
            <LineupSelector
              side="away"
              teamName={selectedFixture?.away_team || ''}
              teamId={selectedFixture?.away_team_id}
              onLineupChange={handleAwayLineup}
              onFetchSquad={fetchSquad}
              loadingSquad={loadingSquad.away}
              injuries={injuries.filter(i => i.team?.name === (selectedFixture?.away_team || ''))}
            />
          </ErrorBoundary>
        </div>
      </main>

      {mode === 'single' && (
        <Footer
          modelStatus={modelStatus}
          dataSource={dataSource}
          onRun={handleRun}
          loading={loading}
          canRun={canRun}
        />
      )}

      {/* Mobile bottom navigation */}
      <MobileNav />

      {/* Mobile match setup drawer */}
      {matchSetupOpen && (
        <MatchSetupDrawer onClose={() => setMatchSetupOpen(false)}>
          <div className="space-y-3">
            <div className="flex items-center gap-2 bg-bg-elevated px-3 py-2 rounded-lg border border-[#2D3748]">
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest">API Mode</span>
              <button
                onClick={() => handleApiToggle(!isApiEnabled)}
                className={`relative w-10 h-5 rounded-full p-0.5 transition-colors ml-auto ${
                  isApiEnabled ? 'bg-accent-green' : 'bg-bg-primary border border-[#2D3748]'
                }`}
              >
                <div className={`w-4 h-4 rounded-full shadow-sm transform transition-transform ${
                  isApiEnabled ? 'translate-x-4 bg-bg-primary' : 'translate-x-0 bg-text-muted'
                }`} />
              </button>
            </div>
            <SearchableSelect
              options={competitions}
              value={selectedComp}
              onChange={(code) => { handleCompChange(code); }}
              placeholder="Select League"
              disabled={!isApiEnabled}
              loading={loadingCompetitions}
              iconKey="emblem" labelKey="name" valueKey="code"
            />
            <SearchableSelect
              options={fixtures.map(f => ({
                ...f,
                label: `${f.home_team} vs ${f.away_team} · ${formatMatchDate(f.date)}`,
                icon: f.home_logo || ''
              }))}
              value={selectedFixture?.match_id ?? ''}
              onChange={(val, opt) => { handleFixtureChange(opt); setMatchSetupOpen(false); }}
              placeholder="Select Match"
              disabled={!selectedComp || !isApiEnabled || loadingFixtures}
              labelKey="label" valueKey="match_id" iconKey="icon"
            />
            <CSVUploader onDataLoaded={(data) => { handleCSVUpload(data); setMatchSetupOpen(false); }} />
          </div>
        </MatchSetupDrawer>
      )}

      {/* Prediction History drawer */}
      <PredictionHistory />
    </div>
  );
}
