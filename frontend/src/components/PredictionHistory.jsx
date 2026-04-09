import { useEffect, useCallback } from 'react';
import { X, Clock, Trash2, ChevronRight, TrendingUp } from 'lucide-react';
import api from '../services/apiClient';
import usePredictionStore from '../store/predictionStore';
import { toPercent } from '../utils/oddsConverter';
import { probToColor } from '../utils/colorScale';

/**
 * PredictionHistory — slide-in right drawer showing last 20 predictions.
 *
 * - Fetches from GET /api/predictions/history
 * - Click an item to re-load those predictions into Dashboard
 * - "Clear History" calls DELETE /api/predictions/history
 */
export default function PredictionHistory() {
  const {
    historyOpen, setHistoryOpen,
    history, setHistory, historyLoading, setHistoryLoading,
    setPredictions,
  } = usePredictionStore();

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const { data } = await api.get('/api/predictions/history?limit=20');
      setHistory(data.predictions || []);
    } catch {
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  }, [setHistory, setHistoryLoading]);

  useEffect(() => {
    if (historyOpen) fetchHistory();
  }, [historyOpen, fetchHistory]);

  const handleClear = async () => {
    try {
      await api.delete('/api/predictions/history');
      setHistory([]);
    } catch { /* silent */ }
  };

  const handleLoadItem = (row) => {
    if (row.result && Object.keys(row.result).length > 0) {
      setPredictions({ ...row.result, prediction_id: row.prediction_id });
    }
    setHistoryOpen(false);
  };

  if (!historyOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm animate-fade-in"
        onClick={() => setHistoryOpen(false)}
        aria-hidden="true"
      />

      {/* Drawer */}
      <aside
        id="prediction-history-drawer"
        role="complementary"
        aria-label="Prediction History"
        className="fixed top-0 right-0 bottom-0 z-50 w-80 flex flex-col
                   glass border-l border-[#1F2937] animate-slide-up"
        style={{ animation: 'slideInRight 0.25s ease-out' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-4
                        border-b border-[#1F2937] shrink-0">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-accent-green" />
            <span className="font-heading font-bold text-sm text-text-primary uppercase tracking-widest">
              History
            </span>
            {history.length > 0 && (
              <span className="text-[10px] text-text-muted bg-bg-elevated
                               px-1.5 py-0.5 rounded-full border border-[#2D3748]">
                {history.length}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {history.length > 0 && (
              <button
                id="clear-history-btn"
                onClick={handleClear}
                className="flex items-center gap-1 text-xs text-text-muted
                           hover:text-danger transition-colors"
                title="Clear all history"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Clear
              </button>
            )}
            <button
              id="close-history-drawer"
              onClick={() => setHistoryOpen(false)}
              className="p-1.5 rounded-lg bg-bg-elevated border border-[#2D3748]
                         text-text-muted hover:text-text-primary transition-all"
              aria-label="Close history drawer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {historyLoading && (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="skeleton h-20 w-full rounded-lg" />
              ))}
            </div>
          )}

          {!historyLoading && history.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full
                            text-center py-12 space-y-2">
              <Clock className="w-10 h-10 text-text-muted opacity-20" />
              <p className="text-sm text-text-muted">No predictions yet</p>
            </div>
          )}

          {!historyLoading && history.map((row) => {
            const mr = row.result?.match_result || {};
            const tg = row.result?.total_goals || {};
            const cs = row.result?.correct_scores || [];
            const topScore = cs[0]?.score || '—';

            return (
              <button
                key={row.prediction_id}
                id={`history-item-${row.prediction_id?.slice(0, 8)}`}
                onClick={() => handleLoadItem(row)}
                className="w-full text-left bg-bg-elevated rounded-xl p-3
                           border border-[#1F2937] hover:border-accent-green/40
                           transition-all group space-y-2"
              >
                {/* Teams */}
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm text-text-primary truncate max-w-[160px]">
                    {row.home_team} <span className="text-text-muted font-normal">vs</span> {row.away_team}
                  </span>
                  <ChevronRight className="w-3.5 h-3.5 text-text-muted
                                          group-hover:text-accent-green transition-colors shrink-0" />
                </div>

                {/* Date + top score */}
                <div className="flex items-center gap-2 text-[10px] text-text-muted">
                  <TrendingUp className="w-3 h-3" />
                  <span>Top score: <strong className="text-text-secondary">{topScore}</strong></span>
                  {tg.predicted && (
                    <span className="ml-auto">~{Number(tg.predicted).toFixed(1)} goals</span>
                  )}
                </div>

                {/* Probability mini bars */}
                {(mr.home || mr.draw || mr.away) && (
                  <div className="flex gap-1 items-center">
                    {[
                      { label: 'H', prob: mr.home },
                      { label: 'D', prob: mr.draw },
                      { label: 'A', prob: mr.away },
                    ].map(({ label, prob }) => (
                      <div key={label} className="flex-1">
                        <div className="flex justify-between items-center mb-0.5">
                          <span className="text-[9px] text-text-muted">{label}</span>
                          <span
                            className="text-[9px] font-bold"
                            style={{ color: probToColor(prob) }}
                          >
                            {toPercent(prob, 0)}
                          </span>
                        </div>
                        <div className="h-1 w-full bg-bg-primary rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${(prob * 100).toFixed(0)}%`,
                              background: probToColor(prob),
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </aside>

      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); opacity: 0; }
          to   { transform: translateX(0);    opacity: 1; }
        }
      `}</style>
    </>
  );
}
