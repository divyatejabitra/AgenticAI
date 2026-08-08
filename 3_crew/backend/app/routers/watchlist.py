from fastapi import APIRouter, HTTPException, Query

from app.services import yahoo

router = APIRouter()


@router.get("/watchlist")
def watchlist(tickers: str = Query(..., description="Comma-separated tickers, e.g. NET,PLTR,QCOM")):
    """Watchlist section: live quotes only, no LLM calls."""
    symbols = [t.strip() for t in tickers.split(",") if t.strip()]
    if not symbols:
        raise HTTPException(status_code=400, detail="Provide at least one ticker")
    return {"quotes": yahoo.get_quotes(symbols)}
