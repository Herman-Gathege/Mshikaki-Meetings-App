/** Empty, loading and error states. Part of the component, not an afterthought. */

import type { ReactNode } from "react";

import { Button, Card, Spinner } from "@/components/ui/kit";
import { ApiError } from "@/api/client";

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
  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : "Something went wrong.";

  return (
    <Card className="border-red-200 bg-red-50">
      <p className="font-medium text-red-800">That did not work</p>
      <p className="mt-1 text-sm text-red-700">{message}</p>
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
}: {
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  return (
    <Card className="border-dashed bg-ink-50 text-center">
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
