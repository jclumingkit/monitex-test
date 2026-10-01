# Realtime Detection Event System (PoC)

This project is a local security-monitoring demo. It generates detection events,
processes them in a backend, and shows live alerts in an operator dashboard.

## Project Structure and Stack

- `stream/` uses Python and WebSockets to generate mock security events. Its
  relay forwards each event to the backend webhook.
- `backend/` uses Python and FastAPI to validate, classify, correlate, and
  publish alerts. It also runs Ultralytics YOLO against a looped test video to
  detect and track people, then creates events with snapshot images.
- SQLite stores raw events, processed alerts, and correlations locally in
  `backend/data/monitex.db`. The database and tables are created when the
  backend starts, so no separate database server is required.
- `frontend/` uses Next.js, React, TanStack Query, and Tailwind CSS to display
  live alerts and let an operator acknowledge or resolve them.

## How to Set Up and Run

You need Python 3.14 with [uv](https://docs.astral.sh/uv/) and Node.js with npm.
Install each app's dependencies with `uv sync` in `stream/` and `backend/`, and
`npm install` in `frontend/`.

### LLM API Provider

You'll also need an OpenRouter API key which you can get by signing up to [openrouter](https://openrouter.ai/)

Once you have the key, copy and paste `backend/.env.example` in the same directory. Then rename it to `.env`. Finally, paste your API key to `OPEN_ROUTER_API` env variable.

```
-- /backend/.env

OPEN_ROUTER_API=<your-api-key-here>
```

- The project will still work without OpenRouter API key but the event triage and summarization will use the static fallback.
- If you choose other LLM API providers, be sure to update `backend/ingestion/classifier.py` and `backend/ingestion/summarizer.py` and replace it with an SDK that your provider supports.

Once dependencies are installed, open four terminals and start the services in
this order. Leave each command running.

1. Start the mock WebSocket event stream:

   ```bash
   cd stream
   uv run python main.py
   ```

2. Start the FastAPI backend:

   ```bash
   cd backend
   uv run fastapi dev main.py
   ```

3. Start the relay that sends WebSocket events to the backend:

   ```bash
   cd stream
   uv run python relay.py
   ```

4. Start the frontend:

   ```bash
   cd frontend
   npm run dev
   ```

## Test the Demo

1. Open [http://localhost:3000/dashboard](http://localhost:3000/dashboard).
2. Confirm new alerts appear automatically from the mock stream and YOLO video
   detection.
3. Open an alert, then try acknowledging or resolving it.
4. Check [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) to confirm
   the backend is healthy.

The OpenRouter API key in `backend/.env.example` is optional. Without it, the
backend uses local classification and summary rules.

## Video Feed

The background worker that loops the test video, extracts events, and sends it to the backend event queue is located at `backend/workers/loop_video_worker/detection.py`. The test video and YOLO26n is already included in `backend/workers/loop_video_worker`.

You can run the worker independently with the following:

```
// from root directory
cd backend/workers/loop_video_worker
uv run run_detection.py
```

To replicate or change the test video being used, just change `VIDEO_PATH` and run the worker again.
