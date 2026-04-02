import { useState, useCallback } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, X, Eye } from 'lucide-react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function CSVUploader({ onDataLoaded }) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | uploading | success | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [showPreview, setShowPreview] = useState(false);

  const processFile = useCallback(async (f) => {
    if (!f?.name.endsWith('.csv')) {
      setError('Please upload a .csv file');
      setStatus('error');
      return;
    }
    setFile(f);
    setStatus('uploading');
    setError('');

    const formData = new FormData();
    formData.append('file', f);

    try {
      const { data } = await axios.post(`${API_BASE}/api/upload-csv`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 30000,
      });
      setResult(data);
      setStatus('success');
      if (onDataLoaded) {
        onDataLoaded(data.data || []);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Upload failed');
      setStatus('error');
    }
  }, [onDataLoaded]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) processFile(f);
  }, [processFile]);

  const onFileInput = (e) => {
    const f = e.target.files[0];
    if (f) processFile(f);
  };

  const reset = () => {
    setFile(null);
    setStatus('idle');
    setResult(null);
    setError('');
    setShowPreview(false);
  };

  return (
    <div className="space-y-3">
      {/* Drop Zone */}
      {status === 'idle' && (
        <label
          className={`drop-zone flex flex-col items-center justify-center p-6 cursor-pointer ${isDragging ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
        >
          <input type="file" accept=".csv" className="hidden" onChange={onFileInput} />
          <Upload className={`w-8 h-8 mb-2 transition-colors ${isDragging ? 'text-accent-green' : 'text-text-muted'}`} />
          <div className="text-sm font-semibold text-text-primary">
            Drop CSV or <span className="text-accent-green">browse</span>
          </div>
          <div className="text-xs text-text-muted mt-1 text-center">
            football-data.co.uk format supported
          </div>
        </label>
      )}

      {/* Uploading */}
      {status === 'uploading' && (
        <div className="prediction-card flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-accent-green border-t-transparent rounded-full animate-spin shrink-0" />
          <div>
            <div className="text-sm font-semibold text-text-primary">Processing {file?.name}…</div>
            <div className="text-xs text-text-muted">Parsing columns and validating data</div>
          </div>
        </div>
      )}

      {/* Error */}
      {status === 'error' && (
        <div className="prediction-card border-danger/30 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-danger shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="text-sm font-semibold text-danger">Upload Failed</div>
            <div className="text-xs text-text-muted mt-0.5">{error}</div>
          </div>
          <button onClick={reset} className="text-text-muted hover:text-text-primary">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Success */}
      {status === 'success' && result && (
        <div className="prediction-card border-accent-green/30 space-y-3 animate-slide-up bg-accent-green/5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-accent-green/20 flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-accent-green" />
              </div>
              <div>
                <span className="text-sm font-bold text-accent-green block uppercase tracking-wide">Data Loaded</span>
                <span className="text-[10px] text-text-muted">CSV processed successfully</span>
              </div>
            </div>
            <button onClick={reset} className="text-text-muted hover:text-text-primary transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-bg-elevated rounded-lg p-2">
              <div className="text-text-muted">Matches</div>
              <div className="font-bold text-text-primary text-lg">{result.rows}</div>
            </div>
            <div className="bg-bg-elevated rounded-lg p-2">
              <div className="text-text-muted">Columns Found</div>
              <div className="font-bold text-text-primary text-lg">{result.columns_found?.length || 0}</div>
            </div>
          </div>

          {/* Warnings */}
          {result.warnings?.length > 0 && (
            <div className="text-xs text-warning bg-warning/10 rounded-lg p-2">
              ⚠ {result.warnings[0]}
            </div>
          )}

          {/* Preview toggle */}
          <button
            onClick={() => setShowPreview(!showPreview)}
            className="flex items-center gap-1.5 text-xs text-accent-blue hover:text-accent-blue/80 transition-colors"
          >
            <Eye className="w-3.5 h-3.5" />
            {showPreview ? 'Hide' : 'Show'} column preview
          </button>

          {/* Column preview table */}
          {showPreview && result.column_preview && (
            <div className="overflow-x-auto">
              <table className="text-xs w-full">
                <thead>
                  <tr className="text-left text-text-muted border-b border-[#1F2937]">
                    <th className="pb-1 pr-3">Column</th>
                    <th className="pb-1 pr-3">Type</th>
                    <th className="pb-1">Sample</th>
                  </tr>
                </thead>
                <tbody>
                  {result.column_preview.slice(0, 10).map((col) => (
                    <tr key={col.name} className="border-b border-[#1F2937]/50">
                      <td className="py-1 pr-3 font-mono text-accent-green">{col.name}</td>
                      <td className="py-1 pr-3 text-text-muted">{col.type}</td>
                      <td className="py-1 text-text-secondary">{col.sample?.join(', ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* File name */}
          <div className="flex items-center gap-1.5 text-xs text-text-muted">
            <FileText className="w-3 h-3" />
            {file?.name}
          </div>
        </div>
      )}
    </div>
  );
}
