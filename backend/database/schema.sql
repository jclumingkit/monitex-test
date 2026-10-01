PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY NOT NULL UNIQUE,
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
    event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'warning', 'info')),
    false_positive_probability REAL NOT NULL
        CHECK (false_positive_probability >= 0.0 AND false_positive_probability <= 1.0),
    summary TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_operator_review',
    date_created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    date_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS event_correlations (
    processed_event_id TEXT PRIMARY KEY NOT NULL
        REFERENCES processed_events(id) ON DELETE CASCADE,
    base_severity TEXT NOT NULL CHECK (base_severity IN ('critical', 'warning', 'info')),
    final_severity TEXT NOT NULL CHECK (final_severity IN ('critical', 'warning', 'info')),
    reason TEXT,
    date_created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_processed_events_queue_order
ON processed_events (
    CASE status
        WHEN 'pending_operator_review' THEN 1
        WHEN 'acknowledged' THEN 2
        WHEN 'resolved' THEN 3
        ELSE 4
    END,
    CASE severity
        WHEN 'critical' THEN 1
        WHEN 'warning' THEN 2
        WHEN 'info' THEN 3
        ELSE 4
    END,
    date_created DESC,
    id ASC
);

CREATE INDEX IF NOT EXISTS idx_processed_events_status_severity
ON processed_events (
    status,
    CASE severity
        WHEN 'critical' THEN 1
        WHEN 'warning' THEN 2
        WHEN 'info' THEN 3
        ELSE 4
    END,
    date_created DESC,
    id ASC
);

CREATE INDEX IF NOT EXISTS idx_processed_events_date_created
ON processed_events (date_created DESC, id ASC);

CREATE INDEX IF NOT EXISTS idx_events_site_timestamp
ON events (site_id, timestamp, event_id);


-- Add operator_action_logs once users table is available. it should log all operator actions like attempted to resolve an event
