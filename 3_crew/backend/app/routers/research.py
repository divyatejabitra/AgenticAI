from fastapi import APIRouter, Path

from app.services import crews, yahoo

router = APIRouter()


@router.get("/research/{ticker}")
def research(ticker: str = Path(..., description="Ticker or company name, e.g. PLTR")):
    """Stock detail section: live quote + a structured financial_researcher analysis."""
    quote = yahoo.get_quote(ticker)
    analysis = crews.run_structured_analysis(ticker)
    return {"ticker": ticker.upper(), "quote": quote, "analysis": analysis}
