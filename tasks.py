from crewai import Task
from agents import property_researcher, property_analyst


def create_research_task(location, property_type):
    return Task(
        description=f"""Conduct a comprehensive analysis of potential {property_type} property investments in {location}.

        Specific research requirements:
        1. Market Analysis:
           - Identify top 3-5 potential {property_type} property investment locations in {location}
           - Analyze current market trends and economic indicators
           - Assess demographic data and consumer spending patterns
           - Evaluate local real estate ecosystem and market dynamics

        2. Property Evaluation Criteria:
           - Foot traffic and demand analysis
           - Accessibility and transportation infrastructure
           - Proximity to complementary businesses and amenities
           - Local economic development plans and upcoming projects

        3. Financial Analysis:
           - Estimate potential rental yields
           - Calculate projected ROI
           - Assess property valuation and appreciation potential
           - Identify potential renovation or repositioning opportunities

        4. Risk Assessment:
           - Analyze competitor landscape
           - Evaluate e-commerce and market disruption impact
           - Assess potential regulatory or zoning challenges
           - Identify potential long-term growth barriers

        Deliverable: A comprehensive, data-driven investment recommendation report.""",
        agent=property_researcher,
        expected_output=f"""Detailed report containing:
        - Market analysis summary for {property_type} properties in {location}
        - Top 3-5 recommended investment opportunities with specific details
        - Financial projections including rental yields and ROI estimates
        - Risk assessment with mitigation strategies
        - Recommendations for further due diligence""",
    )


def create_analysis_task(location, property_type, research_task):
    return Task(
        description=f"""Using the research findings on {property_type} properties in {location}, create a
        professional investor-grade summary report.

        Your report must include:
        1. Executive Summary (2-3 paragraphs covering key findings and recommendation)
        2. Top Investment Picks (ranked list with key metrics for each):
           - Location and property details
           - Price range and rental yield
           - ROI projection (1-year, 3-year, 5-year)
           - Key strengths and risks
        3. Market Overview (current trends, growth drivers, demand-supply dynamics)
        4. Risk Matrix (categorized as High/Medium/Low with mitigation strategies)
        5. Final Recommendation (clear invest/hold/avoid verdict with reasoning)

        Format the report professionally with clear headings and bullet points.
        Use actual numbers and percentages wherever possible.""",
        agent=property_analyst,
        expected_output="""A professional investor summary report with:
        - Executive summary with clear investment thesis
        - Ranked list of top picks with financial metrics
        - Market overview with data-backed insights
        - Risk matrix with categorized risks
        - Clear final recommendation with reasoning""",
        context=[research_task],
        output_file="investment_report.txt",
    )
