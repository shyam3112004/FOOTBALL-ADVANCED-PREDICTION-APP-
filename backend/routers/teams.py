from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from services.football_api import football_api

router = APIRouter(prefix="/api", tags=["teams"])


@router.get("/competitions")
async def get_competitions():
    """List all available competitions."""
    return await football_api.get_competitions()


@router.get("/competitions/{code}/fixtures")
async def get_fixtures(
    code: str,
    status: str = Query(default="SCHEDULED", description="SCHEDULED | FINISHED | LIVE"),
):
    """Fetch fixtures for a competition."""
    fixtures = await football_api.get_fixtures(code, status=status)
    return {"competition": code, "fixtures": fixtures, "count": len(fixtures)}


@router.get("/competitions/{code}/standings")
async def get_standings(code: str):
    """Fetch current standings for a competition."""
    standings = await football_api.get_competition_standings(code)
    return {"competition": code, "standings": standings}


@router.get("/teams/{team_id}/squad")
async def get_squad(team_id: int):
    """Fetch the squad for a specific team."""
    squad = await football_api.get_squad(team_id)
    if "error" in squad:
        raise HTTPException(status_code=502, detail=squad["error"])
    return squad


@router.get("/teams/{team_id}/matches")
async def get_team_matches(team_id: int, limit: int = Query(default=20, le=40)):
    """Fetch recent matches for a team."""
    matches = await football_api.get_team_matches(team_id, limit=limit)
    return {"team_id": team_id, "matches": matches, "count": len(matches)}


@router.get("/matches/{match_id}")
async def get_match(match_id: int):
    """Fetch details for a specific match."""
    match = await football_api.get_match_details(match_id)
    return match
