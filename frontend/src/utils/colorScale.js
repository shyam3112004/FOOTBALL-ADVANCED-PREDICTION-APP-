/**
 * Maps a probability [0, 1] to a CSS color string (red → amber → green)
 */
export const probToColor = (prob) => {
  if (prob == null) return '#4B5563';
  if (prob >= 0.6) return '#00FF87';
  if (prob >= 0.4) return '#F59E0B';
  return '#EF4444';
};

/**
 * Maps probability to a Tailwind class string
 */
export const probToClass = (prob) => {
  if (prob == null) return 'text-text-muted';
  if (prob >= 0.6) return 'text-accent-green';
  if (prob >= 0.4) return 'text-warning';
  return 'text-danger';
};

/**
 * Maps probability to bar fill CSS class ('prob-high' | 'prob-medium' | 'prob-low')
 */
export const probToBarClass = (prob) => {
  if (prob >= 0.6) return 'prob-high';
  if (prob >= 0.4) return 'prob-medium';
  return 'prob-low';
};

/**
 * Confidence badge class
 */
export const confidenceToClass = (conf) => {
  if (conf >= 0.7) return 'badge-high';
  if (conf >= 0.5) return 'badge-medium';
  return 'badge-low';
};

/**
 * Score grid cell color: probability intensity → green scale
 */
export const probToHeatColor = (prob, maxProb = 0.2) => {
  const ratio = Math.min(1, prob / (maxProb || 0.2));
  const alpha = 0.1 + ratio * 0.85;
  const greenIntensity = Math.round(60 + ratio * 137);
  return `rgba(0, ${greenIntensity}, 52, ${alpha.toFixed(2)})`;
};

/**
 * Position group → colour class
 */
export const positionToClass = (pos) => {
  if (!pos) return 'pos-MID';
  if (pos === 'GK') return 'pos-GK';
  if (['CB', 'RB', 'LB', 'WB'].includes(pos)) return 'pos-DEF';
  if (['ST', 'CF', 'LW', 'RW'].includes(pos)) return 'pos-FWD';
  return 'pos-MID';
};

/**
 * Position → pitch fill color (for SVG nodes)
 */
export const positionToFill = (pos) => {
  if (!pos) return '#4ADE80';
  if (pos === 'GK') return '#FCD34D';
  if (['CB', 'RB', 'LB', 'WB'].includes(pos)) return '#60A5FA';
  if (['ST', 'CF', 'LW', 'RW'].includes(pos)) return '#F87171';
  return '#4ADE80';
};
