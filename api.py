import logging
import os
import secrets
import threading
import uuid

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from pipeline import run_analysis
from schemas import AnalyzeRequest, Job
from telemetry import get_git_sha

logger = logging.getLogger(__name__)

# Each crew makes about 18 LLM calls under one shared Gemini quota, so run one at a time.
MAX_ACTIVE_JOBS = 1
MAX_STORED_JOBS = 100

app = FastAPI(title="EstateMind API", description="Multi-agent real estate investment analysis.")

# Jobs live in memory, so they are lost on restart. Production would use Redis or a database.
jobs: dict[str, Job] = {}
jobs_lock = threading.Lock()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(api_key_header)):
    expected = os.getenv("ESTATEMIND_API_KEY")

    # Refuse everything if no key is configured, rather than running open.
    if not expected:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "API key is not configured")
    # compare_digest takes the same time wherever strings differ, which blocks timing attacks.
    if not api_key or not secrets.compare_digest(api_key.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing API key")


def create_job():
    """Reserve the run slot. The lock stops two requests from both seeing it free."""
    with jobs_lock:
        if sum(job.status in ("queued", "running") for job in jobs.values()) >= MAX_ACTIVE_JOBS:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "An analysis is already running")

        finished = [job_id for job_id, job in jobs.items() if job.status in ("succeeded", "failed")]
        for job_id in finished[: max(0, len(jobs) - MAX_STORED_JOBS + 1)]:
            del jobs[job_id]

        job = Job(job_id=uuid.uuid4().hex[:12])
        jobs[job.job_id] = job
        return job


def run_job(job, request):
    job.status = "running"
    try:
        job.result = run_analysis(request.location, request.property_type, request.assumptions)
        job.status = "succeeded"
    except Exception:
        # Log the details but keep internal errors out of the response.
        logger.exception("Job %s failed", job.job_id)
        job.error = "The analysis could not finish. Please try again later."
        job.status = "failed"


@app.get("/health")
def health():
    """Liveness check. It makes no LLM calls, so it is safe to call often."""
    return {"status": "ok", "version": get_git_sha()}


@app.post("/analyze", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_api_key)])
def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks) -> Job:
    """Start an analysis and return at once, because a run takes minutes."""
    job = create_job()
    background_tasks.add_task(run_job, job, request)
    return job


@app.get("/jobs/{job_id}", dependencies=[Depends(require_api_key)])
def get_job(job_id: str) -> Job:
    """Check a job's status, and get its report once it has succeeded."""
    if job_id not in jobs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return jobs[job_id]
