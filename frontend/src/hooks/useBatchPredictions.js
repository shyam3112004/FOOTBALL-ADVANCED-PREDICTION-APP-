import { useState, useCallback } from 'react';
import api from '../services/apiClient';

export function useBatchPredictions() {
  const [batchResults, setBatchResults] = useState([]);
  const [batchId, setBatchId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState({ current: 0, total: 0 });

  const runBatchPredictions = useCallback(async (payloads) => {
    setLoading(true);
    setError(null);
    setBatchResults([]);
    setBatchId(null);
    setProgress({ current: 0, total: payloads.length });

    try {
      const response = await api.post('/api/predict/batch', {
        matches: payloads
      }, {
        timeout: 300000 // 5 minutes specifically for batch
      });
      
      console.log('Batch API Response:', response.data);
      const { batch_id, results } = response.data;
      setBatchId(batch_id);
      setBatchResults(results || []);
      setProgress({ current: payloads.length, total: payloads.length });
    } catch (err) {
      console.error('Batch prediction failed:', err);
      setError(err.response?.data?.detail || 'Failed to run batch predictions');
    } finally {
      setLoading(false);
    }
  }, []);

  const exportBatchExcel = useCallback(async (maybeFilters) => {
    // maybeFilters can be a click event or an object with { minProb, market }
    let filters = { minProb: 0, market: 'any' };
    if (maybeFilters && typeof maybeFilters === 'object' && !maybeFilters.nativeEvent) {
      filters = { ...filters, ...maybeFilters };
    }

    if (!batchId) {
      console.warn('Batch export failed: No current batch ID');
      return;
    }

    setExportLoading(true);
    setError(null); // Clear previous errors
    
    try {
      console.log(`Starting export for batch ${batchId} with filters:`, filters);
      const { minProb, market } = filters;
      const response = await api.get(`/api/export/batch/${batchId}`, {
        params: { min_prob: minProb, market: market },
        responseType: 'blob',
        timeout: 300000 // 5 minutes for large excel generation
      });
      
      if (!response.data) throw new Error('No data received from server');

      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      // Fixed: targetId -> batchId
      const filename = `batch_prediction_${batchId.slice(0, 8)}.xlsx`;
      link.setAttribute('download', filename);
      
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      setTimeout(() => {
        link.remove();
        window.URL.revokeObjectURL(url);
      }, 100);

      console.log('Batch export successful');
    } catch (err) {
      console.error('Batch export failed:', err);
      
      // Try to parse JSON error from Blob
      if (err.response && err.response.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          const errorData = JSON.parse(text);
          setError(errorData.detail || 'Export failed');
        } catch (e) {
          setError('Excel export failed. Please try again.');
        }
      } else {
        setError(err.response?.data?.detail || 'Excel export failed. Please try again.');
      }
    } finally {
      setExportLoading(false);
    }
  }, [batchId]);

  const clearBatch = useCallback(() => {
    setBatchResults([]);
    setBatchId(null);
    setError(null);
    setProgress({ current: 0, total: 0 });
    setExportLoading(false);
  }, []);

  return {
    batchResults,
    batchId,
    loading,
    exportLoading,
    error,
    progress,
    runBatchPredictions,
    exportBatchExcel,
    clearBatch
  };
}
