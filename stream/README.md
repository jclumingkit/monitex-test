This is a mock `streaming` service that generates and relays detection events.

### main.py

Handles the generation and running the websocket

### relay.py

Connects to `main.py` websocket and relays the message to `/backend/api/webhook`
