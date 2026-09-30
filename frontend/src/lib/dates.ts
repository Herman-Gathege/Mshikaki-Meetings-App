/** Dates in one place, so every screen agrees. */

const TIME_ZONE = "Africa/Nairobi";

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: TIME_ZONE,
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatDay(value: string | null | undefined): string {
  if (!value) return "";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: TIME_ZONE,
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export function formatRelative(value: string | null | undefined): string {
  if (!value) return "";
  const diffMinutes = Math.round((new Date(value).getTime() - Date.now()) / 60000);
  const abs = Math.abs(diffMinutes);
  if (abs < 1) return "just now";
  if (abs < 60) return diffMinutes < 0 ? `${abs}m ago` : `in ${abs}m`;
  const hours = Math.round(abs / 60);
  if (hours < 24) return diffMinutes < 0 ? `${hours}h ago` : `in ${hours}h`;
  const days = Math.round(hours / 24);
  if (days < 30) return diffMinutes < 0 ? `${days}d ago` : `in ${days}d`;
  return formatDay(value);
}

export function isOverdue(dueDate: string | null, status: string): boolean {
  if (!dueDate || status === "done" || status === "cancelled") return false;
  return dueDate < new Date().toISOString().slice(0, 10);
}
