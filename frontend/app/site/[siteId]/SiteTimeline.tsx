"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { unwrapActionResult } from "@/lib/action-result";
import { cn, formatDate, humanize } from "@/lib/utils";
import { useInfiniteQuery } from "@tanstack/react-query";
import { ArrowLeft, LoaderCircle, MapPin, Radio, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useEffect, useEffectEvent, useRef } from "react";
import { getSiteProcessedEvents } from "../../actions";
import { SeverityBadge, StatusBadge } from "../../components/EventBadges";
import type { ProcessedEvent } from "../../types";

type SiteTimelineProps = {
  siteId: string;
  initialEvents: ProcessedEvent[];
  initialLoadError: boolean;
};

const severityIndicatorClasses: Record<ProcessedEvent["severity"], string> = {
  critical: "border-red-500 bg-red-500 shadow-red-500/30",
  warning: "border-amber-500 bg-amber-500 shadow-amber-500/30",
  info: "border-sky-500 bg-sky-500 shadow-sky-500/30",
};

const compareByTimestamp = (left: ProcessedEvent, right: ProcessedEvent) =>
  new Date(left.timestamp).getTime() - new Date(right.timestamp).getTime() ||
  left.id.localeCompare(right.id);

export default function SiteTimeline({
  siteId,
  initialEvents,
  initialLoadError,
}: SiteTimelineProps) {
  const loadMoreRef = useRef<HTMLDivElement>(null);
  const eventsQuery = useInfiniteQuery({
    queryKey: ["site-events", siteId],
    queryFn: async ({ pageParam }) =>
      unwrapActionResult(await getSiteProcessedEvents(siteId, pageParam)),
    initialPageParam: 1,
    initialData: initialLoadError
      ? undefined
      : { pages: [initialEvents], pageParams: [1] },
    getNextPageParam: (lastPage, allPages) =>
      lastPage.length > 0 ? allPages.length + 1 : undefined,
    staleTime: 10_000,
  });
  const events = [
    ...new Map(
      (eventsQuery.data?.pages.flat() ?? []).map((event) => [event.id, event]),
    ).values(),
  ].sort(compareByTimestamp);

  const loadNextPage = useEffectEvent(() => {
    if (eventsQuery.hasNextPage && !eventsQuery.isFetchingNextPage) {
      void eventsQuery.fetchNextPage();
    }
  });

  useEffect(() => {
    const target = loadMoreRef.current;
    if (!target) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) loadNextPage();
      },
      { rootMargin: "300px 0px" },
    );

    observer.observe(target);
    return () => observer.disconnect();
  }, [events.length]);

  return (
    <main className="min-h-svh bg-[radial-gradient(circle_at_top_left,var(--color-muted),transparent_38%)]">
      <div className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 lg:py-12">
        <Button
          variant="ghost"
          className="mb-8 -ml-3"
          nativeButton={false}
          render={<Link href="/dashboard" />}
        >
          <ArrowLeft />
          Back to dashboard
        </Button>

        <header className="mb-10 border-b pb-8">
          <div className="mb-3 flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <Radio className="size-4 text-emerald-500" />
            Site activity timeline
          </div>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            {humanize(siteId)}
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
            Processed detection events ordered from the site&apos;s earliest signal
            to its latest activity.
          </p>
        </header>

        {eventsQuery.isPending ? (
          <Card className="border-dashed shadow-none">
            <CardContent className="flex min-h-56 items-center justify-center gap-2 text-sm text-muted-foreground">
              <LoaderCircle className="size-4 animate-spin" />
              Loading site events...
            </CardContent>
          </Card>
        ) : events.length === 0 && !eventsQuery.isError ? (
          <Card className="border-dashed shadow-none">
            <CardContent className="flex min-h-56 flex-col items-center justify-center gap-3 text-center">
              <MapPin className="size-8 text-muted-foreground" />
              <div>
                <p className="font-medium">No processed events found</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  This site does not have any accepted events yet.
                </p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <ol className="relative" aria-label={`Events for ${siteId}`}>
            {events.map((event) => (
              <li
                key={event.id}
                className="group relative grid gap-2 pb-9 pl-10 last:pb-0 md:grid-cols-[10rem_minmax(0,1fr)] md:gap-8 md:pl-0"
              >
                <div className="absolute top-3 bottom-0 left-3 w-px bg-border group-last:hidden md:left-[11.25rem]" />
                <div className="absolute top-2 left-[0.55rem] z-10 md:left-[10.8rem]">
                  <span
                    className={cn(
                      "block size-3 rounded-full border-2 shadow-[0_0_0_5px_var(--color-background)]",
                      severityIndicatorClasses[event.severity],
                    )}
                  />
                </div>

                <time
                  dateTime={event.timestamp}
                  className="text-xs font-medium text-muted-foreground md:pt-1.5 md:text-right"
                >
                  {formatDate(event.timestamp)}
                </time>

                <Card className="gap-3 py-4 shadow-none transition-colors hover:border-foreground/20">
                  <CardContent className="space-y-3 px-4 sm:px-5">
                    <div className="flex flex-wrap items-center gap-2">
                      <SeverityBadge severity={event.severity} />
                      <StatusBadge status={event.status} />
                    </div>
                    <div>
                      <h2 className="font-medium leading-6">{event.summary}</h2>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {humanize(event.type)} in {humanize(event.zone)}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground">
                      <span>Source: {humanize(event.source)}</span>
                      <span>
                        Confidence: {Math.round(event.confidence * 100)}%
                      </span>
                      <span className="font-mono">{event.event_id}</span>
                    </div>
                  </CardContent>
                </Card>
              </li>
            ))}
          </ol>
        )}

        {eventsQuery.isError && (
          <div className="mt-8 flex flex-col items-center gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-center">
            <p className="text-sm text-destructive">
              Unable to load more events for this site.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void eventsQuery.refetch()}
            >
              <RefreshCw />
              Retry
            </Button>
          </div>
        )}

        {eventsQuery.hasNextPage && !eventsQuery.isError && (
          <div
            ref={loadMoreRef}
            className="flex min-h-24 items-center justify-center text-sm text-muted-foreground"
            aria-live="polite"
          >
            {eventsQuery.isFetchingNextPage
              ? "Loading newer events..."
              : "Scroll to load newer events"}
          </div>
        )}

        {!eventsQuery.hasNextPage && events.length > 0 && (
          <p className="mt-10 text-center text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Latest recorded event
          </p>
        )}
      </div>
    </main>
  );
}
