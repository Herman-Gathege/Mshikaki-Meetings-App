/** One status badge for every status in the product. */

import { Badge } from "@/components/ui/kit";

const TONES: Record<string, "neutral" | "ember" | "nile" | "danger" | "success"> = {
  // sessions
  planned: "neutral",
  active: "nile",
  paused: "ember",
  completed: "success",
  cancelled: "neutral",
  // ideas
  new: "ember",
  discussing: "neutral",
  accepted: "success",
  parked: "neutral",
  rejected: "danger",
  converted: "nile",
  // tasks
  backlog: "neutral",
  in_progress: "nile",
  blocked: "danger",
  done: "success",
  // priorities
  low: "neutral",
  normal: "neutral",
  high: "ember",
  urgent: "danger",
};

const LABELS: Record<string, string> = {
  in_progress: "in progress",
};

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={TONES[status] ?? "neutral"}>{LABELS[status] ?? status}</Badge>;
}
