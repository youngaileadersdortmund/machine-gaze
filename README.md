# Machine Gaze

An interactive visual privacy demo for a university festival. Machine Gaze shows what AI systems can observe, infer, and over-assume from a single uploaded photo.

The current version contains the initial frontend experience: a public booth display, a mobile upload placeholder, and an operator dashboard placeholder. Backend and inference projects are initialized but not wired into the frontend yet.

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
/admin               Operator dashboard placeholder
/upload/[sessionId]  Mobile upload placeholder
```

Example upload route:

```text
http://localhost:3000/upload/MG-42A9
```

## Requirements

- Node.js and npm for the frontend
- uv and Python 3.12 for backend/inference development

On the cluster, Node was installed with `nvm`. If `npm` is missing in a new shell, load `nvm` first:

```bash
source ~/.profile
```

Then verify:

```bash
node --version
npm --version
```

## Run The Website Locally

From the project root:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

If you are running the dev server on a remote machine or cluster node, bind to all interfaces:

```bash
cd frontend
npm run dev -- --hostname 0.0.0.0
```

If you are viewing from your laptop through SSH, use port forwarding:

```bash
ssh -L 3000:localhost:3000 abdelrahim@ml2ran12
```

Then open on your laptop:

```text
http://localhost:3000
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
uv run python --version
```

The backend will own:

- session creation and expiry
- upload validation
- temporary storage
- result status
- deletion after finish or timeout
- admin/operator actions

## Inference

The inference project is also managed by `uv`.

```bash
cd inference
uv run python --version
```

The inference project will own:

- image preprocessing
- OCR
- object/person detection
- vision-language model analysis
- privacy risk scoring
- structured report generation

GPU/PyTorch dependencies are intentionally not installed yet. Choose those after confirming the cluster CUDA/PyTorch compatibility and model plan.

## Development Notes

The frontend currently uses mocked state so the booth flow can be designed before the backend and GPU worker are connected.

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
