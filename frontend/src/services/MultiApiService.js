import axios from 'axios';
import { API_CONFIG } from '../config/apis';

/**
 * Unified Football Data Service
 * Orchestrates calls to API-Football, Sportmonks, and football-data.org.
 */
class MultiApiService {
  constructor() {
    // API-Football instance (api-sports.io or RapidAPI)
    this.apiFootballClient = axios.create({
      baseURL: API_CONFIG.apiFootball.base,
      headers: {
        'x-apisports-key': API_CONFIG.apiFootball.key,
      },
      timeout: 15000,
    });

    // Sportmonks instance (v3)
    // Sportmonks uses the API token in the query or header: Authorization: {token}
    this.sportmonksClient = axios.create({
      baseURL: API_CONFIG.sportmonks.base,
      headers: {
        'Authorization': API_CONFIG.sportmonks.key,
      },
      timeout: 15000,
    });

    // football-data.org (Proxied via backend conventionally, but here direct as requested)
    this.footballDataClient = axios.create({
      baseURL: API_CONFIG.footballData.base,
      headers: {
        'X-Auth-Token': API_CONFIG.footballData.key,
      },
      timeout: 15000,
    });
  }

  // ─── API-Football (Live, Injuries, H2H) ────────────────────────────────────

  async getLiveMatches() {
    try {
      const response = await this.apiFootballClient.get('/fixtures', {
        params: { live: 'all' }
      });
      return response.data.response || [];
    } catch (err) {
      console.error('API-Football Live Fetch Error:', err);
      return [];
    }
  }

  async getInjuries(matchId) {
    try {
      const response = await this.apiFootballClient.get('/injuries', {
        params: { fixture: matchId }
      });
      return response.data.response || [];
    } catch (err) {
      console.error('API-Football Injury Fetch Error:', err);
      return [];
    }
  }

  // ─── Sportmonks (xG, Pressure, Detailed Lineups) ──────────────────────────

  async getMatchAdvancedStats(matchId) {
    // Sportmonks requires includes for detailed data
    try {
      const response = await this.sportmonksClient.get(`/fixtures/${matchId}`, {
        params: {
          include: 'statistics;pressure;formations;events.type'
        }
      });
      return response.data.data || null;
    } catch (err) {
      console.error('Sportmonks Stats Fetch Error:', err);
      return null;
    }
  }

  async getxGData(matchId) {
    try {
      const response = await this.sportmonksClient.get(`/fixtures/${matchId}`, {
        params: { include: 'statistics.type;statistics.participant' }
      });
      return response.data.data?.statistics || [];
    } catch (err) {
      return [];
    }
  }

  // ─── Football-Data.org Bridge ──────────────────────────────────────────────

  async getFixtures(leagueCode) {
    try {
      const response = await this.footballDataClient.get(`/competitions/${leagueCode}/matches`);
      return response.data.matches || [];
    } catch (err) {
      console.error('Football-Data.org Fetch Error:', err);
      return [];
    }
  }

  // ─── Utility: Map IDs ──────────────────────────────────────────────────────

  /**
   * Note: Merging IDs across APIs often requires a mapping service or lookup table.
   * In a real app, you would pre-map team IDs (e.g. Arsenal ID in API-X vs API-Y).
   */
  async getUnifiedMatchData(matchId, providers = ['apiFootball', 'sportmonks']) {
     const data = {};
     const promises = [];
     
     if (providers.includes('apiFootball')) promises.push(this.getLiveMatches().then(res => data.live = res));
     if (providers.includes('sportmonks')) promises.push(this.getMatchAdvancedStats(matchId).then(res => data.advanced = res));
     
     await Promise.allSettled(promises);
     return data;
  }
}

export const multiApi = new MultiApiService();
