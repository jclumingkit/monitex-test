"use client";

import {
  type InfiniteData,
  useInfiniteQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useEffect, useEffectEvent, useState } from "react";
import { getProcessedEvents } from "../actions";
import type {
  EventStatus,
  EventStatusUpdate,
  ProcessedEvent,
} from "../types";
import DetectionEventsFeed from "./DetectionEventsFeed";
import EventDetails from "./EventDetails";

type DashboardContentProps = {
  initialEvents: ProcessedEvent[];
};

type StatusFilter = "all" | EventStatus;

const PROCESSED_EVENTS_QUERY_KEY = ["processed-events"] as const;
const EVENTS_STREAM_URL = `${(
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"
).replace(/\/$/, "")}/api/events/stream`;
const getProcessedEventsQueryKey = (
  status: EventStatus | undefined,
  dateFrom: string | undefined,
) => [...PROCESSED_EVENTS_QUERY_KEY, { status, dateFrom }] as const;

const statusPriority: Record<EventStatus, number> = {
  pending_operator_review: 1,
  acknowledged: 2,
  resolved: 3,
};

const severityPriority: Record<ProcessedEvent["severity"], number> = {
  critical: 1,
  warning: 2,
  info: 3,
};

const compareEvents = (left: ProcessedEvent, right: ProcessedEvent) =>
  statusPriority[left.status] - statusPriority[right.status] ||
  severityPriority[left.severity] - severityPriority[right.severity] ||
  new Date(right.date_created).getTime() -
    new Date(left.date_created).getTime() ||
  left.id.localeCompare(right.id);

export default function DashboardContent({
  initialEvents,
}: DashboardContentProps) {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [dateRange, setDateRange] = useState("all");
  const [dateFrom, setDateFrom] = useState<string>();
  const [selectedEventId, setSelectedEventId] = useState<string | undefined>(
    initialEvents[0]?.id,
  );
  const [selectedEventSnapshot, setSelectedEventSnapshot] = useState<
    ProcessedEvent | undefined
  >(initialEvents[0]);
  const [newEventIds, setNewEventIds] = useState<Set<string>>(() => new Set());
  const queryStatus = statusFilter === "all" ? undefined : statusFilter;
  const queryKey = getProcessedEventsQueryKey(queryStatus, dateFrom);
  const isInitialQuery = !queryStatus && !dateFrom;

  const eventsQuery = useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam }) =>
      getProcessedEvents({
        page: pageParam,
        status: queryStatus,
        dateFrom,
      }),
    initialPageParam: 1,
    getNextPageParam: (lastPage, allPages) =>
      lastPage.length > 0 ? allPages.length + 1 : undefined,
    initialData: isInitialQuery
      ? { pages: [initialEvents], pageParams: [1] }
      : undefined,
    staleTime: 10_000,
  });

  const events = [
    ...new Map(
      (eventsQuery.data?.pages.flat() ?? []).map((event) => [event.id, event]),
    ).values(),
  ].sort(compareEvents);

  const handleAlarm = useEffectEvent((message: MessageEvent) => {
    const event: ProcessedEvent = JSON.parse(message.data);
    const matchesStatus = !queryStatus || event.status === queryStatus;
    const matchesDate =
      !dateFrom || new Date(event.date_created).getTime() >= Date.parse(dateFrom);
    let inserted = false;

    if (!matchesStatus || !matchesDate) return;

    queryClient.setQueryData<InfiniteData<ProcessedEvent[]>>(
      getProcessedEventsQueryKey(queryStatus, dateFrom),
      (current) => {
        const existingEvent = current?.pages.some((page) =>
          page.some((item) => item.id === event.id),
        );

        if (current && existingEvent) {
          return {
            ...current,
            pages: current.pages.map((page) =>
              page.map((item) => (item.id === event.id ? event : item)),
            ),
          };
        }

        if (!current) {
          inserted = true;
          return { pages: [[event]], pageParams: [1] };
        }

        const [firstPage = [], ...remainingPages] = current.pages;
        inserted = true;
        return {
          ...current,
          pages: [[event, ...firstPage], ...remainingPages],
        };
      },
    );

    setSelectedEventSnapshot((current) =>
      current?.id === event.id ? event : current,
    );

    if (!inserted) return;

    setNewEventIds((current) => {
      const next = new Set(current);
      next.add(event.id);
      return next;
    });
    setSelectedEventId((current) => current ?? event.id);
  });

  useEffect(() => {
    const source = new EventSource(EVENTS_STREAM_URL);

    source.addEventListener("alarm", handleAlarm);

    source.onerror = (error) => {
      console.error("SSE error", error);
    };

    return () => source.close();
  }, []);

  const selectedIndex = events.findIndex(
    (event) => event.id === selectedEventId,
  );
  const selectedEvent =
    events[selectedIndex] ??
    (selectedEventSnapshot?.id === selectedEventId
      ? selectedEventSnapshot
      : undefined);

  const selectEvent = (eventId: string) => {
    setSelectedEventId(eventId);
    setSelectedEventSnapshot(events.find((event) => event.id === eventId));
    setNewEventIds((current) => {
      if (!current.has(eventId)) return current;

      const next = new Set(current);
      next.delete(eventId);
      return next;
    });
  };

  const selectByIndex = (index: number) => {
    const event = events[index];

    if (event) selectEvent(event.id);
  };

  const changeDateRange = (value: string) => {
    setDateRange(value);

    if (value === "all") {
      setDateFrom(undefined);
      return;
    }

    const days = value === "24h" ? 1 : Number(value);
    setDateFrom(new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString());
  };

  const handleStatusChanges = (
    eventIds: string[],
    status: EventStatusUpdate,
  ) => {
    const updatedIds = new Set(eventIds);
    const dateUpdated = new Date().toISOString();

    queryClient.setQueriesData<InfiniteData<ProcessedEvent[]>>(
      { queryKey: PROCESSED_EVENTS_QUERY_KEY },
      (current) =>
        current
          ? {
              ...current,
              pages: current.pages.map((page) =>
                page.map((event) =>
                  updatedIds.has(event.id)
                    ? { ...event, status, date_updated: dateUpdated }
                    : event,
                ),
              ),
            }
          : current,
    );
    setSelectedEventSnapshot((current) =>
      current && updatedIds.has(current.id)
        ? { ...current, status, date_updated: dateUpdated }
        : current,
    );
    void queryClient.invalidateQueries({
      queryKey: PROCESSED_EVENTS_QUERY_KEY,
    });
  };

  return (
    <div className="grid min-w-0 gap-4 p-4 xl:h-[calc(100svh-4rem)] xl:grid-cols-[minmax(0,1fr)_24rem]">
      <DetectionEventsFeed
        events={events}
        newEventIds={newEventIds}
        selectedEventId={selectedEventId}
        statusFilter={statusFilter}
        dateRange={dateRange}
        earliestDate={dateFrom ? Date.parse(dateFrom) : undefined}
        hasNextPage={eventsQuery.hasNextPage}
        isLoading={eventsQuery.isPending}
        isFetchingNextPage={eventsQuery.isFetchingNextPage}
        loadError={eventsQuery.isError}
        loadMoreError={eventsQuery.isFetchNextPageError}
        onSelectEvent={selectEvent}
        onStatusFilterChange={setStatusFilter}
        onDateRangeChange={changeDateRange}
        onLoadMore={() => void eventsQuery.fetchNextPage()}
        onRetry={() => void eventsQuery.refetch()}
        onBulkStatusChange={handleStatusChanges}
      />
      <aside className="min-w-0">
        <EventDetails
          event={selectedEvent}
          currentIndex={selectedIndex}
          eventCount={events.length}
          onPrevious={() => selectByIndex(selectedIndex - 1)}
          onNext={() => selectByIndex(selectedIndex + 1)}
          onClose={() => setSelectedEventId(undefined)}
          onStatusChange={(eventId, status) =>
            handleStatusChanges([eventId], status)
          }
        />
      </aside>
    </div>
  );
}
