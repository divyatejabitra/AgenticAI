from datetime import datetime
from typing import List, Literal, Optional

from crewai import Agent, Crew, Process, Task
from pydantic import BaseModel, Field

from financial_researcher.crew import ResearchCrew
from stock_picker.crew import StockPicker, TrendingCompanyResearchList


class RiskItem(BaseModel):
    category: str = Field(description="Short risk category, e.g. Company, Regulatory, Macro, Valuation")
    text: str = Field(description="One sentence describing the risk")


# Fixed categories/maxes (mirrors the demo panel's rubric) so the 0-100 total and the
# Buy >= 70 / Hold 45-69 / Sell < 45 legend stay meaningful — a free-form list of
# LLM-chosen categories and maxes wouldn't reliably sum to a comparable scale.
class ScoreBreakdown(BaseModel):
    fundamentals: int = Field(description="0-25")
    valuation: int = Field(description="0-20")
    balance_sheet_cash_flow: int = Field(description="0-20")
    sentiment_catalysts: int = Field(description="0-20")
    risk_adjustment: int = Field(description="0-15")


class StockAnalysis(BaseModel):
    summary: str = Field(description="1-2 sentence overall summary of the investment case")
    stance: Literal["BUY", "HOLD", "SELL", "INSUFFICIENT_DATA"]
    confidence_0_100: int = Field(description="Self-assessed confidence in this stance, 0-100")
    horizon: Literal["SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"]
    positives: List[str] = Field(description="2-4 positive factors")
    negatives: List[str] = Field(description="2-4 negative factors")
    bull_case: List[str] = Field(description="2-3 bullish scenarios")
    bear_case: List[str] = Field(description="2-3 bearish scenarios")
    risks: List[RiskItem] = Field(description="2-4 categorized risks")
    catalysts: List[str] = Field(description="2-3 upcoming events that could move the stock")
    what_could_change: List[str] = Field(description="2-3 things that would change this stance")
    score_breakdown: ScoreBreakdown
    better_entry: Optional[str] = Field(default=None, description="What price/condition would improve the entry point")


def run_trending(sector: str) -> dict:
    """Runs only the trending_company_finder step of stock_picker (fast: single agent, single task)."""
    sp = StockPicker()
    crew = Crew(
        agents=[sp.trending_company_finder()],
        tasks=[sp.find_trending_companies()],
        process=Process.sequential,
        verbose=True,
    )
    result = crew.kickoff(inputs={"sector": sector, "current_date": str(datetime.now())})
    task_output = result.tasks_output[0]
    companies = (
        [c.model_dump() for c in task_output.pydantic.companies]
        if task_output.pydantic else []
    )
    return {"sector": sector, "companies": companies, "raw": task_output.raw}


def run_decide(sector: str) -> dict:
    """Runs the full stock_picker crew end to end: discover -> research -> pick."""
    result = StockPicker().crew().kickoff(inputs={
        "sector": sector,
        "current_date": str(datetime.now()),
    })

    trending, research = [], []
    for task_output in result.tasks_output:
        model = task_output.pydantic
        if model is None:
            continue
        if hasattr(model, "companies"):
            trending = [c.model_dump() for c in model.companies]
        elif hasattr(model, "research_list"):
            research = [c.model_dump() for c in model.research_list]

    return {
        "sector": sector,
        "trending": trending,
        "research": research,
        "decision_markdown": result.raw,
    }


def run_decide_for_companies(companies: list, sector: str) -> dict:
    """Researches and picks the best of an already-known list of trending companies
    (e.g. straight from /api/trending), instead of re-running discovery. Builds a plain
    sequential crew from financial_researcher + stock_picker directly rather than going
    through StockPicker().crew() (hierarchical + memory), which is what run_decide() above
    uses and is a heavier, slower path."""
    sp = StockPicker()
    researcher = sp.financial_researcher()
    picker = sp.stock_picker()

    companies_text = "\n".join(
        f"- {c.get('name')} ({c.get('ticker') or 'N/A'}): {c.get('reason', '')}"
        for c in companies
    )

    research_task = Task(
        description=(
            f"Provide a detailed investment analysis of each of these trending companies "
            f"in the {sector} sector, searching online for the latest information:\n\n"
            f"{companies_text}\n\n"
            "Cover market position, future outlook, and investment potential for each."
        ),
        expected_output="A report containing detailed analysis of each company",
        agent=researcher,
        output_pydantic=TrendingCompanyResearchList,
    )
    pick_task = Task(
        description=(
            "Analyze the research findings and pick the best company for investment "
            "among the companies just researched. Respond with a detailed report on why "
            "you chose this company, and why the other companies were not selected."
        ),
        expected_output=(
            "The chosen company and why it was chosen; the companies that were not "
            "selected and why they were not selected."
        ),
        agent=picker,
        context=[research_task],
    )

    crew = Crew(
        agents=[researcher, picker],
        tasks=[research_task, pick_task],
        process=Process.sequential,
        verbose=True,
    )
    result = crew.kickoff()

    research = (
        [r.model_dump() for r in research_task.output.pydantic.research_list]
        if research_task.output and research_task.output.pydantic else []
    )

    return {
        "sector": sector,
        "trending": companies,
        "research": research,
        "decision_markdown": result.raw,
    }


def run_structured_analysis(ticker: str) -> Optional[dict]:
    """Runs financial_researcher's researcher + analyst agents, but shapes the analyst's
    output as a structured StockAnalysis instead of free-text markdown, so the live
    stock-detail panel can show the same reasoning/bull-bear/risks/catalysts sections the
    demo panel does — grounded in a real crew run rather than fabricated numbers."""
    rc = ResearchCrew()
    researcher = rc.researcher()
    analyst = rc.analyst()

    research_task = Task(
        description=(
            f"Conduct thorough research on {ticker}. Focus on: current status and health, "
            "historical performance, major challenges and opportunities, recent news and "
            "events, and future outlook."
        ),
        expected_output="A comprehensive research summary covering all the requested aspects",
        agent=researcher,
    )
    analysis_task = Task(
        description=(
            f"Using the research above, produce a structured investment analysis of {ticker} "
            "for the fields in the required output format. Ground the stance, confidence, and "
            "score breakdown in the actual research and live market data — don't default to a "
            "generic BUY. For score_breakdown, score each category on its own scale and don't "
            "just split the max evenly: fundamentals out of 25, valuation out of 20, "
            "balance_sheet_cash_flow out of 20, sentiment_catalysts out of 20, and "
            "risk_adjustment out of 15 — these five should sum to roughly the same scale as "
            "confidence_0_100 (out of 100), with higher scores for a stronger BUY case and "
            "lower scores for a weaker one or a SELL."
        ),
        expected_output="A structured StockAnalysis object",
        agent=analyst,
        context=[research_task],
        output_pydantic=StockAnalysis,
    )

    crew = Crew(
        agents=[researcher, analyst],
        tasks=[research_task, analysis_task],
        process=Process.sequential,
        verbose=True,
    )
    crew.kickoff()

    if analysis_task.output and analysis_task.output.pydantic:
        return analysis_task.output.pydantic.model_dump()
    return None


def run_chat_answer(ticker: str, question: str, context: Optional[str] = None) -> str:
    """One-off grounded Q&A using the financial_researcher crew's existing analyst agent."""
    rc = ResearchCrew()
    analyst: Agent = rc.analyst()

    task = Task(
        description=(
            f'A user is looking at {ticker} and asks: "{question}"\n\n'
            f"Live market context (Yahoo Finance):\n{context or 'not available'}\n\n"
            "Answer the question directly in 2-4 sentences, grounded in the market context "
            "above where relevant. If you don't have enough information to answer, say so "
            "plainly instead of guessing."
        ),
        expected_output="A short, direct answer to the user's question.",
        agent=analyst,
    )
    crew = Crew(agents=[analyst], tasks=[task], process=Process.sequential, verbose=True)
    result = crew.kickoff()
    return result.raw
