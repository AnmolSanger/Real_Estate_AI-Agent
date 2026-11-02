from dotenv import load_dotenv

load_dotenv()

from crewai import Crew
from agents import create_llm, create_property_researcher, create_property_analyst
from tasks import create_research_task, create_analysis_task

# Gemini's free tier allows 5 requests per minute; stay one under it.
MAX_REQUESTS_PER_MINUTE = 4


def run_analysis(location, property_type):
    """Run the crew once and return the report text.

    Agents and tasks are built per call so concurrent runs share no state.
    """
    llm = create_llm()
    researcher = create_property_researcher(llm)
    analyst = create_property_analyst(llm)

    research_task = create_research_task(location, property_type, researcher)
    analysis_task = create_analysis_task(location, property_type, analyst, research_task)

    crew = Crew(
        agents=[researcher, analyst],
        tasks=[research_task, analysis_task],
        max_rpm=MAX_REQUESTS_PER_MINUTE,
        verbose=True,
    )

    return str(crew.kickoff())
