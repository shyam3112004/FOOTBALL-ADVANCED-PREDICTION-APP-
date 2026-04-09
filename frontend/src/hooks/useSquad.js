import { useCallback } from 'react';
import api from '../services/apiClient';
import usePredictionStore from '../store/predictionStore';

/**
 * useSquad — Zustand-backed squad/squad/injuries fetcher.
 *
 * KEY CHANGE from original: Injuries now go through the backend proxy
 * endpoint (/api/matches/{id}/injuries) — NOT through MultiApiService
 * in the browser, so API keys are never exposed.
 */
export function useSquad() {
  const competitions = usePredictionStore(state => state.competitions);
  const fixtures = usePredictionStore(state => state.fixtures);
  const squad = usePredictionStore(state => state.squad);
  const loadingSquad = usePredictionStore(state => state.loadingSquad);
  const loadingCompetitions = usePredictionStore(state => state.loadingCompetitions);
  const loadingFixtures = usePredictionStore(state => state.loadingFixtures);
  const injuries = usePredictionStore(state => state.injuries);
  const fixtureError = usePredictionStore(state => state.fixtureError);

  const setCompetitions = usePredictionStore(state => state.setCompetitions);
  const setFixtures = usePredictionStore(state => state.setFixtures);
  const setLoadingCompetitions = usePredictionStore(state => state.setLoadingCompetitions);
  const setLoadingFixtures = usePredictionStore(state => state.setLoadingFixtures);
  const setFixtureError = usePredictionStore(state => state.setFixtureError);
  const setSquad = usePredictionStore(state => state.setSquad);
  const setLoadingSquad = usePredictionStore(state => state.setLoadingSquad);
  const setInjuries = usePredictionStore(state => state.setInjuries);

  const fetchCompetitions = useCallback(async () => {
    setLoadingCompetitions(true);
    try {
      const { data } = await api.get('/api/competitions');
      setCompetitions(Array.isArray(data) ? data : []);
    } catch {
      setFixtureError('Failed to load competitions');
    } finally {
      setLoadingCompetitions(false);
    }
  }, [setCompetitions, setLoadingCompetitions, setFixtureError]);

  const fetchFixtures = useCallback(async (competitionCode) => {
    setLoadingFixtures(true);
    setFixtureError(null);
    try {
      const { data } = await api.get(`/api/competitions/${competitionCode}/fixtures`);
      if (data.fixtures?.[0]?.is_error) {
        setFixtureError(data.fixtures[0].error);
        setFixtures([]);
      } else {
        setFixtures(data.fixtures || []);
      }
    } catch {
      setFixtureError('Failed to load fixtures');
      setFixtures([]);
    } finally {
      setLoadingFixtures(false);
    }
  }, [setFixtures, setLoadingFixtures, setFixtureError]);

  const fetchSquad = useCallback(async (teamId, side) => {
    setLoadingSquad(side, true);
    setFixtureError(null);
    try {
      const { data } = await api.get(`/api/teams/${teamId}/squad`);
      setSquad(side, data);
      return data;
    } catch {
      setFixtureError(`Failed to load ${side} squad`);
      return null;
    } finally {
      setLoadingSquad(side, false);
    }
  }, [setSquad, setLoadingSquad, setFixtureError]);

  const fetchMatchInjuries = useCallback(async (fixtureId) => {
    if (!fixtureId) return;
    try {
      // ✅ Backend proxy — never exposes API keys to the browser
      const { data } = await api.get(`/api/matches/${fixtureId}/injuries`);
      setInjuries(data.injuries || []);
    } catch (err) {
      console.error('Injury fetch error:', err);
    }
  }, [setInjuries]);

  // Expose the same interface as before so App.jsx doesn't need to change
  const error = fixtureError;

  return {
    competitions,
    fixtures,
    squad,
    loadingSquad,
    loadingCompetitions,
    loadingFixtures,
    injuries,
    error,
    fetchCompetitions,
    fetchFixtures,
    fetchSquad,
    fetchMatchInjuries,
  };
}
