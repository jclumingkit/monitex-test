import { Badge } from "@/components/ui/badge";
import { cn, humanize } from "@/lib/utils";
import type { ProcessedEvent } from "../types";

const severityClasses: Record<ProcessedEvent["severity"], string> = {
  critical: "bg-red-500/15 text-red-500 dark:text-red-400",
  warning: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  info: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
};

const statusClasses: Record<ProcessedEvent["status"], string> = {
  pending_operator_review: "bg-amber-500/15 text-amber-500 dark:text-amber-400",
  acknowledged: "bg-blue-500/15 text-blue-600 dark:text-blue-400",
  resolved: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
};

export const SeverityBadge = ({
  severity,
}: {
  severity: ProcessedEvent["severity"];
}) => (
  <Badge
    className={cn(
      "h-7 rounded-md px-2.5 uppercase",
      severityClasses[severity],
    )}
  >
    <span className="size-2 rounded-full bg-current" />
    {severity}
  </Badge>
);

export const StatusBadge = ({ status }: { status: ProcessedEvent["status"] }) => (
  <Badge
    className={cn(
      "h-7 rounded-md px-2.5",
      statusClasses[status] ?? "bg-muted text-muted-foreground",
    )}
  >
    {humanize(status)}
  </Badge>
);
