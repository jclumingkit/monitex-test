"use client";

import { useEffect, useState } from "react";
import type { ProcessedEvent } from "../types";

type AlarmDashboardProps = {
  initialEvents: ProcessedEvent[];
};

export default function AlarmDashboard({
  initialEvents,
}: AlarmDashboardProps) {
  const [events, setEvents] = useState<ProcessedEvent[]>(initialEvents);

  useEffect(() => {
    const source = new EventSource("http://localhost:8000/api/events/stream");

    source.addEventListener("alarm", (message) => {
      const event: ProcessedEvent = JSON.parse(message.data);

      setEvents((current) => {
        if (current.some((item) => item.event_id === event.event_id)) {
          return current;
        }

        return [event, ...current];
      });
    });

    source.onerror = (error) => {
      console.error("SSE error", error);
    };

    return () => {
      source.close();
    };
  }, []);

  return (
    <div>
      <p>Alarms</p>
      {events.map((event) => (
        <div key={event.event_id}>
          <strong>{event.severity}</strong>
          <p>{event.summary}</p>
        </div>
      ))}
    </div>
  );
}
