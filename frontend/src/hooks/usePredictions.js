import { useState, useCallback } from 'react';
import api from '../services/apiClient';

export function usePredictions() {
  const [predictions, setPredictions] = useState(null);
  const [predictionId, setPredictionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [modelStatus, setModelStatus] = useState({
    is_trained: false,
    training_samples: 0,
  });

  const runPredictions = useCallback(async (payload) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.post('/api/predict', payload);
      setPredictions(data);
      setPredictionId(data.prediction_id);
      setModelStatus({
        is_trained: data.is_trained,
        training_samples: data.training_samples,
      });
      return data;
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Prediction failed';
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const exportExcel = useCallback(async () => {
    if (!predictionId) return;
    try {
      const resp = await api.get(`/api/export/${predictionId}`, {
        responseType: 'blob',
      });
      const url = URL.createObjectURL(new Blob([resp.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `prediction_${predictionId.slice(0, 8)}.xlsx`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError('Export failed: ' + (err.message || ''));
    }
  }, [predictionId]);

  const fetchModelStatus = useCallback(async () => {
    try {
      const { data } = await api.get('/api/model/status');
      setModelStatus(data);
    } catch {}
  }, []);

  const trainCompetition = useCallback(async (code) => {
    try {
      await api.post(`/api/train/competition/${code}`);
      await fetchModelStatus();
    } catch {}
  }, [fetchModelStatus]);

  const clearPredictions = useCallback(() => {
    setPredictions(null);
    setPredictionId(null);
    setError(null);
  }, []);

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
