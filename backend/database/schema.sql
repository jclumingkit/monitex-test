PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    site_id TEXT NOT NULL,
    zone TEXT NOT NULL,
    type TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    timestamp TEXT NOT NULL,
    timezone TEXT,
    snapshot_url TEXT,
    metadata TEXT NOT NULL,
    date_created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS processed_events (
    id TEXT PRIMARY KEY NOT NULL,
    event_id TEXT NOT NULL REFERENCES events(event_id),
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'warning', 'info')),
    false_positive_probability REAL NOT NULL
        CHECK (false_positive_probability >= 0.0 AND false_positive_probability <= 1.0),
    summary TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_operator_review',
    date_created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    date_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- Add operator_action_logs once users table is available. it should log all operator actions like attempted to resolve an event