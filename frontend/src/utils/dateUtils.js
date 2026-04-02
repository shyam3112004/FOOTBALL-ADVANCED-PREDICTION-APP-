/**
 * Formats a UTC ISO date string into a user-friendly local date/time.
 * Returns "Today, HH:mm", "Tomorrow, HH:mm", or "DD/MM/YYYY, HH:mm".
 */
export function formatMatchDate(isoString) {
  if (!isoString) return '—';
  
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return isoString;

  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  
  const matchDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());

  const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });

  if (matchDay.getTime() === today.getTime()) {
    return `Today, ${timeStr}`;
  } else if (matchDay.getTime() === tomorrow.getTime()) {
    return `Tomorrow, ${timeStr}`;
  } else {
    const dateStr = date.toLocaleDateString([], { day: '2-digit', month: '2-digit', year: 'numeric' });
    return `${dateStr}, ${timeStr}`;
  }
}

/**
 * Strips common suffixes/prefixes from team names for better fuzzy matching.
 */
export function normalizeTeamName(name) {
  if (!name) return '';
  return name
    .toLowerCase()
    .replace(/\s(fc|fr|cf|afc|sc|ud|sd|rc|fk|c.f.|f.c.)$/g, '')
    .replace(/^(rc|rk|fk)\s/g, '')
    .trim();
}
