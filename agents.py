import os

from crewai import Agent, LLM
from google.genai import types
from tools import create_search_tool, roi_calculator

# Gemini returns 503 during demand spikes. Wait and retry each call, because a
# failed late step would otherwise throw away all the earlier agents' work.
LLM_RETRIES = types.HttpOptions(
    retry_options=types.HttpRetryOptions(attempts=6, initial_delay=5, max_delay=60),
)


def create_llm():
    return LLM(
        model=os.getenv("GEMINI_MODEL", "gemini/gemini-3.1-flash-lite"),
        temperature=0,
        client_params={"http_options": LLM_RETRIES},
    )


def create_property_researcher(llm):
    return Agent(
        llm=llm,
        role="Senior Property Market Researcher",
        goal="""Identify and analyze high-potential investment properties by:
            - Evaluating locations for demand, accessibility, and demographic alignment
            - Analyzing market trends, vacancy rates, and competitor presence
            - Assessing property conditions and potential renovation needs
            - Finding real asking prices and rents with their sources
            - Identifying emerging corridors and high-growth areas""",
        backstory="""You are a seasoned property market researcher with 15 years of experience across residential,
            commercial, retail, industrial, and mixed-use real estate.
            You've successfully identified over $500M worth of property investments across diverse market conditions.
            You combine traditional real estate metrics with modern analytics, including demand patterns,
            e-commerce impact assessment, and demographic shift analysis.
            Your methodology integrates both quantitative analysis (cap rates, NOI, tenant credit ratings)
            and qualitative factors (neighborhood dynamics, market trends, future development plans).""",
        allow_delegation=False,
        tools=[create_search_tool()],
        max_iter=8,
        verbose=True,
    )


def create_financial_modeler(llm):
    return Agent(
        llm=llm,
        role="Real Estate Financial Modeler",
        goal="""Measure each candidate property's returns by running the ROI calculator tool
            for every candidate and for a downside case. Never calculate a metric yourself.""",
        backstory="""You are a careful financial modeler who trusts tools over mental math.
            You reject missing or unsourced inputs, and you stress-test the best option
            before anyone commits capital to it.""",
        allow_delegation=False,
        tools=[roi_calculator],
        max_iter=6,
        verbose=True,
    )


def create_property_analyst(llm):
    return Agent(
        llm=llm,
        role="Senior Investment Report Analyst",
        goal="""Create comprehensive, investor-focused property analysis reports by:
            - Synthesizing complex property data into clear, actionable insights
            - Interpreting the financial model's results and assessing risk
            - Evaluating property conditions, maintenance requirements, and improvement opportunities
            - Analyzing market positioning and competitive advantages
            - Providing clear recommendations backed by data-driven insights
            - Creating professional reports that meet institutional investor standards""",
        backstory="""You are an experienced investment property analyst with a background in both real estate and financial analysis.
            With over 12 years of experience working with major real estate investment trusts and private equity firms,
            you've developed a reputation for producing thorough, investor-grade property analysis reports.

            Your expertise includes:
            - Advanced financial modeling and valuation techniques
            - Deep understanding of different property classes and their unique metrics
            - Experience in both residential and commercial property analysis
            - Strong background in market research and demographic analysis
            - Proven track record of helping investors make informed decisions through detailed reporting

            You've personally analyzed over 1,000 properties and your reports have facilitated more than $750M in successful
            property investments. Your analytical approach combines traditional property metrics with modern market dynamics,
            ensuring reports are both comprehensive and forward-looking.""",
        allow_delegation=False,
        verbose=True,
    )
