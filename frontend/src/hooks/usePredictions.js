import { useCallback } from 'react';
import api from '../services/apiClient';
import usePredictionStore from '../store/predictionStore';

/**
 * usePredictions — reads/writes to Zustand store instead of local useState.
 * Keeps the same public interface so App.jsx callers are unchanged.
 */
export function usePredictions() {
  const predictions = usePredictionStore(state => state.predictions);
  const predictionId = usePredictionStore(state => state.predictionId);
  const loading = usePredictionStore(state => state.loading);
  const error = usePredictionStore(state => state.error);
  const modelStatus = usePredictionStore(state => state.modelStatus);

  const setPredictions = usePredictionStore(state => state.setPredictions);
  const setLoading = usePredictionStore(state => state.setLoading);
  const setError = usePredictionStore(state => state.setError);
  const clearPredictions = usePredictionStore(state => state.clearPredictions);
  const setModelStatus = usePredictionStore(state => state.setModelStatus);

  const runPredictions = useCallback(async (payload) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.post('/api/predict', payload);
      setPredictions(data);
      setModelStatus({
        is_trained:       data.is_trained,
        training_samples: data.training_samples,
        metrics:          data.metrics || {},
      });
      return data;
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Prediction failed';
      setError(Array.isArray(msg)
        ? msg.map((e) => e.msg ?? JSON.stringify(e)).join(', ')
        : msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, setPredictions, setModelStatus]);

  const exportExcel = useCallback(async () => {
    if (!predictionId) return;
    try {
      const resp = await api.get(`/api/export/${predictionId}`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([resp.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `prediction_${predictionId.slice(0, 8)}.xlsx`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError('Export failed: ' + (err.message || ''));
    }
  }, [predictionId, setError]);

  const fetchModelStatus = useCallback(async () => {
    try {
      const { data } = await api.get('/api/model/status');
      setModelStatus(data);
    } catch { /* silent */ }
  }, [setModelStatus]);

  const trainCompetition = useCallback(async (code) => {
    try {
      await api.post(`/api/train/competition/${code}`);
      await fetchModelStatus();
    } catch { /* silent */ }
  }, [fetchModelStatus]);

  return {
    predictions,
    predictionId,
    loading,
    error,
    modelStatus,
    runPredictions,
    exportExcel,
    fetchModelStatus,
    trainCompetition,
    clearPredictions,
  };
}
