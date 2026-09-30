export type EventStatus =
  | "pending_operator_review"
  | "acknowledged"
  | "resolved";

export type EventStatusUpdate = Extract<
  EventStatus,
  "acknowledged" | "resolved"
>;

export type ProcessedEvent = {
  id: string;
  event_id: string;
  site_id: string;
  zone: string;
  type: string;
  source: string;
  confidence: number;
  timestamp: string;
  snapshot_url: string | null;
  severity: "critical" | "warning" | "info";
  summary: string;
  status: EventStatus;
  date_created: string;
  date_updated: string;
};
