# Machine Gaze Backend

FastAPI service for the festival booth flow. It creates short-lived upload sessions,
validates and sanitizes one photo per session, queues inference work in SQLite, serves
worker-only image downloads, stores temporary reports, and deletes personal data on
finish or expiry.

## Run Locally

From this directory:

```bash
uv sync
uv run uvicorn backend.app:app --reload
```

Open:

```text
http://localhost:8000/health
```

The defaults are development-friendly. Copy the root `.env.example` to `.env` and change
`ADMIN_TOKEN` and `WORKER_TOKEN` before using this at the booth.

## API Flow

Admin/operator requests require:

```text
Authorization: Bearer dev-admin-token
```

Worker requests require:

```text
Authorization: Bearer dev-worker-token
```

Main endpoints:

- `GET /health`
- `POST /api/sessions`
- `GET /api/sessions/{session_id}`
- `POST /api/sessions/{session_id}/upload?token=...`
- `POST /api/sessions/{session_id}/finish`
- `GET /api/admin/sessions`
- `POST /api/worker/jobs/claim`
- `POST /api/worker/heartbeat`
- `GET /api/worker/jobs/{job_id}/image`
- `POST /api/worker/jobs/{job_id}/complete`
- `POST /api/worker/jobs/{job_id}/fail`

Upload form fields:

- `display_name`: participant nickname
- `consent`: must be `true`
- `file`: JPEG, PNG, or WebP image

The backend strips EXIF by re-saving the image, stores only the sanitized copy, and
deletes raw upload bytes immediately.

## Worker Health

The inference worker should send heartbeats to:

```text
POST /api/worker/heartbeat
```

with:

```json
{
  "status": "warming",
  "modelId": "Qwen/Qwen3-VL-30B-A3B-Thinking",
  "modelVersion": "transformers"
}
```

`GET /health` returns queue counts and worker status. Processing jobs older than
`WORKER_JOB_TIMEOUT_SECONDS` are requeued until `WORKER_MAX_ATTEMPTS`, then marked
as session errors.

## Manual Acceptance

Create a session:

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Authorization: Bearer dev-admin-token"
```

Upload a photo to the returned URL:

```bash
curl -X POST "http://localhost:8000/api/sessions/MG-XXXX/upload?token=TOKEN" \
  -F "display_name=Mariam" \
  -F "consent=true" \
  -F "file=@/path/to/photo.jpg"
```

Run one inference worker job from `../inference`:

```bash
uv run inference-worker --backend-url http://localhost:8000 --worker-token dev-worker-token
```

Poll the report:

```bash
curl http://localhost:8000/api/sessions/MG-XXXX
```

Finish and delete temporary data:

```bash
curl -X POST http://localhost:8000/api/sessions/MG-XXXX/finish \
  -H "Authorization: Bearer dev-admin-token"
```

## Checks

```bash
uv run pytest
uv run ruff check
```
