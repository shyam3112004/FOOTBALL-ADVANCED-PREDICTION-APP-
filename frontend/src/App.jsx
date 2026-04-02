import { useState, useCallback, useEffect } from 'react';
import api from './services/apiClient';
import {
  Activity, Upload, Download, ChevronDown, Zap,
  AlertCircle, X, Trophy, Database, Loader2
} from 'lucide-react';

import Dashboard from './pages/Dashboard';
import LineupSelector from './components/LineupSelector';
import CSVUploader from './components/CSVUploader';
import SearchableSelect from './components/SearchableSelect';
import { usePredictions } from './hooks/usePredictions';
import { useSquad } from './hooks/useSquad';
import { toPercent } from './utils/oddsConverter';
import { formatMatchDate } from './utils/dateUtils';

// ─── Header ──────────────────────────────────────────────────────────────────

function Header({
  competitions, selectedComp, onCompChange,
  fixtures, selectedFixture, onFixtureChange,
  onCSVUpload, loading, onExport, hasPredictions,
  loadingFixtures, isApiEnabled, onApiToggle,
  csvStatus, fixtureError
}) {
  const [showCSV, setShowCSV] = useState(false);

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

        {/* API Toggle */}
        <div className="flex items-center gap-2 bg-bg-elevated px-3 py-1.5 rounded-lg border border-[#2D3748]">
          <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest whitespace-nowrap">API Mode</span>
          <button
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

        {/* Competition selector */}
        <div className="w-64 shrink-0">
          <SearchableSelect
            options={competitions}
            value={selectedComp}
            onChange={onCompChange}
            placeholder={isApiEnabled ? 'Select League' : 'API Disabled'}
            disabled={!isApiEnabled}
            iconKey="emblem"
            labelKey="name"
            valueKey="code"
          />
        </div>

        {/* Fixture selector */}
        <div className="flex-1 min-w-[320px] max-w-[480px]">
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

        <div className="flex items-center gap-2 ml-auto">
          {/* CSV Upload */}
          <div className="relative">
            <button
              onClick={() => setShowCSV(!showCSV)}
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
            {showCSV && (
              <div className="absolute right-0 top-10 z-50 w-80 bg-bg-elevated border border-[#1F2937] rounded-xl shadow-2xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-semibold text-text-primary">Upload CSV Data</span>
                  <button onClick={() => setShowCSV(false)}>
                    <X className="w-4 h-4 text-text-muted" />
                  </button>
                </div>
                <CSVUploader onDataLoaded={(data) => { onCSVUpload(data); setShowCSV(false); }} />
              </div>
            )}
          </div>

          {/* Export */}
          {hasPredictions && (
            <button
              onClick={onExport}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bg-elevated border border-accent-blue/40 hover:border-accent-blue text-sm text-accent-blue hover:text-accent-blue transition-all"
            >
              <Download className="w-4 h-4" />
              Export XLS
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

// ─── Footer ──────────────────────────────────────────────────────────────────

function Footer({ modelStatus, dataSource, onRun, loading, canRun }) {
  return (
    <footer className="glass border-t border-[#1F2937] px-4 py-3">
      <div className="max-w-screen-2xl mx-auto flex items-center gap-4 flex-wrap">
        {/* Model status */}
        <div className="flex items-center gap-2 text-xs">
          <Activity className="w-3.5 h-3.5 text-accent-green" />
          <span className="text-text-muted">Model:</span>
          <span className={modelStatus.is_trained ? 'text-accent-green font-semibold' : 'text-warning font-semibold'}>
            {modelStatus.is_trained
              ? `Trained (${modelStatus.training_samples} matches)`
              : 'Heuristic fallback (upload CSV to train)'}
          </span>
        </div>

        {/* Data source */}
        <div className="flex items-center gap-2 text-xs">
          <Database className="w-3.5 h-3.5 text-accent-blue" />
          <span className="text-text-muted">Source:</span>
          <span className="text-text-secondary font-semibold capitalize">{dataSource}</span>
        </div>

        {/* Run button */}
        <div className="ml-auto">
          <button
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
    competitions, fixtures, squad,
    loadingSquad, loadingFixtures,
    fetchCompetitions, fetchFixtures, fetchSquad,
    fetchMatchInjuries, injuries, error: squadError
  } = useSquad();

  const [selectedComp, setSelectedComp] = useState('');
  const [selectedFixture, setSelectedFixture] = useState(null);
  const [standings, setStandings] = useState([]);
  const [homeLineup, setHomeLineup] = useState([]);
  const [homeSubs, setHomeSubs] = useState([]);
  const [awayLineup, setAwayLineup] = useState([]);
  const [awaySubs, setAwaySubs] = useState([]);
  const [csvData, setCsvData] = useState(null);
  const [csvStatus, setCsvStatus] = useState('idle'); // idle | loading | success | error
  const [dataSource, setDataSource] = useState('api');
  const [isApiEnabled, setIsApiEnabled] = useState(true);

  // Load competitions on mount
  useEffect(() => {
    fetchCompetitions();
    fetchModelStatus();
  }, [fetchCompetitions, fetchModelStatus]);

  // Fetch fixtures and standings when competition changes
  const handleCompChange = async (code) => {
    setSelectedComp(code);
    setSelectedFixture(null);
    setStandings([]);
    if (code) {
      fetchFixtures(code);
      trainCompetition(code);
      try {
        const { data } = await api.get(`/api/competitions/${code}/standings`);
        setStandings(data.standings || []);
      } catch (err) {
        console.error('Failed to fetch standings', err);
      }
    }
  };

  const handleFixtureChange = (fixture) => {
    setSelectedFixture(fixture);
    if (fixture?.match_id) {
       fetchMatchInjuries(fixture.match_id); 
       // Automatically fetch squads for both teams
       if (fixture.home_team_id) fetchSquad(fixture.home_team_id, 'home');
       if (fixture.away_team_id) fetchSquad(fixture.away_team_id, 'away');
    }
  }

  // Lineup change handlers
  const handleHomeLineup = useCallback((starters, subs) => {
    setHomeLineup(starters);
    setHomeSubs(subs);
  }, []);

  const handleAwayLineup = useCallback((starters, subs) => {
    setAwayLineup(starters);
    setAwaySubs(subs);
  }, []);

  const handleCSVUpload = (data) => {
    setCsvData(data);
    setCsvStatus('success');
    if (!isApiEnabled) {
      setDataSource('csv');
    }
  };

  const handleApiToggle = (val) => {
    setIsApiEnabled(val);
    setDataSource(val ? 'api' : 'csv');
  };

  const canRun = Boolean(
    selectedFixture?.home_team && selectedFixture?.away_team
  );

  const handleRun = async () => {
    if (!selectedFixture) return;

    const findPos = (teamId) => standings.find(s => s.team_id === teamId)?.position || 10;

    const payload = {
      home_team: selectedFixture.home_team,
      away_team: selectedFixture.away_team,
      home_team_id: selectedFixture.home_team_id,
      away_team_id: selectedFixture.away_team_id,
      competition_code: selectedComp || 'PL',
      home_lineup: homeLineup.filter((p) => p.name),
      away_lineup: awayLineup.filter((p) => p.name),
      home_subs: homeSubs.filter((p) => p.name),
      away_subs: awaySubs.filter((p) => p.name),
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
        isApiEnabled={isApiEnabled}
        onApiToggle={handleApiToggle}
        csvStatus={csvStatus}
        fixtureError={squadError}
      />

      {/* Error banner */}
      {error && (
        <div className="max-w-screen-2xl mx-auto w-full px-4 pt-3">
          <div className="flex items-center gap-2 bg-danger/10 border border-danger/30 rounded-lg px-4 py-2 text-sm text-danger">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        </div>
      )}

      {/* Main 3-column layout */}
      <main className="flex-1 max-w-screen-2xl mx-auto w-full px-4 py-4 grid grid-cols-1 xl:grid-cols-[380px_1fr_380px] gap-6">
        {/* Left: Home Lineup */}
        <div className="xl:block">
          <LineupSelector
            side="home"
            teamName={selectedFixture?.home_team || ''}
            teamId={selectedFixture?.home_team_id}
            onLineupChange={handleHomeLineup}
            onFetchSquad={fetchSquad}
            loadingSquad={loadingSquad.home}
            injuries={injuries.filter(i => i.team.name === (selectedFixture?.home_team || ''))}
          />
        </div>

        {/* Center: Dashboard */}
        <div className="min-h-[600px]">
          <Dashboard
            predictions={predictions}
            loading={loading}
            homeTeam={selectedFixture?.home_team}
            awayTeam={selectedFixture?.away_team}
          />
        </div>

        {/* Right: Away Lineup */}
        <div className="xl:block">
          <LineupSelector
            side="away"
            teamName={selectedFixture?.away_team || ''}
            teamId={selectedFixture?.away_team_id}
            onLineupChange={handleAwayLineup}
            onFetchSquad={fetchSquad}
            loadingSquad={loadingSquad.away}
            injuries={injuries.filter(i => i.team.name === (selectedFixture?.away_team || ''))}
          />
        </div>
      </main>

      <Footer
        modelStatus={modelStatus}
        dataSource={dataSource}
        onRun={handleRun}
        loading={loading}
        canRun={canRun}
      />
    </div>
  );
}
