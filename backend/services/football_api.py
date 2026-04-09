import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import httpx
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log,
    RetryError
)
import logging

from config import (
    FOOTBALL_DATA_API_KEY, FOOTBALL_DATA_BASE_URL,
    API_FOOTBALL_KEY, API_FOOTBALL_BASE,
    API_CACHE_TTL_SECONDS
)

# Free plan season: fallback when current season is blocked
FREE_PLAN_SEASONS = [2025, 2024, 2023]

def _current_football_season(league_code: Optional[str] = None) -> int:
    """Return the current football season year.
    - European leagues (PL, BL1, etc.) run Aug→May, so Apr 2026 = season 2025.
    - Calendar leagues (BSA, MLS, etc.) run Jan→Dec, so Apr 2026 = season 2026."""
    now = time.localtime()
    year = now.tm_year
    month = now.tm_mon

    # List of common calendar-year leagues/competitions
    calendar_leagues = ["BSA", "MLS", "ASL", "CSL", "KL1", "JL1", "JL", "CLI", "CSD", "WC", "EC", "AFCON", "COPA"]
    
    if league_code in calendar_leagues:
        return year
    
    # European style: Season year starts in Aug
    return year if month >= 8 else year - 1
from cache import cache_manager
from logger import get_logger

logger = get_logger(__name__)


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
                logger.debug("Rate limiter sleeping %.2fs", wait)
                await asyncio.sleep(wait)
                self.tokens = 0
            else:
                self.tokens -= 1


class FootballAPIClient:
    """
    Async client for football-data.org v4 and API-Football.
    Features:
      - Token-bucket rate limiting
      - Redis-backed response caching (via cache_manager)
      - Tenacity retry logic (3 attempts, exponential backoff)
      - Structured logging (no print() calls)
    """

    def __init__(self):
        self.base_url = FOOTBALL_DATA_BASE_URL
        self.api_key = FOOTBALL_DATA_API_KEY
        self.af_key = API_FOOTBALL_KEY
        self.af_base = API_FOOTBALL_BASE
        self.rate_limiter = RateLimiter(requests_per_minute=10)
        self.league_seasons: Dict[str, int] = {}
        self._client: Optional[httpx.AsyncClient] = None
        self.fd_to_af = {}  # Map like "PL" -> "39"

        # AF ID → Football-Data code mapping (Restricted to Main Full Access Leagues)
        self.af_to_fd = {
            # Top 5 European Leagues
            "39": "PL",    # Premier League (England)
            "140": "PD",   # La Liga (Spain)
            "78": "BL1",   # Bundesliga (Germany)
            "135": "SA",   # Serie A (Italy)
            "61": "FL1",   # Ligue 1 (France)
            # Other Main Leagues
            "94": "PPL",   # Primeira Liga (Portugal)
            "88": "DED",   # Eredivisie (Netherlands)
            "40": "ELC",   # Championship (England)
            "71": "BSA",   # Brasileirão (Brazil)
            "253": "MLS",  # Major League Soccer (USA)
            # Major Continental & International
            "2": "CL",     # UEFA Champions League
            "3": "UEL",    # UEFA Europa League
            "1": "WC",     # FIFA World Cup
            "4": "EC",     # European Championship
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError, httpx.ReadTimeout)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _request_with_retry(
        self, path: str, params: Optional[Dict], headers: Dict, base: str
    ) -> Dict:
        """Inner HTTP call wrapped with tenacity retry (only for transient errors)."""
        client = await self._get_client()
        resp = await client.get(f"{base}{path}", params=params, headers=headers)
        
        # If forbidden or not found, return error immediately without raising for status
        # This avoids retries on non-transient plan/data errors
        if resp.status_code in (403, 404):
            return {"error": f"API {resp.status_code}: {resp.reason_phrase}", "status_code": resp.status_code}
            
        resp.raise_for_status()
        return resp.json()

    async def _request(
        self, path: str, params: Optional[Dict] = None, provider: str = "fd"
    ) -> Dict:
        """
        Cached + retried HTTP request.
        provider: "fd" (football-data.org) | "af" (api-football)
        """
        cache_key = cache_manager.build_key(provider, path, params)
        cached = await cache_manager.get(cache_key)
        if cached is not None:
            return cached

        headers = (
            self._headers() if provider == "fd"
            else {"x-apisports-key": self.af_key}
        )
        base = self.base_url if provider == "fd" else self.af_base

        await self.rate_limiter.acquire()
        logger.debug("API request: %s %s params=%s", provider.upper(), path, params)

        try:
            data = await self._request_with_retry(path, params, headers, base)
            await cache_manager.set(cache_key, data, API_CACHE_TTL_SECONDS)
            return data
        except RetryError as exc:
            # Unwrap the original error from tenacity
            orig = exc.last_attempt.exception() if exc.last_attempt else exc
            logger.error("API request failed after retries: %s %s — %s", provider.upper(), path, orig)
            return {"error": f"API request failed: {orig}"}
        except httpx.HTTPStatusError as exc:
            logger.error("API Status Error: %s %s — %s", provider.upper(), path, exc)
            return {"error": f"API error: {exc.response.status_code}"}
        except httpx.HTTPError as exc:
            logger.error("API Network Error: %s %s — %s", provider.upper(), path, exc)
            return {"error": f"API unavailable: {exc}"}
        except Exception as exc:
            logger.error("Unexpected API error: %s", exc)
            return {"error": str(exc)}

    # ─────────────────────────────────────────────────────────────────────────────
    # API methods
    # ─────────────────────────────────────────────────────────────────────────────

    async def get_competitions(self) -> List[Dict]:
        if not self.af_key:
            logger.info("No API-Football key set, returning mock competitions")
            return self._mock_competitions()

        data = await self._request("/leagues", provider="af")
        leagues = data.get("response", [])

        results = []
        top_codes = {
            "PL": 39, "PD": 140, "BL1": 78, "SA": 135, "FL1": 61, "CL": 2,
            "BSA": 71, "MLS": 253, "ELC": 40
        }

        for item in leagues:
            l = item.get("league", {})
            c = item.get("country", {})
            seasons = item.get("seasons", [])
            af_id = str(l.get("id"))
            code = self.af_to_fd.get(af_id, af_id)
            self.fd_to_af[code] = af_id

            # Always prefer our calculated current season for the starting point
            season_year = _current_football_season(code)

            results.append({
                "id": l.get("id"),
                "code": code,
                "name": l.get("name"),
                "area": c.get("name"),
                "emblem": l.get("logo"),
                "season": season_year,
                "is_top": l.get("id") in top_codes.values() or not code.isdigit()
            })
            self.league_seasons[code] = season_year

        # Filter: Only include "Full Access" leagues (those specifically mapped in af_to_fd)
        # This removes 1200+ obscure leagues that aren't fully supported on free plans
        full_access_codes = set(self.af_to_fd.values())
        original_count = len(results)
        results = [r for r in results if r["code"] in full_access_codes]

        results.sort(key=lambda x: (not x["is_top"], x["name"]))
        logger.info("Loaded %d competitions (filtered from %d original)", len(results), original_count)
        return results

    async def get_fixtures(self, competition_code: str, status: str = "SCHEDULED") -> List[Dict]:
        """Fetch fixtures, preferring FD for top leagues but falling back to AF for others."""
        is_fd_top = any(c == competition_code for c in ["PL", "ELC", "PD", "BL1", "SA", "FL1", "PPL", "DED", "BSA", "CL", "WC", "EC"])
        if is_fd_top and self.api_key:
            data = await self._request(f"/competitions/{competition_code}/matches", provider="fd")
            if "error" not in data:
                matches = data.get("matches", [])
                parsed = [self._parse_match(m) for m in matches]
                now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                # Upcoming matches first (ASC), then finished matches (DESC)
                upcoming = [m for m in parsed if m["date"] >= now_str]
                past = [m for m in parsed if m["date"] < now_str]
                upcoming.sort(key=lambda x: x["date"]) # Soonest upcoming first
                past.sort(key=lambda x: x["date"], reverse=True) # Most recently finished first
                return upcoming + past

        # Fallback to API-Football
        if competition_code not in self.league_seasons:
            await self.get_competitions()
            
        af_id = self.fd_to_af.get(competition_code, competition_code)
        if af_id.isdigit():
            season = self.league_seasons.get(competition_code, _current_football_season(competition_code))
            return await self.get_af_fixtures(int(af_id), season=season)
            
        # Mock fallback if everything fails
        return self._mock_fixtures(competition_code)

    async def get_af_fixtures(self, league_id: int, season: Optional[int] = None) -> List[Dict]:
        if not season:
            season = _current_football_season()

        # Build list of seasons to try: requested season first, then free plan fallbacks
        seasons_to_try = [season] + [s for s in FREE_PLAN_SEASONS if s != season]

        for try_season in seasons_to_try:
            # Try to get both scheduled and live matches
            params = {"league": league_id, "season": try_season}
            data = await self._request("/fixtures", params, provider="af")

            if "error" in data:
                return [{"error": data.get("error"), "is_error": True}]

            # Free plan error → try next season
            # Note: API-Football errors can be a list or dict
            errors = data.get("errors")
            if errors and isinstance(errors, dict):
                plan_err = errors.get("plan") or errors.get("requests") or errors.get("rateLimit")
                if plan_err:
                    logger.warning(
                        "Season %d blocked by plan limit (League %d): %s → trying older season",
                        try_season, league_id, plan_err
                    )
                    continue
                # Some other dict error
                err_msg = next(iter(errors.values()), "Unknown API error")
                return [{"error": f"API Error: {err_msg}", "is_error": True}]
            elif errors and isinstance(errors, list):
                # List of errors, usually means something is wrong but not necessarily a plan limit
                return [{"error": f"API Errors: {errors}", "is_error": True}]

            fixtures = data.get("response", [])
            if fixtures:
                if try_season != season:
                    logger.info(
                        "Using season %d data for League %d (current season unavailable on free plan)",
                        try_season, league_id
                    )
                # Filter for useful statuses
                # Include ALL matches but sort them intelligently in the frontend/here
                parsed = [self._parse_af_match(f) for f in fixtures]
                
                # Sort: Upcoming (ASC), then Past (DESC)
                now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                upcoming = [m for m in parsed if m["date"] >= now_str]
                past = [m for m in parsed if m["date"] < now_str]
                upcoming.sort(key=lambda x: x["date"])
                past.sort(key=lambda x: x["date"], reverse=True)
                return upcoming + past

        # All seasons exhausted
        return [{"error": "No fixture data available — free plan may not cover this league", "is_error": True}]

    async def get_competition_matches(self, competition_code: str, status: str = "FINISHED") -> List[Dict]:
        """Fetch historical matches, preferring FD for top leagues but falling back to AF for others."""
        is_fd_top = any(c == competition_code for c in ["PL", "ELC", "PD", "BL1", "SA", "FL1", "PPL", "DED", "BSA", "CL", "WC", "EC"])

        if is_fd_top and self.api_key:
            data = await self._request(f"/competitions/{competition_code}/matches", {"status": status}, provider="fd")
            if "error" not in data:
                return [self._parse_match(m) for m in data.get("matches", [])]

        # Fallback to API-Football
        if competition_code not in self.league_seasons:
            await self.get_competitions()
            
        af_id = self.fd_to_af.get(competition_code, competition_code)
        if not af_id.isdigit():
            return []
            
        season = self.league_seasons.get(competition_code, _current_football_season())
        
        # Try multiple seasons for free plan compatibility
        seasons_to_try = [season] + [s for s in FREE_PLAN_SEASONS if s != season]
        for try_season in seasons_to_try:
            data = await self._request(
                "/fixtures",
                {"league": int(af_id), "season": try_season, "status": status},
                provider="af"
            )
            if "error" in data:
                continue
            if data.get("errors"):
                if "plan" in str(data["errors"]):
                    continue
            matches = data.get("response", [])
            if matches:
                logger.info(
                    "Fetched %d %s matches for competition %s (season %d) via AF",
                    len(matches), status, competition_code, try_season
                )
                return [self._parse_af_match(m) for m in matches]
        return []

    async def get_team_matches(self, team_id: int, limit: int = 30) -> List[Dict]:
        data = await self._request(f"/teams/{team_id}/matches", {
            "status": "FINISHED", "limit": limit,
        })
        return [self._parse_match(m) for m in data.get("matches", [])]

    async def get_squad(self, team_id: int) -> Dict:
        if not self.api_key:
            logger.info("No API key, returning mock squad for team %d", team_id)
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
        data = await self._request(f"/matches/{match_id}")
        return self._parse_match(data.get("match", data))

    async def get_competition_standings(self, competition_code: str) -> List[Dict]:
        """Fetch standings, preferring FD but falling back to AF for free plan limits."""
        # 1. Try Football-Data first (only for major Top leagues)
        is_fd_top = any(c in competition_code for c in ["PL", "PD", "BL1", "SA", "FL1", "CL", "WC", "EC", "DED", "PPL", "BSA", "ELC"])
        
        if is_fd_top:
            data = await self._request(f"/competitions/{competition_code}/standings", provider="fd")
            if "error" not in data:
                standings_data = data.get("standings", [])
                total_standings = next(
                    (s for s in standings_data if s.get("type") == "TOTAL"),
                    standings_data[0] if standings_data else {}
                )
                table = total_standings.get("table", [])
                if table:
                    return [self._parse_fd_standing(row) for row in table]

        # 2. Fallback to API-Football (covers all other leagues)
        if competition_code not in self.league_seasons:
            await self.get_competitions()
            
        af_id = self.fd_to_af.get(competition_code, competition_code)
        if not af_id.isdigit():
            return []
            
        season = self.league_seasons.get(competition_code, _current_football_season())
        return await self.get_af_standings(int(af_id), season)

    async def get_af_standings(self, league_id: int, season: int) -> List[Dict]:
        """Fetch standings from API-Football."""
        logger.info("Fetching API-Football standings: League=%d Season=%d", league_id, season)
        data = await self._request("/standings", {"league": league_id, "season": season}, provider="af")
        
        if "error" in data:
            return []
            
        response = data.get("response", [])
        if not response:
            return []
            
        # AF Response: league -> standings -> array of groups -> array of teams
        # Usually one group for domestic leagues
        standings = response[0].get("league", {}).get("standings", [])
        if not standings:
            return []
            
        # Use first group (table)
        table = standings[0]
        return [
            {
                "position": row.get("rank"),
                "team_id": row.get("team", {}).get("id"),
                "team_name": row.get("team", {}).get("name"),
                "points": row.get("points"),
                "played": row.get("all", {}).get("played"),
                "won": row.get("all", {}).get("win"),
                "draw": row.get("all", {}).get("draw"),
                "lost": row.get("all", {}).get("lose"),
                "goals_for": row.get("all", {}).get("goals", {}).get("for"),
                "goals_against": row.get("all", {}).get("goals", {}).get("against"),
            }
            for row in table
        ]

    def _parse_fd_standing(self, row: Dict) -> Dict:
        """Helper to parse a row from Football-Data standing."""
        return {
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

    async def get_injuries(self, fixture_id: int) -> List[Dict]:
        """Proxy injuries from API-Football (never called from browser)."""
        if not self.af_key:
            logger.info("No API-Football key, returning empty injuries for fixture %d", fixture_id)
            return []
        data = await self._request("/injuries", {"fixture": fixture_id}, provider="af")
        if "error" in data:
            logger.warning("Injuries fetch error for fixture %d: %s", fixture_id, data.get("error"))
            return []
        return data.get("response", [])

    async def get_live_matches(self) -> List[Dict]:
        """Proxy live matches from API-Football."""
        if not self.af_key:
            return []
        data = await self._request("/fixtures", {"live": "all"}, provider="af")
        if "error" in data:
            return []
        return data.get("response", [])

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
            "Goalkeeper": "GK", "Centre-Back": "CB", "Right-Back": "RB",
            "Left-Back": "LB", "Defensive Midfield": "CDM",
            "Central Midfield": "CM", "Attacking Midfield": "CAM",
            "Left Midfield": "CM", "Right Midfield": "CM",
            "Left Winger": "LW", "Right Winger": "RW",
            "Centre-Forward": "ST", "Secondary Striker": "CF",
        }
        return mapping.get(api_position, "CM")

    # ─────────────────────────────────────────────────────────────────────────────
    # Mock data
    # ─────────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _mock_competitions() -> List[Dict]:
        return [
            # Top 5 European Leagues
            {"id": 39, "code": "PL", "name": "Premier League", "area": "England", "emblem": "", "is_top": True, "season": 2025},
            {"id": 140, "code": "PD", "name": "La Liga", "area": "Spain", "emblem": "", "is_top": True, "season": 2025},
            {"id": 78, "code": "BL1", "name": "Bundesliga", "area": "Germany", "emblem": "", "is_top": True, "season": 2025},
            {"id": 135, "code": "SA", "name": "Serie A", "area": "Italy", "emblem": "", "is_top": True, "season": 2025},
            {"id": 61, "code": "FL1", "name": "Ligue 1", "area": "France", "emblem": "", "is_top": True, "season": 2025},
            # Other Main Leagues
            {"id": 94, "code": "PPL", "name": "Primeira Liga", "area": "Portugal", "emblem": "", "is_top": False, "season": 2025},
            {"id": 88, "code": "DED", "name": "Eredivisie", "area": "Netherlands", "emblem": "", "is_top": False, "season": 2025},
            {"id": 40, "code": "ELC", "name": "Championship", "area": "England", "emblem": "", "is_top": False, "season": 2025},
            {"id": 71, "code": "BSA", "name": "Brasileirão Série A", "area": "Brazil", "emblem": "", "is_top": True, "season": 2025},
            {"id": 253, "code": "MLS", "name": "Major League Soccer", "area": "USA", "emblem": "", "is_top": True, "season": 2025},
            # Continental & International
            {"id": 2, "code": "CL", "name": "Champions League", "area": "Europe", "emblem": "", "is_top": True, "season": 2025},
            {"id": 3, "code": "UEL", "name": "Europa League", "area": "Europe", "emblem": "", "is_top": False, "season": 2025},
            {"id": 1, "code": "WC", "name": "World Cup", "area": "World", "emblem": "", "is_top": True, "season": 2025},
            {"id": 4, "code": "EC", "name": "Euro Championship", "area": "Europe", "emblem": "", "is_top": True, "season": 2025},
        ]

    @staticmethod
    def _mock_fixtures(competition_code: str) -> List[Dict]:
        teams = {
            "PL": [
                ("Manchester City", "Arsenal"), ("Liverpool", "Chelsea"),
                ("Tottenham", "Manchester United"), ("Newcastle", "Aston Villa"),
            ],
            "PD": [("Real Madrid", "Barcelona"), ("Atletico Madrid", "Sevilla")],
            "BL1": [("Bayern Munich", "Borussia Dortmund")],
        }
        pairs = teams.get(competition_code, [("Home Team", "Away Team")])
        
        now = datetime.now()
        return [
            {
                "match_id": 1000 + i, 
                "date": (now + timedelta(days=i, hours=2+i)).strftime("%Y-%m-%dT%H:%M:00Z"),
                "competition": competition_code, "home_team": home,
                "home_team_id": 100 + i * 2, "away_team": away,
                "away_team_id": 101 + i * 2, "home_goals": None, "away_goals": None,
                "home_ht_goals": None, "away_ht_goals": None, "status": "SCHEDULED",
                "stage": "REGULAR_SEASON", "venue": f"{home} Stadium",
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
            "team_id": team_id, "name": f"Team {team_id}", "crest": "",
            "players": [
                {
                    "player_id": str(team_id * 100 + i),
                    "name": f"Player {i + 1}", "position": pos,
                    "nationality": "England", "date_of_birth": "1998-01-01",
                    "jersey_no": i + 1, "goals_season": max(0, 15 - i),
                    "xg_per90": max(0.05, 0.5 - i * 0.04), "recent_form_goals": max(0, 3 - i // 3),
                }
                for i, (pos, _) in enumerate(names)
            ] + [
                {
                    "player_id": str(team_id * 100 + 20 + i),
                    "name": f"Sub {i + 1}", "position": pos,
                    "nationality": "England", "date_of_birth": "2000-01-01",
                    "jersey_no": 12 + i, "goals_season": 2, "xg_per90": 0.15, "recent_form_goals": 0,
                }
                for i, pos in enumerate(["GK", "CB", "CM", "CM", "RW", "ST", "LW"])
            ],
        }


# Singleton instance
football_api = FootballAPIClient()
