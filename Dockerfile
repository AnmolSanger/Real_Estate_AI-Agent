# Slim keeps the base small, and 3.12 matches local development.
FROM python:3.12-slim

WORKDIR /app

# Copy requirements first: Docker reuses this cached layer unless they change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Run as a normal user, not root. UID 1000 is also what Hugging Face Spaces uses.
RUN useradd --create-home --uid 1000 appuser
COPY --chown=appuser . .
RUN mkdir artifacts && chown appuser artifacts
USER appuser

EXPOSE 8000 8501

# One image, two apps: APP_MODE=ui starts Streamlit, otherwise the API starts.
CMD ["sh", "-c", "if [ \"$APP_MODE\" = ui ]; then exec python -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true; else exec python -m uvicorn api:app --host 0.0.0.0 --port 8000; fi"]
