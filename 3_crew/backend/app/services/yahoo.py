import json
from typing import List

import yfinance as yf

from stock_picker.tools.yahoo_finance_tool import YahooFinanceTool

_tool = YahooFinanceTool()


def get_quote(ticker: str) -> dict:
    """Fast, LLM-free live quote lookup — reuses the same tool the agents call."""
    return json.loads(_tool._run(ticker))


def get_quotes(tickers: List[str]) -> List[dict]:
    return [get_quote(t) for t in tickers]


def search_symbols(query: str, max_results: int = 8) -> List[dict]:
    """Company-name-or-ticker search against Yahoo Finance's own search index."""
    query = (query or "").strip()
    if not query:
        return []

    results = yf.Search(query, max_results=max_results).quotes
    symbols = []
    for r in results:
        symbol = r.get("symbol")
        if not symbol:
            continue
        symbols.append({
            "symbol": symbol,
            "name": r.get("shortname") or r.get("longname") or symbol,
            "exchange": r.get("exchDisp") or r.get("exchange"),
            "type": r.get("typeDisp") or r.get("quoteType"),
        })
    return symbols
