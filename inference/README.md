# Machine Gaze Inference

Inference package for the festival prototype. It provides a fast stub analyzer for tests,
a Gemini analyzer for live privacy reports, a Google Vision API debug analyzer, and a GPU
analyzer for `Qwen/Qwen3-VL-30B-A3B-Thinking`.

The report separates visible observations from weak speculation and keeps sensitive or
protected traits as unsafe-overreach examples, not factual predictions.

## GPU Setup

The Qwen worker dependencies live in the `gpu` dependency group so normal tests do not
download a large CUDA stack.

```bash
uv sync --group gpu
uv run --group gpu python - <<'PY'
import torch
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "no cuda")
PY
```

The first real Qwen run downloads model weights into `HF_HOME`:

```bash
export HF_HOME=../hf_cache
```

## Run The Worker

Start the backend first. Then from this directory:

```bash
uv run inference-worker --daemon --analyzer gemini \
  --backend-url http://localhost:8000 \
  --worker-token dev-worker-token
```

The worker:

1. Sends a `warming` heartbeat while loading the model.
2. Sends a `ready` heartbeat after the model is warm.
3. Claims queued backend jobs continuously.
4. Downloads sanitized images through the worker-authenticated API.
5. Posts validated reports back to `/api/worker/jobs/{job_id}/complete`.

For a fast smoke test without the model:

```bash
INFERENCE_ANALYZER=stub uv run inference-worker --once
```

For Gemini on Vertex AI:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project your-project-id
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=global
export GOOGLE_GENAI_USE_ENTERPRISE=true
uv run inference-worker --daemon --analyzer gemini \
  --backend-url http://localhost:8000 \
  --worker-token dev-worker-token
```

For Google Cloud Vision without the local GPU model:

```bash
gcloud auth application-default login
uv run inference-worker --daemon --analyzer google-vision \
  --backend-url http://localhost:8000 \
  --worker-token dev-worker-token
```

Set `GOOGLE_CLOUD_QUOTA_PROJECT=your-project-id` if your local ADC user credentials
need an explicit billing/quota project.

## Report Contract

`inference.contracts.PrivacyReport` contains:

- `riskScore`: integer from `0` to `100`
- `observed`: persona-read sections displayed as the main dossier
- `speculative`: deeper persona guesses displayed below the main dossier
- `targeting`: influence hooks or ad/algorithmic categories
- `safetyNotes`: optional notes, usually empty for Gemini persona reports
- `model`: model name/version metadata

`riskScore` and group `confidence` remain in the wire contract for backend compatibility,
but the frontend does not display them for Gemini persona reports.

## Checks

```bash
uv run pytest
uv run ruff check
```
