import json
import os
from typing import Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


class FinnhubInput(BaseModel):
    """Input schema for FinnhubTool."""
    ticker: str = Field(..., description="Stock ticker symbol, e.g. AAPL, PLTR, NET")


class FinnhubTool(BaseTool):
    name: str = "Finnhub Quote"
    description: str = (
        "Fetches live market data for a stock ticker from Finnhub: current price, day "
        "change, market cap, P/E ratio, 52-week range, and sector/industry. This is an "
        "independent second source from Yahoo Finance — use both and cross-check the "
        "figures rather than relying on either alone."
    )
    args_schema: Type[BaseModel] = FinnhubInput

    def _run(self, ticker: str) -> str:
        symbol = ticker.strip().upper()
        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            return json.dumps({
                "ticker": symbol,
                "source": "finnhub",
                "error": "FINNHUB_API_KEY is not set. Only Yahoo Finance data is available.",
            })

        try:
            quote = self._get(f"{FINNHUB_BASE_URL}/quote", symbol, api_key)
            profile = self._get(f"{FINNHUB_BASE_URL}/stock/profile2", symbol, api_key)
            metrics = self._get(f"{FINNHUB_BASE_URL}/stock/metric", symbol, api_key, extra={"metric": "all"})
        except requests.RequestException as e:
            return json.dumps({"ticker": symbol, "source": "finnhub", "error": f"Could not fetch data: {e}"})

        price = quote.get("c")
        prev_close = quote.get("pc")
        if not price:
            return json.dumps({
                "ticker": symbol,
                "source": "finnhub",
                "error": "No data found for this ticker. It may be delisted, privately "
                         "held, or the symbol may be wrong.",
            })

        change_pct_today = (
            round((price - prev_close) / prev_close * 100, 2) if prev_close else None
        )
        m = metrics.get("metric", {})

        # Finnhub reports marketCapitalization in millions of USD; normalize to raw
        # dollars so it's directly comparable to YahooFinanceTool's market_cap.
        market_cap_millions = profile.get("marketCapitalization")
        market_cap = market_cap_millions * 1_000_000 if market_cap_millions is not None else None

        data = {
            "ticker": symbol,
            "source": "finnhub",
            "company_name": profile.get("name"),
            "exchange": profile.get("exchange"),
            "price": price,
            "currency": profile.get("currency"),
            "change_pct_today": change_pct_today,
            "market_cap": market_cap,
            "pe_ratio_trailing": m.get("peTTM") or m.get("peExclExtraTTM"),
            "52_week_high": m.get("52WeekHigh"),
            "52_week_low": m.get("52WeekLow"),
            "sector": profile.get("finnhubIndustry"),
            "industry": profile.get("finnhubIndustry"),
            "revenue_growth": m.get("revenueGrowthTTMYoy"),
            "profit_margin": m.get("netProfitMarginTTM"),
            "price_to_sales": m.get("psTTM"),
            "debt_to_equity": m.get("totalDebt/totalEquityQuarterly"),
            "return_on_equity": m.get("roeTTM"),
        }
        return json.dumps(data)

    @staticmethod
    def _get(url: str, symbol: str, api_key: str, extra: dict | None = None) -> dict:
        params = {"symbol": symbol, "token": api_key, **(extra or {})}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
