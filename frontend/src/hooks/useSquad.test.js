import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// ── Mock apiClient ────────────────────────────────────────────────────────────
vi.mock('../services/apiClient', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import api from '../services/apiClient';
import { useSquad } from './useSquad';

describe('useSquad', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetchCompetitions sets competitions list', async () => {
    const mockData = [
      { id: 2021, code: 'PL', name: 'Premier League', area: 'England' },
    ];
    api.get.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(() => useSquad());

    await act(async () => {
      await result.current.fetchCompetitions();
    });

    expect(result.current.competitions).toHaveLength(1);
    expect(result.current.competitions[0].code).toBe('PL');
  });

  it('fetchFixtures sets fixtures on success', async () => {
    const mockFixtures = [
      { match_id: 1, home_team: 'Arsenal', away_team: 'Chelsea' },
      { match_id: 2, home_team: 'Liverpool', away_team: 'City' },
    ];
    api.get.mockResolvedValueOnce({ data: { fixtures: mockFixtures, count: 2 } });

    const { result } = renderHook(() => useSquad());

    await act(async () => {
      await result.current.fetchFixtures('PL');
    });

    expect(result.current.fixtures).toHaveLength(2);
    expect(result.current.loadingFixtures).toBe(false);
  });

  it('fetchFixtures sets error on API failure', async () => {
    api.get.mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useSquad());

    await act(async () => {
      await result.current.fetchFixtures('PL');
    });

    expect(result.current.fixtures).toHaveLength(0);
    expect(result.current.error).toMatch(/Failed to load fixtures/);
  });

  it('fetchSquad returns squad data for home side', async () => {
    const mockSquad = {
      team_id: 57,
      name: 'Arsenal',
      players: [{ player_id: '1', name: 'Saka', position: 'RW' }],
    };
    api.get.mockResolvedValueOnce({ data: mockSquad });

    const { result } = renderHook(() => useSquad());

    let squad;
    await act(async () => {
      squad = await result.current.fetchSquad(57, 'home');
    });

    expect(squad).toBeTruthy();
    expect(squad.name).toBe('Arsenal');
    expect(result.current.loadingSquad.home).toBe(false);
  });

  it('fetchMatchInjuries calls backend proxy endpoint', async () => {
    api.get.mockResolvedValueOnce({ data: { injuries: [], count: 0 } });

    const { result } = renderHook(() => useSquad());

    await act(async () => {
      await result.current.fetchMatchInjuries(12345);
    });

    // Should call /api/matches/12345/injuries (NOT a direct API-Football call)
    expect(api.get).toHaveBeenCalledWith('/api/matches/12345/injuries');
  });

  it('does not call API when fetchMatchInjuries called with null', async () => {
    const { result } = renderHook(() => useSquad());

    await act(async () => {
      await result.current.fetchMatchInjuries(null);
    });

    expect(api.get).not.toHaveBeenCalled();
  });
});
