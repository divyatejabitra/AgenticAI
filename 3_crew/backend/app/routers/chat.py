from fastapi import APIRouter
from pydantic import BaseModel

from app.services import crews, yahoo

router = APIRouter()


class ChatRequest(BaseModel):
    ticker: str
    question: str


@router.post("/chat")
def chat(req: ChatRequest):
    """Stock detail assistant panel: ask a follow-up question about a ticker."""
    quote = yahoo.get_quote(req.ticker)
    context = None if quote.get("error") else str(quote)
    answer = crews.run_chat_answer(req.ticker, req.question, context)
    return {"ticker": req.ticker.upper(), "question": req.question, "answer": answer}
