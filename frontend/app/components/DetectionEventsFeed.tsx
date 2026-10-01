"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDateOnly, formatTime, humanize } from "@/lib/utils";
import { useMutation } from "@tanstack/react-query";
import { unwrapActionResult } from "@/lib/action-result";
import { CheckCheck, ChevronRight, Filter, LoaderCircle } from "lucide-react";
import { useEffect, useEffectEvent, useRef, useState } from "react";
import { bulkUpdateEventStatus } from "../actions";
import type {
  EventStatus,
  EventStatusUpdate,
  ProcessedEvent,
} from "../types";
import { SeverityBadge, StatusBadge } from "./EventBadges";

type DetectionEventsFeedProps = {
  events: ProcessedEvent[];
  newEventIds: ReadonlySet<string>;
  selectedEventId?: string;
  statusFilter: "all" | EventStatus;
  dateRange: string;
  earliestDate?: number;
  hasNextPage: boolean;
  isLoading: boolean;
  isFetchingNextPage: boolean;
  loadError: boolean;
  loadMoreError: boolean;
  onSelectEvent: (eventId: string) => void;
  onStatusFilterChange: (status: "all" | EventStatus) => void;
  onDateRangeChange: (dateRange: string) => void;
  onLoadMore: () => void;
  onRetry: () => void;
  onBulkStatusChange: (eventIds: string[], status: EventStatusUpdate) => void;
};

type FilterOption = {
  label: string;
  value: string;
};

type FilterSubmenuProps = {
  label: string;
  value: string;
  options: FilterOption[];
  onChange: (value: string) => void;
};

const EVENT_TYPES = [
  "motion_detected",
  "perimeter_breach",
  "door_forced",
  "glass_break",
  "smoke_detected",
  "fire_alarm",
  "object_detected",
  "person_detected",
  "loitering",
  "camera_offline",
  "panic_button",
];

const toFilterOptions = (values: string[]): FilterOption[] =>
  values.map((value) => ({ value, label: humanize(value) }));

const SEVERITY_OPTIONS = toFilterOptions(["critical", "warning", "info"]);
const STATUS_OPTIONS = toFilterOptions([
  "pending_operator_review",
  "acknowledged",
  "resolved",
]);
const TYPE_OPTIONS = toFilterOptions(EVENT_TYPES);
const SOURCE_OPTIONS = toFilterOptions(["camera", "sensor"]);
const DATE_OPTIONS: FilterOption[] = [
  { value: "24h", label: "Last 24 Hours" },
  { value: "7", label: "Last 7 Days" },
  { value: "30", label: "Last 30 Days" },
];

const FilterSubmenu = ({
  label,
  value,
  options,
  onChange,
}: FilterSubmenuProps) => (
  <DropdownMenuSub>
    <DropdownMenuSubTrigger>{label}</DropdownMenuSubTrigger>
    <DropdownMenuSubContent className="max-h-80 overflow-y-auto">
      <DropdownMenuRadioGroup value={value} onValueChange={onChange}>
        <DropdownMenuRadioItem value="all">All {label}</DropdownMenuRadioItem>
        {options.map((option) => (
          <DropdownMenuRadioItem key={option.value} value={option.value}>
            {option.label}
          </DropdownMenuRadioItem>
        ))}
      </DropdownMenuRadioGroup>
    </DropdownMenuSubContent>
  </DropdownMenuSub>
);

export default function DetectionEventsFeed({
  events,
  newEventIds,
  selectedEventId,
  statusFilter,
  dateRange,
  earliestDate,
  hasNextPage,
  isLoading,
  isFetchingNextPage,
  loadError,
  loadMoreError,
  onSelectEvent,
  onStatusFilterChange,
  onDateRangeChange,
  onLoadMore,
  onRetry,
  onBulkStatusChange,
}: DetectionEventsFeedProps) {
  const [severity, setSeverity] = useState("all");
  const [type, setType] = useState("all");
  const [source, setSource] = useState("all");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [bulkError, setBulkError] = useState<string>();
  const loadMoreRef = useRef<HTMLTableRowElement>(null);
  const bulkStatusMutation = useMutation({
    mutationFn: ({
      eventIds,
      status,
    }: {
      eventIds: string[];
      status: EventStatusUpdate;
    }) =>
      bulkUpdateEventStatus(eventIds, status).then(unwrapActionResult),
    onSuccess: (updated) => {
      onBulkStatusChange(updated.ids, updated.status);
      setSelectedIds((current) => {
        const next = new Set(current);
        updated.ids.forEach((eventId) => next.delete(eventId));
        return next;
      });
    },
    onError: () => {
      setBulkError("Unable to update the selected events. Please try again.");
    },
  });
  const isBulkUpdating = bulkStatusMutation.isPending;

  const filteredEvents = events.filter(
    (event) =>
      (severity === "all" || event.severity === severity) &&
      (statusFilter === "all" || event.status === statusFilter) &&
      (type === "all" || event.type === type) &&
      (source === "all" || event.source === source) &&
      (!earliestDate || new Date(event.date_created).getTime() >= earliestDate),
  );
  const activeFilterCount = [
    severity,
    statusFilter,
    type,
    source,
    dateRange,
  ].filter((filter) => filter !== "all").length;
  const visibleEventIds = filteredEvents.map((event) => event.id);
  const selectedVisibleCount = visibleEventIds.filter((id) =>
    selectedIds.has(id),
  ).length;
  const allVisibleSelected =
    visibleEventIds.length > 0 &&
    selectedVisibleCount === visibleEventIds.length;
  const someVisibleSelected = selectedVisibleCount > 0 && !allVisibleSelected;

  const clearFilters = () => {
    setSeverity("all");
    onStatusFilterChange("all");
    setType("all");
    setSource("all");
    onDateRangeChange("all");
  };

  const toggleEvent = (eventId: string, checked: boolean) => {
    setSelectedIds((current) => {
      const next = new Set(current);

      if (checked) {
        next.add(eventId);
      } else {
        next.delete(eventId);
      }

      return next;
    });
  };

  const toggleVisibleEvents = (checked: boolean) => {
    setSelectedIds((current) => {
      const next = new Set(current);

      for (const eventId of visibleEventIds) {
        if (checked) {
          next.add(eventId);
        } else {
          next.delete(eventId);
        }
      }

      return next;
    });
  };

  const updateSelectedEvents = (nextStatus: EventStatusUpdate) => {
    const eventIds = [...selectedIds];

    setBulkError(undefined);
    bulkStatusMutation.mutate({
      eventIds,
      status: nextStatus,
    });
  };

  const requestMore = useEffectEvent(() => {
    if (hasNextPage && !isFetchingNextPage && !loadMoreError) onLoadMore();
  });

  useEffect(() => {
    const target = loadMoreRef.current;
    if (!target || !hasNextPage || loadMoreError) return;

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) requestMore();
    });
    observer.observe(target);

    return () => observer.disconnect();
  }, [events.length, hasNextPage, isFetchingNextPage, loadMoreError]);

  return (
    <Card className="min-h-0 gap-0 rounded-xl py-0 shadow-none">
      <div className="shrink-0 border-b p-3">
        <div className="flex flex-wrap items-center gap-4">
          <DropdownMenu>
            <DropdownMenuTrigger
              render={<Button variant="outline" className="rounded-lg" />}
            >
              <Filter />
              Filters
              {activeFilterCount > 0 && (
                <span className="rounded-full bg-primary px-1.5 text-xs text-primary-foreground">
                  {activeFilterCount}
                </span>
              )}
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="min-w-52">
              <DropdownMenuGroup>
                <DropdownMenuLabel>Filter events</DropdownMenuLabel>
                <FilterSubmenu
                  label="Severities"
                  value={severity}
                  options={SEVERITY_OPTIONS}
                  onChange={setSeverity}
                />
                <FilterSubmenu
                  label="Statuses"
                  value={statusFilter}
                  options={STATUS_OPTIONS}
                  onChange={(value) =>
                    onStatusFilterChange(value as "all" | EventStatus)
                  }
                />
                <FilterSubmenu
                  label="Types"
                  value={type}
                  options={TYPE_OPTIONS}
                  onChange={setType}
                />
                <FilterSubmenu
                  label="Sources"
                  value={source}
                  options={SOURCE_OPTIONS}
                  onChange={setSource}
                />
                <FilterSubmenu
                  label="Date range"
                  value={dateRange}
                  options={DATE_OPTIONS}
                  onChange={onDateRangeChange}
                />
              </DropdownMenuGroup>
              <DropdownMenuSeparator />
              <DropdownMenuGroup>
                <DropdownMenuItem
                  disabled={activeFilterCount === 0}
                  onClick={clearFilters}
                >
                  Clear filters
                </DropdownMenuItem>
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>

          <DropdownMenu>
            <DropdownMenuTrigger
              disabled={selectedIds.size === 0 || isBulkUpdating}
              render={<Button variant="outline" className="rounded-lg" />}
            >
              <CheckCheck />
              {isBulkUpdating
                ? "Updating..."
                : `Bulk actions (${selectedIds.size})`}
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuGroup>
                <DropdownMenuLabel>Update selected events</DropdownMenuLabel>
                <DropdownMenuItem
                  onClick={() => updateSelectedEvents("acknowledged")}
                >
                  Mark acknowledged
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => updateSelectedEvents("resolved")}
                >
                  Mark resolved
                </DropdownMenuItem>
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>

          {newEventIds.size > 0 && (
            <span
              className="ml-auto inline-flex items-center rounded-full bg-sky-100 px-2.5 py-1 text-xs font-semibold text-sky-800 dark:bg-sky-900/50 dark:text-sky-200"
              role="status"
            >
              {newEventIds.size} new
            </span>
          )}
        </div>
        {bulkError && (
          <p className="mt-2 text-sm text-destructive" role="alert">
            {bulkError}
          </p>
        )}
      </div>

      <ScrollArea className="h-128 min-h-0 xl:h-auto xl:flex-1">
        <Table className="min-w-240">
          <TableHeader className="sticky top-0 z-10 bg-card">
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-10">
                <Checkbox
                  checked={allVisibleSelected}
                  indeterminate={someVisibleSelected}
                  aria-label="Select all visible events"
                  onCheckedChange={toggleVisibleEvents}
                />
              </TableHead>
              <TableHead>Severity</TableHead>
              <TableHead>Summary</TableHead>
              <TableHead>Site ID</TableHead>
              <TableHead>Zone</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Timestamp</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredEvents.map((event) => (
              <TableRow
                key={event.id}
                tabIndex={0}
                aria-selected={event.id === selectedEventId}
                data-new={newEventIds.has(event.id) || undefined}
                className="cursor-pointer data-[new=true]:bg-sky-50 data-[new=true]:hover:bg-sky-100/80 aria-selected:bg-primary/10 aria-selected:ring-1 aria-selected:ring-inset aria-selected:ring-primary hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring dark:data-[new=true]:bg-sky-950/50 dark:data-[new=true]:hover:bg-sky-900/40"
                onClick={() => onSelectEvent(event.id)}
                onKeyDown={(keyboardEvent) => {
                  if (
                    keyboardEvent.key === "Enter" ||
                    keyboardEvent.key === " "
                  ) {
                    keyboardEvent.preventDefault();
                    onSelectEvent(event.id);
                  }
                }}
              >
                <TableCell
                  onClick={(mouseEvent) => mouseEvent.stopPropagation()}
                  onKeyDown={(keyboardEvent) => keyboardEvent.stopPropagation()}
                >
                  <Checkbox
                    checked={selectedIds.has(event.id)}
                    aria-label={`Select ${event.summary}`}
                    onCheckedChange={(checked) =>
                      toggleEvent(event.id, checked)
                    }
                  />
                </TableCell>
                <TableCell>
                  <SeverityBadge severity={event.severity} />
                </TableCell>
                <TableCell className="max-w-52 truncate font-medium">
                  {event.summary}
                </TableCell>
                <TableCell>{humanize(event.site_id)}</TableCell>
                <TableCell>{humanize(event.zone)}</TableCell>
                <TableCell>{humanize(event.type)}</TableCell>
                <TableCell>
                  <span className="flex flex-col">
                    <span className="font-medium">
                      {formatTime(event.timestamp)}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {formatDateOnly(event.timestamp)}
                    </span>
                  </span>
                </TableCell>
                <TableCell>
                  <StatusBadge status={event.status} />
                </TableCell>
                <TableCell>
                  <ChevronRight className="size-4 text-muted-foreground" />
                </TableCell>
              </TableRow>
            ))}
            {isLoading && (
              <TableRow>
                <TableCell
                  colSpan={9}
                  className="h-40 text-center text-muted-foreground"
                >
                  <LoaderCircle className="mr-2 inline size-4 animate-spin" />
                  Loading events...
                </TableCell>
              </TableRow>
            )}
            {!isLoading && loadError && events.length === 0 && (
              <TableRow>
                <TableCell colSpan={9} className="h-40 text-center">
                  <p className="text-sm text-destructive">
                    Unable to load events.
                  </p>
                  <Button
                    className="mt-3"
                    size="sm"
                    variant="outline"
                    onClick={onRetry}
                  >
                    Try again
                  </Button>
                </TableCell>
              </TableRow>
            )}
            {!isLoading && !loadError && filteredEvents.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={9}
                  className="h-40 text-center text-muted-foreground"
                >
                  No events match these filters.
                </TableCell>
              </TableRow>
            )}
            {loadMoreError && events.length > 0 && (
              <TableRow>
                <TableCell colSpan={9} className="h-20 text-center">
                  <span className="mr-3 text-sm text-destructive">
                    Unable to load more events.
                  </span>
                  <Button size="sm" variant="outline" onClick={onLoadMore}>
                    Try again
                  </Button>
                </TableCell>
              </TableRow>
            )}
            {hasNextPage && !loadMoreError && (
              <TableRow ref={loadMoreRef} className="hover:bg-transparent">
                <TableCell
                  colSpan={9}
                  className="h-16 text-center text-muted-foreground"
                >
                  {isFetchingNextPage && (
                    <>
                      <LoaderCircle className="mr-2 inline size-4 animate-spin" />
                      Loading more events...
                    </>
                  )}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </ScrollArea>
    </Card>
  );
}
