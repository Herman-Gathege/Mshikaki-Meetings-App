/** Empty, loading and error states. Part of the component, not an afterthought. */

import type { ReactNode } from "react";

import { Button, Card, Spinner } from "@/components/ui/kit";
import { ApiError } from "@/api/client";

/**
 * What to say instead of a server code.

 * The plan's rule: no technical error text in front of a user. The code stays in
 * the logs and in the reference line, never as the message.
 */
const HUMAN_MESSAGES: Record<string, string> = {
  "auth.required": "Please sign in again.",
  "auth.invalid_credentials": "That email and password combination is not right.",
  "request.invalid": "Hmm, that didn't save. Check the highlighted information and try again.",
  "request.untrusted": "That request looked unsafe, so Mshikaki stopped it. Try again.",
  "permission_denied": "You don't have permission to do that.",
  "not_found": "We couldn't find that. It may have been removed.",
  "conflict": "Somebody else changed this first. Reload and try again.",
  "internal_error": "Something went wrong on our side. Please try again.",
  "join.email_domain": "Please use your work email address.",
  "minutes.not_closed": "Close the meeting first and Mshikaki will write the minutes.",
  "session.already_active": "Another meeting is already running. Close it first.",
  "task.owner_required": "Give the task an owner before moving it on.",
  "blocker.owner_required": "Give the task an owner before blocking it.",
  "idea.not_convertible": "That idea has already been dealt with.",
};

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-10">
      <Spinner label={label} />
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  const apiError = error instanceof ApiError ? error : null;
  const message =
    (apiError && (HUMAN_MESSAGES[apiError.code] ?? apiError.message)) ||
    (error instanceof Error ? error.message : "Something went wrong.");
  const reference =
    apiError && apiError.status >= 500
      ? String(apiError.details?.request_id ?? "")
      : "";

  return (
    <Card className="border-red-200 bg-red-50">
      <p className="font-medium text-red-800">That did not work</p>
      <p className="mt-1 text-sm text-red-700">{message}</p>
      {reference ? (
        <p className="mt-1 text-xs text-red-600">
          Reference {reference}. Quote it if you report this.
        </p>
      ) : null}
      {onRetry ? (
        <Button variant="outline" size="sm" className="mt-3" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </Card>
  );
}

export function EmptyState({
  title,
  body,
  action,
  mark = false,
}: {
  title: string;
  body?: string;
  action?: ReactNode;
  /** The first-run screens show the skewer; the others stay plain. */
  mark?: boolean;
}) {
  return (
    <Card className="border-dashed bg-ink-50 text-center">
      {mark ? (
        <img src="/mshikaki-mark.png" alt="" aria-hidden className="mx-auto mb-3 size-24" />
      ) : null}
      <p className="font-medium">{title}</p>
      {body ? <p className="mt-1 text-sm text-ink-600">{body}</p> : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </Card>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold text-balance">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-ink-600">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </header>
  );
}
