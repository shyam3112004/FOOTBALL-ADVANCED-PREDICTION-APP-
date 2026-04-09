/**
 * Zustand store for Football Predictor Pro.
 *
 * Slices:
 *   predictions    – current prediction result + loading/error state
 *   history        – loaded from /api/predictions/history
 *   batchResults   – multi-match batch predictions
 *   selectedFixture / selectedComp
 *   competitions / fixtures
 *   modelStatus    – { is_trained, training_samples, metrics }
 *   ui             – drawer/panel visibility flags
 */

import { create } from 'zustand';

const usePredictionStore = create((set, get) => ({

  // ── predictions ─────────────────────────────────────────────────────────────
  predictions: null,
  predictionId: null,
  loading: false,
  error: null,

  setPredictions: (data) => set({
    predictions: data,
    predictionId: data?.prediction_id ?? null,
    error: null,
  }),
  setLoading: (v) => set({ loading: v }),
  setError: (msg) => set({ error: msg }),
  clearPredictions: () => set({ predictions: null, predictionId: null, error: null }),

  // ── history drawer ─────────────────────────────────────────────────────────
  history: [],
  historyLoading: false,
  historyOpen: false,

  setHistory: (rows) => set({ history: rows }),
  setHistoryLoading: (v) => set({ historyLoading: v }),
  setHistoryOpen: (v) => set({ historyOpen: v }),

  // ── competitions / fixtures ─────────────────────────────────────────────────
  competitions: [],
  fixtures: [],
  loadingCompetitions: false,
  loadingFixtures: false,
  fixtureError: null,

  setCompetitions: (list) => set({ competitions: list }),
  setFixtures: (list) => set({ fixtures: list }),
  setLoadingCompetitions: (v) => set({ loadingCompetitions: v }),
  setLoadingFixtures: (v) => set({ loadingFixtures: v }),
  setFixtureError: (msg) => set({ fixtureError: msg }),

  // ── selected match ──────────────────────────────────────────────────────────
  selectedComp: '',
  selectedFixture: null,

  setSelectedComp: (code) => set({ selectedComp: code, selectedFixture: null }),
  setSelectedFixture: (fixture) => set({ selectedFixture: fixture }),

  // ── squad / injuries ────────────────────────────────────────────────────────
  squad: { home: null, away: null },
  loadingSquad: { home: false, away: false },
  injuries: [],

  setSquad: (side, data) => set((s) => ({ squad: { ...s.squad, [side]: data } })),
  setLoadingSquad: (side, v) => set((s) => ({ loadingSquad: { ...s.loadingSquad, [side]: v } })),
  setInjuries: (list) => set({ injuries: list }),

  // ── lineups ─────────────────────────────────────────────────────────────────
  homeLineup: [],
  homeSubs: [],
  awayLineup: [],
  awaySubs: [],

  setHomeLineup: (starters, subs) => set({ homeLineup: starters, homeSubs: subs }),
  setAwayLineup: (starters, subs) => set({ awayLineup: starters, awaySubs: subs }),

  // ── model status ────────────────────────────────────────────────────────────
  modelStatus: { is_trained: false, training_samples: 0, metrics: {} },
  setModelStatus: (s) => set({ modelStatus: s }),

  // ── data source ─────────────────────────────────────────────────────────────
  dataSource: 'api',
  isApiEnabled: true,
  csvData: null,
  csvStatus: 'idle', // idle | success | error

  setDataSource: (src) => set({ dataSource: src }),
  setApiEnabled: (v) => set({ isApiEnabled: v, dataSource: v ? 'api' : 'csv' }),
  setCsvData: (data) => set({ csvData: data, csvStatus: 'success' }),

  // ── UI flags ────────────────────────────────────────────────────────────────
  mobilePanel: 'dashboard',     // 'home' | 'dashboard' | 'away' | 'settings'
  matchSetupOpen: false,        // mobile slide-up drawer

  setMobilePanel: (panel) => set({ mobilePanel: panel }),
  setMatchSetupOpen: (v) => set({ matchSetupOpen: v }),

  // ── standings ────────────────────────────────────────────────────────────────
  standings: [],
  setStandings: (list) => set({ standings: list }),
  // ── mode ───────────────────────────────────────────────────────────────────
  mode: 'single', // 'single' | 'batch'
  setMode: (m) => set({ mode: m }),

  // ── batch selection ────────────────────────────────────────────────────────
  batchSelectedIds: [],
  setBatchSelectedIds: (ids) => set({ batchSelectedIds: Array.isArray(ids) ? ids : [...ids] }),
  clearBatchSelection: () => set({ batchSelectedIds: [] }),

  // ── batch multi-league fixtures ────────────────────────────────────────────
  batchFixtures: [],       // fixtures accumulated from multiple leagues
  batchComps: [],          // [{ code, name, emblem }] selected leagues
  batchLoadingFixtures: false,
  setBatchFixtures: (list) => set({ batchFixtures: list }),
  addBatchFixtures: (leagueFixtures) => set((s) => ({
    batchFixtures: [...s.batchFixtures, ...leagueFixtures],
  })),
  removeBatchComp: (code) => set((s) => ({
    batchComps: s.batchComps.filter(c => c.code !== code),
    batchFixtures: s.batchFixtures.filter(f => f._compCode !== code),
    batchSelectedIds: s.batchSelectedIds.filter(id =>
      s.batchFixtures.find(f => f.match_id === id && f._compCode !== code) ? true :
      !s.batchFixtures.find(f => f.match_id === id)
    ),
  })),
  addBatchComp: (comp) => set((s) => ({
    batchComps: s.batchComps.some(c => c.code === comp.code) ? s.batchComps : [...s.batchComps, comp],
  })),
  setBatchLoadingFixtures: (v) => set({ batchLoadingFixtures: v }),
  clearBatchAll: () => set({ batchSelectedIds: [], batchFixtures: [], batchComps: [] }),

  // ── batch filters ────────────────────────────────────────────────────────
  batchMinProb: 70,
  batchTargetMarket: 'double_chance',
  setBatchMinProb: (v) => set({ batchMinProb: v }),
  setBatchTargetMarket: (v) => set({ batchTargetMarket: v }),
}));

export default usePredictionStore;
