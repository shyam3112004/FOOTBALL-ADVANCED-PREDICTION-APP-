import { useRef, useEffect } from 'react';
import { toDecimalOdds, toPercent } from '../utils/oddsConverter';
import { probToBarClass, probToColor, confidenceToClass } from '../utils/colorScale';

function ProbBar({ prob, label, animate = true }) {
  const barRef = useRef(null);

  useEffect(() => {
    if (barRef.current && animate) {
      barRef.current.style.setProperty('--bar-target-width', `${(prob * 100).toFixed(1)}%`);
      barRef.current.classList.remove('animated');
      void barRef.current.offsetWidth;
      barRef.current.classList.add('animated');
    }
  }, [prob, animate]);

  return (
    <div className="space-y-1">
      {label && (
        <div className="flex items-center justify-between text-xs text-text-secondary">
          <span>{label}</span>
          <div className="flex items-center gap-2">
            <span className="font-mono font-semibold" style={{ color: probToColor(prob) }}>
              {toPercent(prob)}
            </span>
            <span className="odds-badge">{toDecimalOdds(prob)}</span>
          </div>
        </div>
      )}
      <div className="prob-bar-track">
        <div
          ref={barRef}
          className={`prob-bar-fill ${probToBarClass(prob)}`}
          style={{ '--bar-target-width': `${(prob * 100).toFixed(1)}%` }}
        />
      </div>
    </div>
  );
}

export function PredictionCard({
  title,
  confidence,
  children,
  className = '',
  badge,
}) {
  const confClass = confidenceToClass(confidence || 0);

  return (
    <div className={`prediction-card animate-fade-in ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-heading font-semibold text-base tracking-wide text-text-primary uppercase">
          {title}
        </h3>
        <div className="flex items-center gap-2">
          {badge && <span className="text-xs text-text-muted">{badge}</span>}
          {confidence != null && (
            <span className={`confidence-badge ${confClass}`}>
              {toPercent(confidence, 0)} conf.
            </span>
          )}
        </div>
      </div>
      <div className="border-t border-[#1F2937] pt-3">{children}</div>
    </div>
  );
}

export { ProbBar };

/* ── Skeleton version of prediction card ─────────────────────────────── */
export function PredictionCardSkeleton() {
  return (
    <div className="prediction-card space-y-3">
      <div className="flex justify-between">
        <div className="skeleton h-4 w-32 rounded" />
        <div className="skeleton h-4 w-16 rounded" />
      </div>
      <div className="border-t border-[#1F2937] pt-3 space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="space-y-1.5">
            <div className="flex justify-between">
              <div className="skeleton h-3 w-20 rounded" />
              <div className="skeleton h-3 w-12 rounded" />
            </div>
            <div className="skeleton h-2.5 w-full rounded-full" />
          </div>
        ))}
      </div>
    </div>
  );
}
