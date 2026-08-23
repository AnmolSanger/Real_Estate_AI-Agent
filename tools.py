from dotenv import load_dotenv
from crewai_tools import SerperDevTool

load_dotenv()

search_tool = SerperDevTool()
