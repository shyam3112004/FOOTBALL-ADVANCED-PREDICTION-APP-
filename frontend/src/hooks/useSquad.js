import { useState, useCallback } from 'react';
import api from '../services/apiClient';
import { multiApi } from '../services/MultiApiService';

export function useSquad() {
  const [competitions, setCompetitions] = useState([]);
  const [fixtures, setFixtures] = useState([]);
  const [squad, setSquad] = useState({ home: null, away: null });
  const [loadingSquad, setLoadingSquad] = useState({ home: false, away: false });
  const [loadingFixtures, setLoadingFixtures] = useState(false);
  const [injuries, setInjuries] = useState([]);
  const [error, setError] = useState(null);

  const fetchCompetitions = useCallback(async () => {
    try {
      const { data } = await api.get('/api/competitions');
      setCompetitions(Array.isArray(data) ? data : []);
    } catch (err) {
      setError('Failed to load competitions');
    }
  }, []);

  const fetchFixtures = useCallback(async (competitionCode) => {
    setLoadingFixtures(true);
    setError(null);
    try {
      const { data } = await api.get(`/api/competitions/${competitionCode}/fixtures`);
      if (data.fixtures && data.fixtures[0]?.is_error) {
        setError(data.fixtures[0].error);
        setFixtures([]);
      } else {
        setFixtures(data.fixtures || []);
      }
    } catch (err) {
      setError('Failed to load fixtures');
      setFixtures([]);
    } finally {
      setLoadingFixtures(false);
    }
  }, []);

  const fetchSquad = useCallback(async (teamId, side) => {
    setLoadingSquad((s) => ({ ...s, [side]: true }));
    setError(null);
    try {
      const { data } = await api.get(`/api/teams/${teamId}/squad`);
      setSquad((s) => ({ ...s, [side]: data }));
      return data;
    } catch (err) {
      setError(`Failed to load ${side} squad`);
      return null;
    } finally {
      setLoadingSquad((s) => ({ ...s, [side]: false }));
    }
  }, []);

  const fetchMatchInjuries = useCallback(async (fixtureId) => {
    if (!fixtureId) return;
    try {
      const data = await multiApi.getInjuries(fixtureId);
      setInjuries(data);
    } catch (err) {
      console.error('Injury fetch error:', err);
    }
  }, []);

  return {
    competitions,
    fixtures,
    squad,
    loadingSquad,
    loadingFixtures,
    error,
    fetchCompetitions,
    fetchFixtures,
    fetchSquad,
    fetchMatchInjuries,
    injuries
  };
}
