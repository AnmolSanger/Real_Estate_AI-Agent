# Real Estate Investment AI Agent

A multi-agent AI system that analyzes real estate investment opportunities using CrewAI. Two specialized AI agents — a Property Researcher and a Property Analyst — work together to produce investor-grade reports for any location and property type.

## How It Works

1. You enter a **location** (e.g., Mumbai, Berlin) and **property type** (e.g., retail, residential)
2. The **Researcher Agent** searches the web and analyzes market trends, rental yields, ROI potential, and risks
3. The **Analyst Agent** takes the research and produces a structured investment report with rankings and recommendations
4. The final report is saved to `investment_report.txt`

## Tech Stack

- **CrewAI** — Multi-agent orchestration framework
- **Google Gemini 2.0 Flash** — LLM for analysis and report generation
- **LangChain** — LLM abstraction layer
- **SerperDev** — Google Search API for real-time market data

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Get API keys

- **Gemini API Key** — [Google AI Studio](https://aistudio.google.com) → Get API Key
- **Serper API Key** — [serper.dev](https://serper.dev) → Sign up (free tier: 2,500 searches)

### 3. Create `.env` file

Copy `.env.example` to `.env` and add your keys:

```
GOOGLE_API_KEY=your_gemini_api_key_here
SERPER_API_KEY=your_serper_api_key_here
```

### 4. Run

```bash
python crew.py
```

## Project Structure

```
├── crew.py          # Entry point — creates the crew and runs the pipeline
├── agents.py        # Agent definitions (Researcher + Analyst)
├── tasks.py         # Task definitions with dynamic location/property input
├── tools.py         # External tools (web search)
├── .env.example     # Template for API keys
└── .gitignore       # Prevents secrets and cache from being committed
```
