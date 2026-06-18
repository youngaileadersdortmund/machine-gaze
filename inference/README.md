# Machine Gaze Inference

Python worker for the Machine Gaze booth. It claims queued backend jobs, downloads the
sanitized uploaded image, sends it to Gemini through Vertex AI using Application Default
Credentials, and completes the job with a Big Five report.

The report is a playful festival interpretation of visible presentation, not a
psychometric assessment.

## Setup

Authenticate with Google Cloud ADC and choose a Vertex AI project:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project your-project-id
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1
```

Install dependencies:

```bash
uv sync
```

## Run

Process one queued job:

```bash
uv run inference-worker --once \
  --backend-url http://localhost:8000 \
  --worker-token dev-worker-token
```

Run continuously:

```bash
uv run inference-worker --daemon \
  --backend-url http://localhost:8000 \
  --worker-token dev-worker-token
```

Useful environment variables:

```text
INFERENCE_BACKEND_URL=http://localhost:8000
INFERENCE_WORKER_TOKEN=dev-worker-token
GEMINI_MODEL_ID=gemini-2.5-flash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

## Checks

```bash
uv run pytest
uv run ruff check
```
