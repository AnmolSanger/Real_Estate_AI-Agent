# Real Estate Investment AI Agent

A multi-agent AI system that analyzes real estate investment opportunities using CrewAI and Google Gemini. Two specialized AI agents — a Property Researcher and a Property Analyst — collaborate autonomously to produce investor-grade reports for any location and property type worldwide.

## Features

- **Multi-Agent Architecture** — Two AI agents with distinct roles work together in a pipeline
- **Real-Time Web Research** — Researcher agent searches the web for live market data using Google Search API
- **Investor-Grade Reports** — Analyst agent produces structured reports with ROI projections, risk matrices, and recommendations
- **Dynamic Input** — Analyze any location with property types: Residential, Commercial, Retail, Industrial, Mixed-Use
- **Streamlit Web Interface** — Interactive UI with real-time status updates and downloadable reports
- **CLI Support** — Run directly from the terminal for quick analysis

## How It Works

```
User Input (Location + Property Type)
        │
        ▼
┌─────────────────────────┐
│   Property Researcher   │  → Searches the web for market data
│       (Agent 1)         │  → Analyzes trends, yields, ROI
│                         │  → Assesses risks and competition
└───────────┬─────────────┘
            │ Research findings passed as context
            ▼
┌─────────────────────────┐
│    Property Analyst     │  → Reads research output
│       (Agent 2)         │  → Creates structured report
│                         │  → Ranks properties, adds risk matrix
└───────────┬─────────────┘
            │
            ▼
   Final Investment Report
```

## Tech Stack

| Technology | Purpose |
|---|---|
| **CrewAI** | Multi-agent orchestration framework |
| **Google Gemini** | LLM for analysis and report generation |
| **LiteLLM** | Unified LLM API interface (used internally by CrewAI) |
| **SerperDev** | Google Search API for real-time market data |
| **Streamlit** | Interactive web UI |

## Getting Started

### Prerequisites

- Python 3.12+
- A Google Gemini API key (free)
- A Serper API key (free tier: 2,500 searches)

### Step 1 — Clone the repository

```bash
git clone https://github.com/AnmolSanger/Real_Estate_AI-Agent.git
cd Real_Estate_AI-Agent
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Get API keys

1. **Gemini API Key** — Go to [Google AI Studio](https://aistudio.google.com), sign in, click "Get API Key" and create one
2. **Serper API Key** — Go to [serper.dev](https://serper.dev), sign up, and copy your API key from the dashboard

### Step 4 — Set up environment variables

Create a `.env` file in the project root (you can copy from the example):

```bash
cp .env.example .env
```

Then edit `.env` and add your keys:

```
GOOGLE_API_KEY=your_gemini_api_key_here
SERPER_API_KEY=your_serper_api_key_here
```

### Step 5 — Run the application

**Option A — Web App (recommended):**

```bash
streamlit run app.py
```

The app opens automatically in your browser. Enter a location and property type, then click "Analyze Properties". The agents will work through the analysis and display the report on screen.

**Option B — Command Line:**

```bash
python crew.py
```

Follow the prompts to enter a location and property type. The report will print to the terminal and save to `investment_report.txt`.

## Project Structure

```
├── app.py               # Streamlit web app
├── crew.py              # CLI entry point
├── agents.py            # AI agent definitions (Researcher + Analyst)
├── tasks.py             # Task definitions with dynamic user input
├── tools.py             # External tools (Google Search via SerperDev)
├── requirements.txt     # Python dependencies
├── .env.example         # Template for required API keys
└── .gitignore           # Prevents secrets and cache from being committed
```

## Sample Output

The report includes:

- **Executive Summary** — Key findings and investment thesis
- **Top Investment Picks** — Ranked properties with price, rental yield, and ROI projections
- **Market Overview** — Current trends, growth drivers, demand-supply dynamics
- **Risk Matrix** — Categorized risks (High/Medium/Low) with mitigation strategies
- **Final Recommendation** — Clear invest/hold/avoid verdict with reasoning
