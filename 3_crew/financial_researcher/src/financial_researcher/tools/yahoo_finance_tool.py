from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import json

import yfinance as yf


class YahooFinanceInput(BaseModel):
    """Input schema for YahooFinanceTool."""
    ticker: str = Field(..., description="Stock ticker symbol, e.g. AAPL, PLTR, NET")


class YahooFinanceTool(BaseTool):
    name: str = "Yahoo Finance Quote"
    description: str = (
        "Fetches live market data for a stock ticker from Yahoo Finance: current price, "
        "day change, market cap, P/E ratio, dividend yield, 52-week range, and recent price "
        "trend (1/3/6 month % change). Use this to ground research in real, current numbers "
        "instead of estimates."
    )
    args_schema: Type[BaseModel] = YahooFinanceInput

    def _run(self, ticker: str) -> str:
        symbol = ticker.strip().upper()
        try:
            t = yf.Ticker(symbol)
            info = t.info
            hist = t.history(period="6mo")
        except Exception as e:
            return json.dumps({"ticker": symbol, "error": f"Could not fetch data: {e}"})

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not info or price is None:
            return json.dumps({
                "ticker": symbol,
                "error": "No data found for this ticker. It may be delisted, privately "
                         "held, or the symbol may be wrong.",
            })

        prev_close = info.get("previousClose")
        change_pct_today = (
            round((price - prev_close) / prev_close * 100, 2) if prev_close else None
        )

        def pct_change(days: int):
            if hist.empty or len(hist) <= days:
                return None
            closes = hist["Close"]
            old, new = closes.iloc[-days], closes.iloc[-1]
            return round((new - old) / old * 100, 2) if old else None

        data = {
            "ticker": symbol,
            "company_name": info.get("shortName") or info.get("longName"),
            "exchange": info.get("fullExchangeName") or info.get("exchange"),
            "price": price,
            "currency": info.get("currency"),
            "change_pct_today": change_pct_today,
            "market_cap": info.get("marketCap"),
            "pe_ratio_trailing": info.get("trailingPE"),
            "pe_ratio_forward": info.get("forwardPE"),
            "eps_trailing": info.get("trailingEps"),
            "dividend_yield": info.get("dividendYield"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
            "volume": info.get("volume"),
            "avg_volume": info.get("averageVolume"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "analyst_target_mean_price": info.get("targetMeanPrice"),
            "analyst_recommendation": info.get("recommendationKey"),
            "trend_1m_pct": pct_change(21),
            "trend_3m_pct": pct_change(63),
            "trend_6m_pct": pct_change(126),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "profit_margin": info.get("profitMargins"),
            "free_cash_flow": info.get("freeCashflow"),
            "peg_ratio": info.get("trailingPegRatio") or info.get("pegRatio"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "debt_to_equity": info.get("debtToEquity"),
            "return_on_equity": info.get("returnOnEquity"),
            "fifty_day_average": info.get("fiftyDayAverage"),
            "two_hundred_day_average": info.get("twoHundredDayAverage"),
        }
        return json.dumps(data)
