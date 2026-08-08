from fastapi import APIRouter, Query

from app.services import yahoo

router = APIRouter()


@router.get("/search")
def search(q: str = Query(..., min_length=1, description="Company name or ticker, e.g. 'Toyota' or 'TM'")):
    """Stock detail section: type-ahead search against Yahoo Finance's own search index."""
    return {"query": q, "results": yahoo.search_symbols(q)}
