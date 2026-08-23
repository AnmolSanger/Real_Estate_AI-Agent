from dotenv import load_dotenv

load_dotenv()

from crewai import Crew
from agents import property_researcher, property_analyst
from tasks import create_research_task, create_analysis_task


def run():
    print("\n--- Real Estate Investment AI Agent ---\n")
    location = input("Enter the location to analyze (e.g., Mumbai, Berlin, New York): ").strip()
    property_type = input("Enter the property type (e.g., retail, residential, commercial): ").strip()

    if not location or not property_type:
        print("Both location and property type are required.")
        return

    print(f"\nAnalyzing {property_type} properties in {location}...\n")

    research_task = create_research_task(location, property_type)
    analysis_task = create_analysis_task(location, property_type, research_task)

    crew = Crew(
        agents=[property_researcher, property_analyst],
        tasks=[research_task, analysis_task],
        verbose=True,
    )

    result = crew.kickoff()
    print("\n--- Final Investment Report ---\n")
    print(result)
    print("\nReport saved to investment_report.txt")


if __name__ == "__main__":
    run()
