# Monitex Event Processing Backend

This FastAPI backend receives a continuous stream of security detections and
turns them into alerts that operators can review in the Monitex dashboard.

An event might report motion near a perimeter, a forced door, smoke, a camera
going offline, or a panic button being pressed. The backend checks the event,
estimates its severity, filters likely false alarms, and creates a short summary
for an operator.

## How It Works

1. The stream relay sends a detection event to the backend webhook.
2. The backend validates the event and places it in an in-memory queue.
3. Five workers process queued events concurrently, so up to five events can be
   handled at the same time. Each received event is saved to SQLite first.
4. Trusted alarm types, such as panic buttons and fire alarms, use fixed rules.
5. Other events are classified by Jev through OpenRouter when an API key is
   available. The classifier considers details such as detection confidence,
   location, event type, and local time.
6. Events that are likely false positives are filtered out. Accepted events are
   assigned a severity, given a one-sentence summary, and saved for operator
   review with a pending status.
7. Accepted events are immediately published to connected dashboards over
   server-sent events (SSE).
8. A separate worker correlates recent events from the same site. Repeated or
   combined signals can raise an event's severity and publish the update without
   delaying the initial alert.

```text
Simulated event stream
        |
        v
     Relay
        |
        v
 Backend webhook -> Event queue -> 5 concurrent workers -> SQLite -> SSE
                                       |                         |
                                       v                         v
                           Classify and summarize      Operator dashboard
                                       |
                                       v
                              Correlation queue
                                       |
                                       v
                         Correlate, persist, and republish
```

Events are stored in a local SQLite database at `data/monitex.db`. Raw received
events are stored in `events`, accepted alerts are stored in `processed_events`,
and completed correlation evaluations are stored in `event_correlations`.
Processed events begin with a `pending_operator_review` status and can be
acknowledged or resolved through the API and dashboard.

## Running the Backend

This project uses Python 3.14 and `uv`.

```bash
uv sync
uv run fastapi dev main.py
```

The backend starts at `http://127.0.0.1:8000`. Its health status is available at
`http://127.0.0.1:8000/health`.

On startup, the backend creates the local data directory, initializes the SQLite
schema, starts five event workers, one correlation worker, and the looped video
detection worker. Queues are drained and the database connection is closed
during graceful shutdown.

To use the AI classifier and summarizer, add an OpenRouter API key to
`backend/.env`:

```bash
OPEN_ROUTER_API="your-api-key"
```

The backend loads this file automatically. Existing environment variables take
precedence over values in `.env`. The demo also runs without a key by using
local classification rules and a summary generated from the event fields.

## API Overview

- `POST /api/webhook` validates and queues a detection event.
- `GET /api/get-processed-events` returns paginated alerts with status and date
  filters.
- `GET /api/sites/{site_id}/processed-events` returns a site's paginated event
  history, ordered by the source event timestamp.
- `PATCH /api/processed-events/{event_id}/status` acknowledges or resolves one
  alert.
- `PATCH /api/processed-events/status` updates multiple alerts.
- `GET /api/events/stream` streams new and correlated alert updates over SSE.
- `GET /health` reports service and event queue status.

## Running the Full Demo

Run these components in separate terminals:

1. Start this backend.
2. Start `stream/main.py` to generate simulated security events.
3. Start `stream/relay.py` to forward those events to the backend.

See `../stream/README.md` for the stream commands.

## Current Limits

- The event and correlation queues exist only in memory and are lost when the
  backend stops.
- The SQLite database is local to the backend instance and is not configured for
  multi-instance deployments.
- False-positive events are stored as raw events but are not yet inserted into
  `processed_events`.
- There is no authentication on the webhook.
- Correlation uses fixed demo rules rather than configurable policies.
