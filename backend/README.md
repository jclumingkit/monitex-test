# Monitex Event Processing Demo

This backend demonstrates how a security monitoring system could receive a
continuous stream of detection events and turn them into useful alerts.

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

```text
Simulated event stream
        |
        v
     Relay
        |
        v
 Backend webhook -> Event queue -> 5 concurrent workers -> SQLite
                                       |
                                       v
                           Classify and summarize
                                       |
                                       v
                               Processed events
```

This is currently a prototype. Events are stored in a local SQLite database at
`backend/data/monitex.db`. Raw received events are stored in `events`, while
accepted classified events are stored in `processed_events` with a default
status of `pending_operator_review`. There is not yet a user interface or an
operator workflow for updating that status.

## Running the Backend

This project uses Python 3.14 and `uv`.

```bash
uv sync
uv run fastapi dev main.py
```

The backend starts at `http://127.0.0.1:8000`. Its health status is available at
`http://127.0.0.1:8000/health`.

On startup, the backend creates the local data directory and initializes the
SQLite schema if the database does not already exist. The database connection is
closed after the worker queue is drained during shutdown.

To use the AI classifier and summarizer, add an OpenRouter API key to `.env`:

```bash
OPEN_ROUTER_API="your-api-key"
```

Then start the backend normally:

```bash
uv run fastapi dev main.py
```

The demo still runs without an API key. In that case, it uses local fallback
rules for classification and generates a basic summary from the event fields.

## Running the Full Demo

Run these components in separate terminals:

1. Start this backend.
2. Start `stream/main.py` to generate simulated security events.
3. Start `stream/relay.py` to forward those events to the backend.

See `../stream/README.md` for the stream commands.

## Current Limits

- The queue exists only in memory and is lost when the backend stops.
- The SQLite database is local to the backend instance and is not configured for
  multi-instance deployments.
- False-positive events are stored as raw events but are not yet inserted into
  `processed_events`.
- There is no authentication on the webhook.
- The demo does not yet provide a dashboard or operator review workflow.
