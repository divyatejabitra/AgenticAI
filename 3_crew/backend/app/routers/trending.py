from fastapi import APIRouter, Query

from app.services import crews

router = APIRouter()


@router.get("/trending")
def get_trending(sector: str = Query("Technology", description="Sector to scan, e.g. Technology, Defense")):
    """Discover section: runs trending_company_finder only."""
    return crews.run_trending(sector)
