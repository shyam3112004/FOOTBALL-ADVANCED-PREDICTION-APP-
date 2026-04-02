/**
 * Probability → Decimal Odds
 */
export const toDecimalOdds = (prob) => {
  if (!prob || prob <= 0) return '—';
  return (1 / prob).toFixed(2);
};

/**
 * Probability → Fractional Odds string (e.g. "5/2")
 */
export const toFractionalOdds = (prob) => {
  if (!prob || prob <= 0 || prob >= 1) return '—';
  const decimal = 1 / prob;
  const numerator = decimal - 1;
  const denoms = [1, 2, 4, 5, 8, 10, 20, 25, 50];
  for (const d of denoms) {
    const n = Math.round(numerator * d);
    if (n > 0 && Math.abs(n / d - numerator) < 0.05) {
      return `${n}/${d}`;
    }
  }
  return `${Math.round(numerator * 10)}/10`;
};

/**
 * Probability (0–1) → American Odds string
 */
export const toAmericanOdds = (prob) => {
  if (!prob || prob <= 0 || prob >= 1) return '—';
  if (prob >= 0.5) {
    return `-${Math.round((prob / (1 - prob)) * 100)}`;
  }
  return `+${Math.round(((1 - prob) / prob) * 100)}`;
};

/**
 * Format probability as percentage string
 */
export const toPercent = (prob, decimals = 1) => {
  if (prob == null) return '—';
  return `${(prob * 100).toFixed(decimals)}%`;
};
