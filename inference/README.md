# Machine Gaze Inference

Inference package for the festival prototype. It provides a fast stub analyzer for tests
and a GPU analyzer for `Qwen/Qwen3-VL-30B-A3B-Thinking`.

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
uv run --group gpu inference-worker --daemon \
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

## Report Contract

`inference.contracts.PrivacyReport` contains:

- `riskScore`: integer from `0` to `100`
- `observed`: visible facts and privacy exposure signals
- `speculative`: low-confidence profile-style guesses
- `targeting`: ad-targeting simulation tags
- `safetyNotes`: privacy and protected-trait guardrails
- `model`: model name/version metadata

The backend validates the same JSON shape before marking a session `ready`. The analyzer
postprocesses model output so protected and sensitive traits stay in unsafe-overreach
examples, never in observed facts.

## Checks

```bash
uv run pytest
uv run ruff check
```
