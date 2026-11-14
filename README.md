# EstateMind

[![CI](https://github.com/AnmolSanger/Real_Estate_AI-Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/AnmolSanger/Real_Estate_AI-Agent/actions/workflows/ci.yml)

A multi-agent AI system that researches real estate markets and produces investment reports. LLM agents find properties and reason about them, while plain Python calculates every financial metric, so the numbers cannot be hallucinated.

**Live demo:** [Streamlit app](https://estatemind-ui.onrender.com) (password protected) · [API docs](https://estatemind-api.onrender.com/docs) · [Sample report](docs/sample_report.md)

The free services sleep when idle, so the first request can take about a minute. Reports are a project demo, not investment advice.

## How it works

```text
Streamlit UI ─┐
FastAPI ──────┼─> pipeline.py
CLI ──────────┘        │
                       ▼
        Researcher ──> Financial Modeler ──> Analyst
        (web search)   (finance tool)        (written report)
                       │
                       ▼
        Python drops implausible properties
        Python computes every metric and the downside case
                       │
                       ▼
        Report and telemetry saved to Backblaze B2
        (or ./artifacts/ if the upload fails)
```

1. The **Researcher** searches the web for candidate properties, with prices, rents and sources.
2. The **Financial Modeler** runs the deterministic ROI tool on each candidate, plus a downside case.
3. The **Analyst** writes the report. It may say a result is positive or negative, but it does not write calculated figures.
4. **Python** computes the final metrics and appends them as a verified table.

## Supported locations

EstateMind accepts only **Indian cities with 1 lakh or more people**: 467 cities across 31 states and union territories. Users pick a state, then a city, and the agents receive both, such as "Pune, Maharashtra".

- **Source:** "Urban Agglomerations/Cities having population 1 lakh and above", Provisional Population Totals, Census of India 2011. It is the latest official city-level data, because Census 2027 results are not yet published. The original censusindia.gov.in link is gone, so the list was built from an [archived copy](https://web.archive.org/web/20170101050957/http://www.censusindia.gov.in/2011-prov-results/paper2/data_files/India2/Table_3_PR_UA_Citiees_1Lakh_and_Above.pdf).
- **Conversion:** [scripts/build_city_list.py](scripts/build_city_list.py) turns the PDF into [data/indian_cities.csv](data/indian_cities.csv). It merges urban areas with their main city, moves Telangana's cities out of Andhra Pradesh, and uses current names, such as Gurugram and Prayagraj. Each row keeps its original Census name.
- **Not included:** Sikkim, Arunachal Pradesh, Ladakh, Lakshadweep, and Dadra and Nagar Haveli and Daman and Diu had no city of 1 lakh or more in 2011. Places the Census counted inside a larger urban area, like Thane within Mumbai, are not listed separately.

## Design decisions

| Decision | Why |
|---|---|
| LLM picks inputs, Python does the math | LLMs make arithmetic mistakes. `finance.py` gives the same output for the same input every time |
| Only listed Indian cities accepted | All evals ran on Indian markets with Indian loan defaults, and a fixed list keeps free text out of the prompts |
| City list stored in the repo | It is small reference data the code depends on, so it is versioned with the code. Object storage is for run outputs |
| One `pipeline.py` for every interface | Streamlit, the API and the CLI cannot drift apart |
| Agents built per run | Concurrent runs share no state |
| Loose parsing, then checks in Python | A strict schema rejected a whole run over one rent of 0. Now only the bad property is dropped |
| Plausibility check on rent and price | A live run used a per-sq-ft price and produced a 3,901% Cap Rate |
| `POST /analyze` returns a job ID | Reports take minutes, which is too long to hold an HTTP request open |
| One job at a time | Each report makes about 18 LLM calls under one shared quota |
| Finance tool in-process, also exposed over MCP | In-process is simpler for the crew, and MCP lets outside clients reuse the same formulas |
| boto3 with a configurable endpoint | Storage works with Backblaze today and AWS S3 with config changes only |

## Failure handling

| Failure | What happens |
|---|---|
| Gemini 429 rate limit | The crew stays under 4 requests a minute |
| Gemini 503 overload | Each call retries with backoff, up to 6 attempts |
| Bad price or rent | That property is excluded and named in the report |
| No believable property | The written report stays, and no metrics are shown |
| Storage upload fails | Files save to `./artifacts/`, and the report still returns |
| Run crashes | Telemetry is still saved, and the user gets a readable error |
| Agent gets stuck | Iteration limits and a 300-second time limit stop it |

## Evaluation

`evals/run_evals.py` runs 5 live reports across the four property types, with Pune run twice to check stability. Evals call real APIs, so they run by hand, not in CI. Full results are in [evals/results](evals/results).

The table below comes from the earlier suite, which ran 6 reports including a mixed-use case.

| Check | Prompt v3 | Prompt v4 | Prompt v5 |
|---|---|---|---|
| Runs completed | 6/6 | 5/6 | 6/6 |
| Valid structured output | 100% | 83% | 100% |
| Finance tool used | 100% | 83% | 100% |
| Numbers match the engine | 100% | 83% | 100% |
| No LLM-written metrics | 100% | 83% | 100% |
| All sections present | 100% | 83% | 100% |
| Plausible inputs | 100% | 83% | 100% |
| Reliable sources | 67% | 83% | 100% |
| Rent spread (limit 25%) | 0% | 31.4% | **46% (fails)** |

- **v4** removed social media links as price sources, and exposed the strict-schema crash.
- **v5** fixed that crash by moving value checks from parsing into Python.

**Property type check, added later.** A new scorer checks that each source URL names the requested type, like `2-bhk-flats` for Residential or `warehouse` for Industrial. Applied to the saved results with no new API calls:

- **Mixed-use failed in every version.** All its sources were commercial listings, because Indian property portals rarely list mixed-use. It was removed, leaving four types.
- **v5 passed 3 of its 5 other runs.** An Industrial pick came from a commercial listing, and a Retail source URL had no category words.

The check reads URL words only, so it can fail a correct listing whose URL gives no category.

### Latest run: four property types, prompt v5

| Check | Result |
|---|---|
| Runs completed | 5/5 |
| Valid structured output, finance tool used, numbers match, no LLM-written metrics, sections present, plausible inputs, reliable sources | 100% each |
| Property type matches | 80% |
| Rent spread (limit 25%) | 25.0%, exactly on the limit |

- **Property type:** the Chennai industrial run used a commercial listing again, the same failure as in v5.
- **Rent spread:** Baner came back at ₹32,000 and ₹40,000 a month in the two Pune runs. It only just meets the limit, so stability is still not solved.
- **Weak industrial inputs:** two Chennai picks earned yearly rent of about 1.2% of their price, close to the plausibility floor, and one was a land listing rather than a building.

### Averaging listings: prompt v6

Each area used to rely on one sale listing and one rent listing, often for different-sized properties. Now the agents choose one comparable kind of unit per area, such as "2 BHK flat, about 1,000 sq ft", and collect 2-3 prices and 2-3 rents for it. Python averages them, and the report shows how many listings went into each average, with a link to every source.

| Check | v5 | v6 |
|---|---|---|
| Rent spread (limit 25%) | 25.0% | **17.9%** |
| At least 2 sale and 2 rent listings per area | Not measured | 80% |
| Property type matches | 80% | 80% |
| The other seven checks | 100% | 100% |
| Tokens per report | about 59k-76k | about 70k-99k |

- **Industrial improved:** every Chennai source is now a warehouse or shed listing, with no commercial listings or land.
- **A scorer bug was found:** the saved v6 file reports 60% for property type, because the check did not recognise `2bhk` in a URL. With the fix, the score is 80%. The one remaining failure is a URL with no category words.
- **Listings in one area still vary a lot.** For example, Hinjewadi prices ranged from ₹61 lakh to ₹1.1 crore in one run, so the "comparable unit" rule is not always followed.
- **Averaging costs more:** extra searches use about 15-30% more tokens per report.

## Known limitations

- **Inputs are not stable.** The same property's rent can differ a lot between runs, because each run samples different listings. The next fix is to average several listings per area.
- **A property's type is not verified.** The type guides the agents' search, and the eval checks source URLs, but nothing confirms that a listing is really that type.
- **Correct math does not make inputs true.** A plausible but wrong price still passes. Figures come from web listings and are not verified against market data.
- **The eval sample is small.** Six runs per version catch failures, but do not prove statistical confidence.
- **Jobs live in memory.** A restart loses them, and only one server process is supported. Production would use a queue and a database.
- **The city list is from 2011.** City sizes have changed, and smaller cities may have too few listings for a full report.
- **Prompt injection is reduced, not removed.** Locations come from a fixed list and agents are told to ignore instructions in web pages.
- **This is LLMOps, not classic MLOps.** There is no model training, registry or drift monitoring.

## Run it locally

You need Python 3.12 and free keys from [Google AI Studio](https://aistudio.google.com) and [Serper](https://serper.dev).

```bash
git clone https://github.com/AnmolSanger/Real_Estate_AI-Agent.git
cd Real_Estate_AI-Agent
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
copy .env.example .env
```

On macOS or Linux, use `.venv/bin/pip` and `cp` instead. Then add your keys to `.env`. Backblaze settings are optional: without them, reports save to `./artifacts/`.

| Command | What it starts |
|---|---|
| `.venv\Scripts\python -m streamlit run app.py` | Streamlit app at `localhost:8501` |
| `.venv\Scripts\python -m uvicorn api:app --port 8000` | API at `localhost:8000/docs` |
| `.venv\Scripts\python crew.py` | Command line version |
| `.venv\Scripts\python mcp_server.py` | MCP server over stdio |
| `.venv\Scripts\python -m pytest` | Tests, with no API keys needed |
| `.venv\Scripts\python -m evals.run_evals` | Live evals, which use API quota |

### With Docker

```bash
docker compose up --build
```

This starts both apps from one image. Secrets stay out of the image and are passed in from `.env`.

## API

Requests to `/analyze` and `/jobs` need an `X-API-Key` header.

```bash
curl -X POST https://estatemind-api.onrender.com/analyze -H "X-API-Key: YOUR_KEY" -H "Content-Type: application/json" -d "{\"state\": \"Maharashtra\", \"city\": \"Pune\", \"property_type\": \"Residential\"}"
```

| Endpoint | Purpose |
|---|---|
| `GET /health` | Checks the service is alive, using no LLM calls |
| `POST /analyze` | Starts a report and returns a job ID |
| `GET /jobs/{job_id}` | Returns the status, then the report and telemetry |

## Project structure

```text
├── pipeline.py        # Core path used by every interface
├── agents.py          # Researcher, Financial Modeler and Analyst
├── tasks.py           # Prompts and the prompt version
├── tools.py           # Search tool and ROI calculator tool
├── finance.py         # Deterministic formulas and plausibility check
├── schemas.py         # Pydantic models
├── telemetry.py       # Latency, tokens, cost and run metadata
├── storage.py         # S3-compatible storage with local fallback
├── app.py             # Streamlit app
├── api.py             # FastAPI service
├── crew.py            # Command line entry point
├── mcp_server.py      # MCP server for the finance engine
├── cities.py          # Loads the supported Indian cities
├── data/              # Census-based city list
├── scripts/           # Builds the city list from the Census PDF
├── evals/             # Live evaluation suite and saved results
├── tests/             # Mocked test suite
├── docs/              # Sample report
└── Dockerfile         # One image for the API and Streamlit
```

## Tech stack

Python, CrewAI, Gemini, MCP, FastAPI, Streamlit, Pydantic, Serper, boto3, Backblaze B2, Docker, Render, pytest, GitHub Actions.
