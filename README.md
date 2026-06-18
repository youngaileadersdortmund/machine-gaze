# Machine Gaze

An interactive visual privacy demo for a university festival. Machine Gaze shows what AI systems can observe, infer, and over-assume from a single uploaded photo.

The current version contains a connected frontend, a working FastAPI backend, a fast
stub worker for smoke tests, and a Gemini worker for live privacy reports.

## Project Structure

```text
.
├── frontend/    # Next.js interface for display, upload, and admin routes
├── backend/     # FastAPI project for sessions, uploads, state, and deletion
├── inference/   # Python project for image analysis and report generation
├── docs/        # Architecture, privacy, deployment, and event notes
├── scripts/     # Developer and operations scripts
└── shared/      # Shared contracts and schemas later
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
- uv and Python 3.12 for backend/inference development
- Google Cloud ADC with Vertex AI enabled for the Gemini inference worker
- Optional: NVIDIA GPU + CUDA-compatible PyTorch for the Qwen inference worker

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

From the project root, start backend, frontend, and the inference worker together:

```bash
./scripts/run-dev.sh
```

Defaults:

- frontend: `http://localhost:3000`
- backend health: `http://localhost:8000/health`
- inference worker: real `gemini` analyzer
- backend token defaults come from `.env.example`

For a fast smoke test without loading the model:

```bash
INFERENCE_ANALYZER=stub ./scripts/run-dev.sh
```

The default Gemini path uses Google Cloud Application Default Credentials and Vertex AI.
Before running live reports, authenticate and set your project:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project your-project-id
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=global
export GOOGLE_GENAI_USE_ENTERPRISE=true
```

The Qwen path is still available for local GPU inference. It downloads model weights
into `HF_HOME` on first run and needs the `inference` GPU dependency group.

To use Google Cloud Vision as a lower-level debug analyzer, authenticate with
Application Default Credentials and choose the Google analyzer:

```bash
gcloud auth application-default login
INFERENCE_ANALYZER=google-vision ./scripts/run-dev.sh
```

The Google Vision analyzer returns grounded visual annotations such as people/object
signals, OCR text, logos, landmarks, safe-search likelihoods, and image properties. It
does not infer sensitive traits such as race, religion, sexuality, politics, or income.
If your ADC user credentials need an explicit billing/quota project, set
`GOOGLE_CLOUD_QUOTA_PROJECT=your-project-id`.

### Remote Cluster Access

If the services run on a remote login node or compute node, keep `./scripts/run-dev.sh`
running there and open an SSH tunnel from your laptop:

```bash
ssh -L 3000:localhost:3000 -L 8000:localhost:8000 <user>@<host>
```

Replace `<user>` and `<host>` with your own university account and server hostname.
Then open on your laptop:

```text
http://localhost:3000
```

If your cluster requires connecting through a login node to a compute node, use the
equivalent SSH tunnel or `ProxyJump` command for your environment.

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

Terminal 3, fast stub inference worker:

```bash
cd inference
uv sync
INFERENCE_ANALYZER=stub uv run inference-worker --daemon \
  --backend-url http://localhost:8000 \
  --worker-token dev-worker-token
```

Terminal 3, Gemini worker:

```bash
cd inference
uv sync
uv run inference-worker --daemon --analyzer gemini \
  --backend-url http://localhost:8000 \
  --worker-token dev-worker-token
```

Terminal 3, Google Vision worker:

```bash
cd inference
uv sync
uv run inference-worker --daemon --analyzer google-vision \
  --backend-url http://localhost:8000 \
  --worker-token dev-worker-token
```

Terminal 3, real Qwen GPU worker:

```bash
cd inference
uv sync --group gpu
uv run --group gpu inference-worker --daemon --analyzer qwen \
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

The default Compose stack starts:

- FastAPI backend on `http://localhost:8000`
- Next.js frontend on `http://localhost:3000`
- continuous inference worker using the fast stub analyzer
- persistent Docker volumes for SQLite/uploads and Hugging Face cache

Follow logs:

```bash
docker compose logs -f backend frontend inference-worker
```

Stop the stack:

```bash
docker compose down
```

Delete persisted session/model-cache volumes:

```bash
docker compose down -v
```

### Docker GPU Worker

To run the real Qwen worker instead of the stub worker, use the GPU override:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

This builds the inference image with the `gpu` dependency group and requests one NVIDIA
GPU for `inference-worker`. The first run downloads `Qwen/Qwen3-VL-30B-A3B-Thinking`
into the `machine_gaze_hf_cache` Docker volume.

Useful Docker environment overrides:

```bash
FRONTEND_PUBLIC_URL=http://your-hostname:3000
ADMIN_TOKEN=change-me
BACKEND_ADMIN_TOKEN=change-me
WORKER_TOKEN=change-me
INFERENCE_WORKER_TOKEN=change-me
docker compose up --build
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
- result status
- deletion after finish or timeout
- admin/operator actions

Create a session with:

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Authorization: Bearer dev-admin-token"
```

## Inference

The inference project is also managed by `uv`.

Fast stub worker:

```bash
cd inference
uv sync
INFERENCE_ANALYZER=stub uv run inference-worker --daemon \
  --backend-url http://localhost:8000 \
  --worker-token dev-worker-token
```

Google Vision worker:

```bash
cd inference
uv sync
uv run inference-worker --daemon --analyzer google-vision \
  --backend-url http://localhost:8000 \
  --worker-token dev-worker-token
```

Gemini worker:

```bash
cd inference
uv sync
uv run inference-worker --daemon --analyzer gemini \
  --backend-url http://localhost:8000 \
  --worker-token dev-worker-token
```

Real Qwen GPU worker:

```bash
cd inference
uv sync --group gpu
uv run --group gpu inference-worker --daemon --analyzer qwen \
  --backend-url http://localhost:8000 \
  --worker-token dev-worker-token
```

The inference project owns the report contract, a test stub, a Gemini worker, a Google
Vision worker, and a Qwen GPU worker for:

- image preprocessing
- OCR
- object/person detection
- vision-language model analysis
- privacy risk scoring
- structured report generation

The Qwen worker requires a CUDA-compatible PyTorch install and a visible NVIDIA GPU.
The first run may take a while because model weights are downloaded into `HF_HOME`.

## Development Notes

The frontend uses Next.js proxy routes to connect the booth display, mobile upload flow, and admin dashboard to the FastAPI backend without exposing operator secrets in the browser.

The intended production flow is:

```text
public display creates session
student scans QR code
student uploads photo
backend validates and stores temporarily
inference worker analyzes image
frontend displays observed facts and speculative assumptions
operator presses finish
backend deletes temporary data
```

Data should also auto-expire if a user abandons the flow.

## Privacy Principle

Machine Gaze should distinguish between:

- observed facts: visible objects, clothing, text, faces, scene clues
- speculative assumptions: lifestyle, personality, ads, demographics, sensitive traits

Speculative or sensitive claims should be clearly labeled as unreliable overreach, not presented as truth.
