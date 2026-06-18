# Machine Gaze

An interactive visual privacy demo for a university festival. Machine Gaze shows how a single uploaded photo can become a playful machine-read profile.

The current version contains a connected Next.js frontend, a working FastAPI backend,
and a Gemini Big Five inference worker that uses Vertex AI through Google Cloud
Application Default Credentials.

## Project Structure

```text
.
├── frontend/    # Next.js interface for display, upload, and admin routes
├── backend/     # FastAPI project for sessions, uploads, state, jobs, and deletion
├── inference/   # Python worker for Gemini Big Five report generation
└── scripts/     # Developer startup scripts
```

## Frontend Routes

```text
/                    Public booth display
/admin               Operator dashboard
/upload/[sessionId]  Mobile upload page
```

Example upload route:

```text
http://localhost:3000/upload/MG-42A9
```

## Requirements

- Node.js and npm for the frontend
- uv and Python 3.12 for the backend and inference worker
- Google Cloud ADC with Vertex AI enabled for the Gemini worker
- Docker is optional

On many university clusters, Node is loaded through `nvm` or a module system. If `npm`
is missing in a new shell, try loading your login profile first:

```bash
source ~/.profile
```

Then verify:

```bash
node --version
npm --version
```

## Run Without Docker

Use this path on servers or university clusters where Docker is not available.

Before running live inference, authenticate and set a project:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project your-project-id
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1
```

From the project root, start backend, frontend, and the worker together:

```bash
./scripts/run-dev.sh
```

For UI-only work without the inference worker:

```bash
SKIP_INFERENCE=1 ./scripts/run-dev.sh
```

Defaults:

- frontend: `http://localhost:3000`
- backend health: `http://localhost:8000/health`
- inference worker: Gemini Big Five analyzer
- backend token defaults come from `.env.example`

### Remote Cluster Access

If the services run on a remote login node or compute node, keep `./scripts/run-dev.sh`
running there and open an SSH tunnel from your laptop:

```bash
ssh -L 3000:localhost:3000 -L 8000:localhost:8000 <user>@<host>
```

Then open on your laptop:

```text
http://localhost:3000
```

### Manual No-Docker Startup

If you prefer separate terminals, run these from the project root.

Terminal 1, backend:

```bash
cd backend
uv sync
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Terminal 2, frontend:

```bash
cd frontend
npm install
npm run dev -- --hostname 0.0.0.0 --port 3000
```

Terminal 3, inference worker:

```bash
cd inference
uv sync
uv run inference-worker --daemon \
  --backend-url http://localhost:8000 \
  --worker-token dev-worker-token
```

## Run With Docker

Docker is optional. Use it only on machines where Docker Engine or Docker Desktop is
already available.

```bash
docker compose up --build
```

Open:

```text
http://localhost:3000
```

Check backend health:

```bash
curl http://localhost:8000/health
```

The current Compose stack starts:

- FastAPI backend on `http://localhost:8000`
- Next.js frontend on `http://localhost:3000`
- a persistent Docker volume for SQLite/uploads

Follow logs:

```bash
docker compose logs -f backend frontend
```

Stop the stack:

```bash
docker compose down
```

Delete persisted session data:

```bash
docker compose down -v
```

## Frontend Quality Checks

Run lint:

```bash
cd frontend
npm run lint
```

Run a production build:

```bash
cd frontend
npm run build
```

Start the built app:

```bash
cd frontend
npm run start
```

## Backend

The backend is a Python/FastAPI project managed by `uv`.

```bash
cd backend
uv sync
uv run uvicorn backend.app:app --reload
```

The backend owns:

- session creation and expiry
- upload validation
- temporary storage
- queued worker jobs
- result status
- deletion after finish or timeout
- admin/operator actions

Create a session with:

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Authorization: Bearer dev-admin-token"
```

## Inference

The inference worker is a Python project managed by `uv`. It claims backend jobs,
downloads the sanitized uploaded image, sends it to Gemini through Vertex AI using ADC,
and completes the job with a five-trait report.

```bash
cd inference
uv sync
uv run inference-worker --once
```

Use `--daemon` for continuous booth mode. The worker produces a playful festival
interpretation, not a psychometric assessment.

## Development Notes

The frontend uses Next.js proxy routes to connect the booth display, mobile upload flow,
and admin dashboard to the FastAPI backend without exposing operator secrets in the browser.

The intended production flow is:

```text
public display creates session
student scans QR code
student uploads photo
backend validates and stores temporarily
Gemini worker generates a Big Five report
frontend displays five trait scores
operator presses finish
backend deletes temporary data
```

Data should also auto-expire if a user abandons the flow.
