import os
import subprocess
import time
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field, PrivateAttr

# USD per 1M (input, output) tokens at Google's paid rates, checked 2026-11-02.
# The free tier charges nothing; this estimates what a run would cost in production.
MODEL_PRICES = {"gemini-3.1-flash-lite": (0.25, 1.50)}


def get_git_sha():
    """Identify the code version. Images have no .git folder, so hosts provide it instead."""
    hosted_sha = os.getenv("GIT_SHA") or os.getenv("RENDER_GIT_COMMIT")
    if hosted_sha:
        return hosted_sha[:7]
    try:
        output = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        )
        return output.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def estimate_cost(model, prompt_tokens, completion_tokens):
    """Return the estimated USD cost, or None for a model with no known price."""
    if model not in MODEL_PRICES:
        return None
    input_price, output_price = MODEL_PRICES[model]
    return round((prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000, 6)


class StepRecord(BaseModel):
    agent: str
    finished_after_seconds: float
    tool_calls: int = 0


class RunTelemetry(BaseModel):
    """Everything needed to trace a run: what ran, how long it took and what it used."""

    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    location: str
    property_type: str
    model: str
    prompt_version: str
    git_sha: str = Field(default_factory=get_git_sha)
    status: str = "running"
    error: str | None = None
    latency_seconds: float | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    llm_requests: int = 0
    estimated_cost_usd: float | None = None
    steps: list[StepRecord] = Field(default_factory=list)

    _start: float = PrivateAttr(default_factory=time.perf_counter)

    def _elapsed(self):
        return round(time.perf_counter() - self._start, 2)

    def record_step(self, task_output):
        """Crew task_callback: runs each time an agent finishes its task."""
        messages = getattr(task_output, "messages", None) or []
        self.steps.append(
            StepRecord(
                agent=str(task_output.agent).strip(),
                finished_after_seconds=self._elapsed(),
                tool_calls=sum(message.get("role") == "tool" for message in messages),
            )
        )

    def finish(self, token_usage):
        self.status = "success"
        self.latency_seconds = self._elapsed()
        self.prompt_tokens = token_usage.prompt_tokens
        self.completion_tokens = token_usage.completion_tokens
        self.total_tokens = token_usage.total_tokens
        self.llm_requests = token_usage.successful_requests
        self.estimated_cost_usd = estimate_cost(self.model, self.prompt_tokens, self.completion_tokens)

    def fail(self, error):
        self.status = "failed"
        self.error = str(error)[:300]
        self.latency_seconds = self._elapsed()
