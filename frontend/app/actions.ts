"use server";

import type { ProcessedEvent } from "./types";

export async function getProcessedEvents(): Promise<ProcessedEvent[]> {
  const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
  const response = await fetch(
    `${backendUrl}/api/get-processed-events?page=1`,
    { cache: "no-store" },
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch processed events: ${response.status}`);
  }

  return response.json() as Promise<ProcessedEvent[]>;
}
