import asyncio
import time
from typing import Dict, List, Any, Optional
import httpx
from config import (
    FOOTBALL_DATA_API_KEY, FOOTBALL_DATA_BASE_URL,
    API_FOOTBALL_KEY, API_FOOTBALL_BASE,
    API_CACHE_TTL_SECONDS
)


class RateLimiter:
    """Simple token-bucket rate limiter for API requests."""

    def __init__(self, requests_per_minute: int = 10):
        self.rate = requests_per_minute
        self.tokens = float(requests_per_minute)
        self.last_check = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_check
            self.last_check = now
            self.tokens = min(self.rate, self.tokens + elapsed * (self.rate / 60.0))
            if self.tokens < 1:
                wait = (1 - self.tokens) * (60.0 / self.rate)
                await asyncio.sleep(wait)
                self.tokens = 0
            else:
                self.tokens -= 1


class FootballAPIClient:
    """
    Async client for football-data.org v4 API.
    Handles rate limiting (10 req/min free tier) and response caching.
    """

    def __init__(self):
        self.base_url = FOOTBALL_DATA_BASE_URL
        self.api_key = FOOTBALL_DATA_API_KEY
        self.af_key = API_FOOTBALL_KEY
        self.af_base = API_FOOTBALL_BASE
        self.rate_limiter = RateLimiter(requests_per_minute=10)
        self._cache: Dict[str, Dict] = {}
        self.league_seasons: Dict[str, int] = {} # league_id -> current_season_year
        self._client: Optional[httpx.AsyncClient] = None
        
        # Mapping API-Football ID -> Football-Data.org Code
        self.af_to_fd = {
            "39": "PL", "140": "PD", "78": "BL1", "135": "SA", "61": "FL1",
            "94": "PPL", "88": "DED", "71": "BSA", "40": "ELC", "2": "CL",
            "1": "WC", "4": "EC", "13": "CLI"
        }

    def _headers(self) -> Dict[str, str]:
        return {"X-Auth-Token": self.api_key}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers(),
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _is_cached(self, key: str) -> bool:
        if key not in self._cache:
            return False
        return time.monotonic() - self._cache[key]["ts"] < API_CACHE_TTL_SECONDS

    async def _request(self, path: str, params: Optional[Dict] = None, provider: str = "fd") -> Dict:
        """
        provider: "fd" (football-data.org) or "af" (api-football)
        """
        cache_key = f"{provider}:{path}:{str(params)}"
        if self._is_cached(cache_key):
            return self._cache[cache_key]["data"]

        headers = self._headers() if provider == "fd" else {"x-apisports-key": self.af_key}
        base = self.base_url if provider == "fd" else self.af_base

        await self.rate_limiter.acquire()
        client = await self._get_client()
        try:
            resp = await client.get(f"{base}{path}", params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            self._cache[cache_key] = {"data": data, "ts": time.monotonic()}
            return data
        except Exception as e:
            return {"error": str(e)}

    # ─────────────────────────────────────────────────────────────────────────────
    # API methods
    # ─────────────────────────────────────────────────────────────────────────────

    async def get_competitions(self) -> List[Dict]:
        """List all available competitions (from API-Football for maximum coverage)."""
        if not self.af_key:
            return self._mock_competitions()
        
        data = await self._request("/leagues", provider="af")
        leagues = data.get("response", [])
        
        results = []
        # Prioritize top leagues
        top_codes = {"PL": 39, "PD": 140, "BL1": 78, "SA": 135, "FL1": 61, "CL": 2}
        
        for item in leagues:
            l = item.get("league", {})
            c = item.get("country", {})
            seasons = item.get("seasons", [])
            # Find current season or fallback to latest
            current_season = next((s for s in seasons if s.get("current")), seasons[-1] if seasons else {})
            season_year = current_season.get("year", time.localtime().tm_year)
            
            af_id = str(l.get("id"))
            # Use Football-Data code if available for better free access
            code = self.af_to_fd.get(af_id, af_id)
            
            results.append({
                "id": l.get("id"),
                "code": code, 
                "name": l.get("name"),
                "area": c.get("name"),
                "emblem": l.get("logo"),
                "season": season_year,
                "is_top": l.get("id") in top_codes.values() or not code.isdigit()
            })
            # Store for fixture lookup
            self.league_seasons[code] = season_year
        
        # Sort so top leagues are first
        results.sort(key=lambda x: (not x["is_top"], x["name"]))
        return results

    async def get_fixtures(self, competition_code: str, status: str = "SCHEDULED") -> List[Dict]:
        """Fetch upcoming/recent fixtures (Routes to correct provider)."""
        # If numeric, use API-Football. If legacy code (PL, PD, etc.), use Football-Data.org.
        is_numeric = competition_code.isdigit()
        
        if is_numeric:
            if competition_code not in self.league_seasons:
                await self.get_competitions()
            season = self.league_seasons.get(competition_code, time.localtime().tm_year)
            return await self.get_af_fixtures(int(competition_code), season=season)
        else:
            # Football-Data.org (Better for Free Tier top leagues)
            if not self.api_key:
                return self._mock_fixtures(competition_code)
            data = await self._request(f"/competitions/{competition_code}/matches", {"status": status})
            if "error" in data:
                return [{"error": data.get("error", "Unknown API error"), "is_error": True}]
            matches = data.get("matches", [])
            return [self._parse_match(m) for m in matches]

    async def get_af_fixtures(self, league_id: int, season: Optional[int] = None) -> List[Dict]:
        """Fetch fixtures from API-Football."""
        if not season:
            season = time.localtime().tm_year
        
        print(f"⚽ Fetching API-Football fixtures: League={league_id}, Season={season}")
        data = await self._request("/fixtures", {"league": league_id, "season": season}, provider="af")
        
        if "error" in data:
            return [{"error": data.get("error"), "is_error": True}]
            
        # Check for Free Plan restriction in the response body
        if data.get("errors") and "plan" in data["errors"]:
             return [{"error": f"API Plan Limit: {data['errors']['plan']}", "is_error": True}]
            
        fixtures = data.get("response", [])
        return [self._parse_af_match(f) for f in fixtures]

    async def get_competition_matches(self, competition_code: str, status: str = "FINISHED") -> List[Dict]:
        """Fetch all matches for a competition (historical data)."""
        is_numeric = competition_code.isdigit()
        
        if is_numeric:
            if competition_code not in self.league_seasons:
                await self.get_competitions()
            season = self.league_seasons.get(competition_code, time.localtime().tm_year)
            # Fetch from API-Football
            data = await self._request("/fixtures", {"league": int(competition_code), "season": season, "status": status}, provider="af")
            if "error" in data:
                return []
            matches = data.get("response", [])
            return [self._parse_af_match(m) for m in matches]
        else:
            # Football-Data.org
            data = await self._request(f"/competitions/{competition_code}/matches", {"status": status})
            if "error" in data:
                return []
            matches = data.get("matches", [])
            return [self._parse_match(m) for m in matches]

    async def get_team_matches(self, team_id: int, limit: int = 30) -> List[Dict]:
        """Fetch recent matches for a specific team."""
        data = await self._request(f"/teams/{team_id}/matches", {
            "status": "FINISHED",
            "limit": limit,
        })
        matches = data.get("matches", [])
        return [self._parse_match(m) for m in matches]

    async def get_squad(self, team_id: int) -> Dict:
        """Fetch team squad information."""
        if not self.api_key:
            return self._mock_squad(team_id)
        data = await self._request(f"/teams/{team_id}")
        squad = data.get("squad", [])
        return {
            "team_id": team_id,
            "name": data.get("name", "Unknown"),
            "crest": data.get("crest", ""),
            "players": [
                {
                    "player_id": str(p.get("id", "")),
                    "name": p.get("name", ""),
                    "position": self._map_position(p.get("position", "")),
                    "nationality": p.get("nationality", ""),
                    "date_of_birth": p.get("dateOfBirth", ""),
                    "jersey_no": p.get("shirtNumber", 0) or 0,
                    "goals_season": 0,
                    "xg_per90": 0.2,
                    "recent_form_goals": 0,
                }
                for p in squad
            ],
        }

    async def get_match_details(self, match_id: int) -> Dict:
        """Fetch detailed match info including lineups."""
        data = await self._request(f"/matches/{match_id}")
        return self._parse_match(data.get("match", data))

    async def get_competition_standings(self, competition_code: str) -> List[Dict]:
        """Fetch current standings/table for a competition."""
        data = await self._request(f"/competitions/{competition_code}/standings")
        standings_data = data.get("standings", [])
        if not standings_data:
            return []
        total_standings = next(
            (s for s in standings_data if s.get("type") == "TOTAL"),
            standings_data[0] if standings_data else {}
        )
        table = total_standings.get("table", [])
        return [
            {
                "position": row.get("position"),
                "team_id": row.get("team", {}).get("id"),
                "team_name": row.get("team", {}).get("name"),
                "points": row.get("points"),
                "played": row.get("playedGames"),
                "won": row.get("won"),
                "draw": row.get("draw"),
                "lost": row.get("lost"),
                "goals_for": row.get("goalsFor"),
                "goals_against": row.get("goalsAgainst"),
            }
            for row in table
        ]

    # ─────────────────────────────────────────────────────────────────────────────
    # Parse helpers
    # ─────────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_match(m: Dict) -> Dict:
        home_score = m.get("score", {}).get("fullTime", {}).get("home")
        away_score = m.get("score", {}).get("fullTime", {}).get("away")
        ht_home = m.get("score", {}).get("halfTime", {}).get("home")
        ht_away = m.get("score", {}).get("halfTime", {}).get("away")
        return {
            "match_id": m.get("id"),
            "date": m.get("utcDate", ""),
            "competition": m.get("competition", {}).get("code", ""),
            "home_team": m.get("homeTeam", {}).get("name", ""),
            "home_team_id": m.get("homeTeam", {}).get("id"),
            "away_team": m.get("awayTeam", {}).get("name", ""),
            "away_team_id": m.get("awayTeam", {}).get("id"),
            "home_goals": home_score,
            "away_goals": away_score,
            "home_ht_goals": ht_home,
            "away_ht_goals": ht_away,
            "status": m.get("status", ""),
            "stage": m.get("stage", ""),
            "venue": m.get("venue", ""),
        }

    @staticmethod
    def _parse_af_match(f: Dict) -> Dict:
        """Parse API-Football match structure."""
        fixture = f.get("fixture", {})
        teams = f.get("teams", {})
        goals = f.get("goals", {})
        score = f.get("score", {})
        
        return {
            "match_id": fixture.get("id"),
            "date": fixture.get("date", ""),
            "competition": str(f.get("league", {}).get("id", "")),
            "home_team": teams.get("home", {}).get("name", ""),
            "home_team_id": teams.get("home", {}).get("id"),
            "home_logo": teams.get("home", {}).get("logo", ""),
            "away_team": teams.get("away", {}).get("name", ""),
            "away_team_id": teams.get("away", {}).get("id"),
            "away_logo": teams.get("away", {}).get("logo", ""),
            "home_goals": goals.get("home"),
            "away_goals": goals.get("away"),
            "home_ht_goals": score.get("halftime", {}).get("home"),
            "away_ht_goals": score.get("halftime", {}).get("away"),
            "status": fixture.get("status", {}).get("short", ""),
            "stage": f.get("league", {}).get("round", ""),
            "venue": fixture.get("venue", {}).get("name", ""),
        }

    @staticmethod
    def _map_position(api_position: str) -> str:
        mapping = {
            "Goalkeeper": "GK",
            "Centre-Back": "CB",
            "Right-Back": "RB",
            "Left-Back": "LB",
            "Defensive Midfield": "CDM",
            "Central Midfield": "CM",
            "Attacking Midfield": "CAM",
            "Left Midfield": "CM",
            "Right Midfield": "CM",
            "Left Winger": "LW",
            "Right Winger": "RW",
            "Centre-Forward": "ST",
            "Secondary Striker": "CF",
        }
        return mapping.get(api_position, "CM")

    # ─────────────────────────────────────────────────────────────────────────────
    # Mock data (when no API key)
    # ─────────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _mock_competitions() -> List[Dict]:
        return [
            {"id": 2021, "code": "PL", "name": "Premier League", "area": "England", "emblem": ""},
            {"id": 2014, "code": "PD", "name": "La Liga", "area": "Spain", "emblem": ""},
            {"id": 2002, "code": "BL1", "name": "Bundesliga", "area": "Germany", "emblem": ""},
            {"id": 2019, "code": "SA", "name": "Serie A", "area": "Italy", "emblem": ""},
            {"id": 2015, "code": "FL1", "name": "Ligue 1", "area": "France", "emblem": ""},
            {"id": 2001, "code": "CL", "name": "Champions League", "area": "Europe", "emblem": ""},
        ]

    @staticmethod
    def _mock_fixtures(competition_code: str) -> List[Dict]:
        teams = {
            "PL": [
                ("Manchester City", "Arsenal"), ("Liverpool", "Chelsea"),
                ("Tottenham", "Manchester United"), ("Newcastle", "Aston Villa"),
                ("Brighton", "Everton"),
            ],
            "PD": [
                ("Real Madrid", "Barcelona"), ("Atletico Madrid", "Sevilla"),
                ("Valencia", "Villarreal"),
            ],
            "BL1": [
                ("Bayern Munich", "Borussia Dortmund"), ("RB Leipzig", "Bayer Leverkusen"),
            ],
        }
        pairs = teams.get(competition_code, [("Home Team", "Away Team")])
        return [
            {
                "match_id": 1000 + i,
                "date": f"2025-05-{15 + i:02d}",
                "competition": competition_code,
                "home_team": home,
                "home_team_id": 100 + i * 2,
                "away_team": away,
                "away_team_id": 101 + i * 2,
                "home_goals": None,
                "away_goals": None,
                "home_ht_goals": None,
                "away_ht_goals": None,
                "status": "SCHEDULED",
                "stage": "REGULAR_SEASON",
                "venue": f"{home} Stadium",
            }
            for i, (home, away) in enumerate(pairs)
        ]

    @staticmethod
    def _mock_squad(team_id: int) -> Dict:
        names = [
            ("GK", "Goalkeeper"), ("RB", "Right Back"), ("CB", "Centre Back 1"),
            ("CB", "Centre Back 2"), ("LB", "Left Back"), ("CDM", "Defensive Mid"),
            ("CM", "Central Mid 1"), ("CM", "Central Mid 2"), ("RW", "Right Winger"),
            ("LW", "Left Winger"), ("ST", "Striker"),
        ]
        return {
            "team_id": team_id,
            "name": f"Team {team_id}",
            "crest": "",
            "players": [
                {
                    "player_id": str(team_id * 100 + i),
                    "name": f"Player {i + 1}",
                    "position": pos,
                    "nationality": "England",
                    "date_of_birth": "1998-01-01",
                    "jersey_no": i + 1,
                    "goals_season": max(0, 15 - i * 1),
                    "xg_per90": max(0.05, 0.5 - i * 0.04),
                    "recent_form_goals": max(0, 3 - i // 3),
                }
                for i, (pos, _) in enumerate(names)
            ] + [
                {
                    "player_id": str(team_id * 100 + 20 + i),
                    "name": f"Sub {i + 1}",
                    "position": pos,
                    "nationality": "England",
                    "date_of_birth": "2000-01-01",
                    "jersey_no": 12 + i,
                    "goals_season": 2,
                    "xg_per90": 0.15,
                    "recent_form_goals": 0,
                }
                for i, pos in enumerate(["GK", "CB", "CM", "CM", "RW", "ST", "LW"])
            ],
        }


# Singleton instance
football_api = FootballAPIClient()
