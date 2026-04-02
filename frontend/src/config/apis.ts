export const API_CONFIG = {
  apiFootball: {
    key: import.meta.env.VITE_API_FOOTBALL_KEY,
    base: import.meta.env.VITE_API_FOOTBALL_BASE,
    rateLimit: { requestsPerDay: 100, requestsPerMinute: 10 },
    features: ['fixtures', 'live', 'standings', 'players', 'h2h', 'predictions', 'odds', 'injuries', 'transfers', 'xg']
  },
  sportmonks: {
    key: import.meta.env.VITE_SPORTMONKS_KEY,
    base: 'https://api.sportmonks.com/v3/football',
    rateLimit: { requestsPerHour: 1000 },
    features: ['fixtures', 'live', 'standings', 'players', 'odds', 'xg', 'pressure', 'formations', 'tv', 'coaches']
  },
  footballData: {
    key: import.meta.env.VITE_FOOTBALL_DATA_KEY,
    base: import.meta.env.VITE_FOOTBALL_DATA_BASE,
    rateLimit: { requestsPerMinute: 10 },
    features: ['fixtures', 'standings', 'teams', 'scorers', 'head2head']
  }
} as const;

export type ApiName = keyof typeof API_CONFIG;
export type FeatureKey = string;
