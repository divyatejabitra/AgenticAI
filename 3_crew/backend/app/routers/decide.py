from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services import crews

router = APIRouter()


@router.get("/decide")
def decide(sector: str = Query("Technology", description="Sector to scan, e.g. Technology, Defense")):
    """Decide section: runs the full stock_picker crew from scratch (discover -> research -> pick)."""
    return crews.run_decide(sector)


class TrendingCompanyIn(BaseModel):
    name: str
    ticker: Optional[str] = None
    reason: Optional[str] = ""


class DecideFromCompaniesRequest(BaseModel):
    sector: str = "Technology"
    companies: List[TrendingCompanyIn]


@router.post("/decide")
def decide_from_companies(req: DecideFromCompaniesRequest):
    """Decide section: researches and picks the best of an already-known list of trending
    companies (typically the ones /api/trending just returned), skipping re-discovery."""
    companies = [c.model_dump() for c in req.companies]
    return crews.run_decide_for_companies(companies, req.sector)
