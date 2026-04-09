import { useState, useEffect, useCallback, useRef } from 'react';
import api from '../services/apiClient';

/**
 * useLiveFeed Hook — smart, tab-aware polling.
 *
 * Improvements:
 *  1. Only polls when the "live" tab is active (activeTab === 'live')
 *  2. Pauses polling when the browser tab is hidden (visibilitychange)
 *  3. Exposes lastUpdated timestamp
 *  4. Uses backend proxy endpoints instead of MultiApiService
 *
 * @param {number|string|null} matchId  - fixture ID to fetch stats for
 * @param {string}             activeTab - current dashboard tab
 * @param {number}             pollingInterval - ms between polls (default 60s)
 */
export function useLiveFeed(matchId = null, activeTab = 'result', pollingInterval = 60000) {
  const [liveMatches, setLiveMatches] = useState([]);
  const [matchStats, setMatchStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const timerRef = useRef(null);

  const isLiveTabActive = activeTab === 'live';
  const isPageVisible = useRef(true);

  // Track page visibility
  useEffect(() => {
    const handleVisibility = () => {
      isPageVisible.current = document.visibilityState === 'visible';
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);

  const fetchLive = useCallback(async () => {
    // ── Guard: only poll when live tab is shown and page is visible ────────
    if (!isLiveTabActive || !isPageVisible.current) return;

    setLoading(true);
    try {
      // Backend proxy instead of direct API-Football call
      const { data } = await api.get('/api/live');
      setLiveMatches(data.matches || []);

      if (matchId) {
        // No Sportmonks proxy yet — show graceful empty state
        setMatchStats(null);
      }
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      setError('Live feed unavailable');
    } finally {
      setLoading(false);
    }
  }, [matchId, isLiveTabActive]);

  // Setup / teardown interval when live tab becomes active
  useEffect(() => {
    if (!isLiveTabActive) {
      // Clear interval when not on live tab
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    fetchLive();

    if (pollingInterval > 0) {
      timerRef.current = setInterval(fetchLive, pollingInterval);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
    };
  }, [fetchLive, isLiveTabActive, pollingInterval]);

  return {
    liveMatches,
    matchStats,
    loading,
    error,
    lastUpdated,
    refresh: fetchLive,
  };
}
