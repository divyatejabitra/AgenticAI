from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.services import email as email_service
from app.services import yahoo

router = APIRouter()


class TrackRequest(BaseModel):
    ticker: str
    email: EmailStr


@router.post("/track")
def track(req: TrackRequest):
    """Sends a real confirmation email (via Resend) when someone tracks a ticker."""
    ticker = req.ticker.strip().upper()
    try:
        quote = yahoo.get_quote(ticker)
    except Exception:
        quote = None

    try:
        email_service.send_tracking_email(req.email, ticker, quote)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not send email: {e}")

    return {"status": "sent", "ticker": ticker, "email": req.email}
