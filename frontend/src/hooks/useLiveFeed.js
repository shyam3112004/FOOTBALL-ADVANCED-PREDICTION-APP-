import { useState, useEffect, useCallback, useRef } from 'react';
import { multiApi } from '../services/MultiApiService';

/**
 * useLiveFeed Hook
 * Manages real-time data polling for live matches and advanced metrics.
 */
export function useLiveFeed(matchId = null, pollingInterval = 60000) {
  const [liveMatches, setLiveMatches] = useState([]);
  const [matchStats, setMatchStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  const fetchLive = useCallback(async () => {
    setLoading(true);
    try {
      const live = await multiApi.getLiveMatches();
      setLiveMatches(live);
      
      if (matchId) {
        const stats = await multiApi.getMatchAdvancedStats(matchId);
        setMatchStats(stats);
      }
    } catch (err) {
      setError('Live feed update failed');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [matchId]);

  // Handle Polling
  useEffect(() => {
    fetchLive(); // Initial fetch
    
    if (pollingInterval > 0) {
      timerRef.current = setInterval(fetchLive, pollingInterval);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [fetchLive, pollingInterval]);

  return {
    liveMatches,
    matchStats,
    loading,
    error,
    refresh: fetchLive
  };
}
