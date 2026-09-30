"use server";

import type { EventStatus, EventStatusUpdate, ProcessedEvent } from "./types";

type GetProcessedEventsOptions = {
  page?: number;
  dateFrom?: string;
  dateTo?: string;
  status?: EventStatus;
};

export async function getProcessedEvents({
  page = 1,
  dateFrom,
  dateTo,
  status,
}: GetProcessedEventsOptions = {}): Promise<ProcessedEvent[]> {
  if (!Number.isInteger(page) || page < 1) {
    throw new Error("Page must be a positive integer");
  }

  const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
  const parameters = new URLSearchParams({ page: String(page) });

  if (dateFrom) parameters.set("date_from", dateFrom);
  if (dateTo) parameters.set("date_to", dateTo);
  if (status) parameters.set("status", status);

  const response = await fetch(
    `${backendUrl}/api/get-processed-events?${parameters}`,
    { cache: "no-store" },
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch processed events: ${response.status}`);
  }

  return response.json() as Promise<ProcessedEvent[]>;
}

export async function updateEventStatus(
  eventId: string,
  status: EventStatusUpdate,
): Promise<{ id: string; status: EventStatusUpdate }> {
  if (!eventId) {
    throw new Error("Event ID is required");
  }
  if (status !== "acknowledged" && status !== "resolved") {
    throw new Error("Invalid event status");
  }

  const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
  const response = await fetch(
    `${backendUrl}/api/processed-events/${encodeURIComponent(eventId)}/status`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(`Failed to update event status: ${response.status}`);
  }

  return response.json() as Promise<{ id: string; status: EventStatusUpdate }>;
}

export async function bulkUpdateEventStatus(
  eventIds: string[],
  status: EventStatusUpdate,
): Promise<{ ids: string[]; status: EventStatusUpdate }> {
  if (eventIds.length === 0) {
    throw new Error("At least one event ID is required");
  }
  if (status !== "acknowledged" && status !== "resolved") {
    throw new Error("Invalid event status");
  }

  const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
  const response = await fetch(`${backendUrl}/api/processed-events/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_ids: eventIds, status }),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to update event statuses: ${response.status}`);
  }

  return response.json() as Promise<{
    ids: string[];
    status: EventStatusUpdate;
  }>;
}
