"use client";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { formatDate, humanize } from "@/lib/utils";
import { useMutation } from "@tanstack/react-query";
import {
  Check,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  ImageOff,
  X,
} from "lucide-react";
import Image, { type ImageLoader } from "next/image";
import { useState } from "react";
import { updateEventStatus } from "../actions";
import type { EventStatusUpdate, ProcessedEvent } from "../types";
import { SeverityBadge, StatusBadge } from "./EventBadges";

type EventDetailsProps = {
  event?: ProcessedEvent;
  currentIndex: number;
  eventCount: number;
  onPrevious: () => void;
  onNext: () => void;
  onClose: () => void;
  onStatusChange: (eventId: string, status: EventStatusUpdate) => void;
};

const passthroughImageLoader: ImageLoader = ({ src }) => src;
const BACKEND_URL = (
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

const resolveSnapshotUrl = (snapshotUrl: string | null) => {
  if (!snapshotUrl) return undefined;
  if (snapshotUrl.startsWith("http://") || snapshotUrl.startsWith("https://")) {
    return snapshotUrl;
  }
  if (snapshotUrl.startsWith("/")) return `${BACKEND_URL}${snapshotUrl}`;

  return undefined;
};

const EventSnapshot = ({ event }: { event: ProcessedEvent }) => {
  const [failed, setFailed] = useState(false);
  const snapshotUrl = resolveSnapshotUrl(event.snapshot_url);
  const showPlaceholder = !snapshotUrl || failed;
  const imageSource = !showPlaceholder
    ? snapshotUrl
    : "/snapshot-placeholder.svg";

  return (
    <div className="relative aspect-video overflow-hidden rounded-lg border bg-muted">
      <Image
        key={imageSource}
        src={imageSource}
        alt={
          showPlaceholder
            ? "No event snapshot available"
            : `Snapshot for ${event.summary}`
        }
        fill
        sizes="(min-width: 1280px) 24rem, 100vw"
        className="object-cover"
        loader={showPlaceholder ? undefined : passthroughImageLoader}
        unoptimized={!showPlaceholder}
        onError={() => setFailed(true)}
        loading="eager"
      />
      {showPlaceholder && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-muted-foreground">
          <ImageOff className="size-8" />
          <span className="text-xs font-medium">Snapshot unavailable</span>
        </div>
      )}
    </div>
  );
};

const DetailRow = ({ label, value }: { label: string; value: string }) => (
  <div className="grid grid-cols-[7rem_minmax(0,1fr)] gap-3 text-sm">
    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
      {label}
    </dt>
    <dd className="min-w-0 wrap-break-word">{value}</dd>
  </div>
);

export default function EventDetails({
  event,
  currentIndex,
  eventCount,
  onPrevious,
  onNext,
  onClose,
  onStatusChange,
}: EventDetailsProps) {
  const snapshotUrl = resolveSnapshotUrl(event?.snapshot_url ?? null);
  const [updateError, setUpdateError] = useState<{
    eventId: string;
    message: string;
  }>();
  const statusMutation = useMutation({
    mutationFn: ({
      eventId,
      status,
    }: {
      eventId: string;
      status: EventStatusUpdate;
    }) => updateEventStatus(eventId, status),
    onSuccess: (updatedEvent) => {
      onStatusChange(updatedEvent.id, updatedEvent.status);
    },
    onError: (_error, variables) => {
      setUpdateError({
        eventId: variables.eventId,
        message: "Unable to update the event status. Please try again.",
      });
    },
  });
  const isUpdating = statusMutation.isPending;

  if (!event) {
    return (
      <Card className="min-h-72 items-center justify-center rounded-xl text-center shadow-none">
        <ImageOff className="size-10 text-muted-foreground" />
        <div>
          <p className="font-medium">No event selected</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Select an event to view its details.
          </p>
        </div>
      </Card>
    );
  }

  const handleStatusUpdate = (status: EventStatusUpdate) => {
    setUpdateError(undefined);
    statusMutation.mutate({
      eventId: event.id,
      status,
    });
  };

  return (
    <Card className="min-h-0 gap-5 rounded-xl py-5 shadow-none xl:h-full xl:overflow-y-auto">
      <CardHeader className="gap-4 px-5">
        <div className="flex items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={event.severity} />
            <StatusBadge status={event.status} />
          </div>
          <div className="flex items-center gap-1">
            {/* <span className="mr-1 text-xs text-muted-foreground">
              {currentIndex + 1} of {eventCount}
            </span> */}
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Previous event"
              disabled={currentIndex <= 0}
              onClick={onPrevious}
            >
              <ChevronLeft />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Next event"
              disabled={currentIndex >= eventCount - 1}
              onClick={onNext}
            >
              <ChevronRight />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Close event details"
              onClick={onClose}
            >
              <X />
            </Button>
          </div>
        </div>
        <div>
          <CardTitle className="text-xl">{event.summary}</CardTitle>
          <CardDescription className="mt-1">
            Detection event recorded at {event.site_id}, {event.zone}.
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="space-y-5 px-5">
        <EventSnapshot key={event.id} event={event} />

        <dl className="space-y-3">
          <DetailRow label="ID" value={event.id} />
          <DetailRow label="Event ID" value={event.event_id} />
          <DetailRow label="Site ID" value={humanize(event.site_id)} />
          <DetailRow label="Zone" value={humanize(event.zone)} />
          <DetailRow label="Type" value={humanize(event.type)} />
          <DetailRow label="Source" value={humanize(event.source)} />
          <DetailRow
            label="Confidence"
            value={`${Math.round(event.confidence * 100)}%`}
          />
          <DetailRow label="Timestamp" value={formatDate(event.timestamp)} />
        </dl>

        {snapshotUrl && (
          <>
            <Separator />
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Snapshot URL
              </span>
              <a
                href={snapshotUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-primary underline-offset-4 hover:underline"
              >
                View image
                <ExternalLink className="size-3.5" />
              </a>
            </div>
          </>
        )}
      </CardContent>

      <CardFooter className="mt-auto grid grid-cols-2 gap-3 px-5">
        {updateError?.eventId === event.id && (
          <p className="col-span-2 text-sm text-destructive" role="alert">
            {updateError.message}
          </p>
        )}
        <Button
          className="rounded-lg bg-blue-600 text-white hover:bg-blue-600/90"
          disabled={isUpdating || event.status === "acknowledged"}
          onClick={() => handleStatusUpdate("acknowledged")}
        >
          <Check />
          Acknowledge
        </Button>
        <Button
          className="rounded-lg bg-emerald-600 text-white hover:bg-emerald-600/90"
          disabled={isUpdating || event.status === "resolved"}
          onClick={() => handleStatusUpdate("resolved")}
        >
          <Check />
          Resolve
        </Button>
      </CardFooter>
    </Card>
  );
}
