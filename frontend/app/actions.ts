"use server";

import type { ActionResult } from "@/lib/action-result";
import type { EventStatus, EventStatusUpdate, ProcessedEvent } from "./types";

type GetProcessedEventsOptions = {
  page?: number;
  dateFrom?: string;
  dateTo?: string;
  status?: EventStatus;
};

const requestBackend = async <T>(
  url: string,
  init?: RequestInit,
): Promise<ActionResult<T>> => {
  try {
    const response = await fetch(url, { ...init, cache: "no-store" });

    if (!response.ok) {
      return {
        data: null,
        error: `Backend request failed with status ${response.status}`,
      };
    }

    return { data: (await response.json()) as T, error: null };
  } catch {
    return { data: null, error: "Unable to connect to the backend" };
  }
};

export async function getProcessedEvents({
  page = 1,
  dateFrom,
  dateTo,
  status,
}: GetProcessedEventsOptions = {}): Promise<ActionResult<ProcessedEvent[]>> {
  if (!Number.isInteger(page) || page < 1) {
    return { data: null, error: "Page must be a positive integer" };
  }

  const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
  const parameters = new URLSearchParams({ page: String(page) });

  if (dateFrom) parameters.set("date_from", dateFrom);
  if (dateTo) parameters.set("date_to", dateTo);
  if (status) parameters.set("status", status);

  return requestBackend<ProcessedEvent[]>(
    `${backendUrl}/api/get-processed-events?${parameters}`,
  );
}

export async function getSiteProcessedEvents(
  siteId: string,
  page = 1,
): Promise<ActionResult<ProcessedEvent[]>> {
  if (!siteId) {
    return { data: null, error: "Site ID is required" };
  }
  if (!Number.isInteger(page) || page < 1) {
    return { data: null, error: "Page must be a positive integer" };
  }

  const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
  return requestBackend<ProcessedEvent[]>(
    `${backendUrl}/api/sites/${encodeURIComponent(siteId)}/processed-events?page=${page}`,
  );
}

export async function updateEventStatus(
  eventId: string,
  status: EventStatusUpdate,
): Promise<ActionResult<{ id: string; status: EventStatusUpdate }>> {
  if (!eventId) {
    return { data: null, error: "Event ID is required" };
  }
  if (status !== "acknowledged" && status !== "resolved") {
    return { data: null, error: "Invalid event status" };
  }

  const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
  return requestBackend<{ id: string; status: EventStatusUpdate }>(
    `${backendUrl}/api/processed-events/${encodeURIComponent(eventId)}/status`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    },
  );
}

export async function bulkUpdateEventStatus(
  eventIds: string[],
  status: EventStatusUpdate,
): Promise<ActionResult<{ ids: string[]; status: EventStatusUpdate }>> {
  if (eventIds.length === 0) {
    return { data: null, error: "At least one event ID is required" };
  }
  if (status !== "acknowledged" && status !== "resolved") {
    return { data: null, error: "Invalid event status" };
  }

  const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
  return requestBackend<{
    ids: string[];
    status: EventStatusUpdate;
  }>(`${backendUrl}/api/processed-events/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_ids: eventIds, status }),
  });
}
