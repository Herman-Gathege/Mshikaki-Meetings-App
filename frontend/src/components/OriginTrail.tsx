/**
 * "Why does this exist?" - the traceability walk, in both directions.

 * Task -> Decision -> Idea -> Session, with a graceful state when one of the
 * origins has been deleted. The links are permanent; the trail must never look
 * broken.
 */

import { Link } from "react-router-dom";

import { Card } from "@/components/ui/kit";

type Origin = {
  session_id?: string | null;
  idea_id?: string | null;
  decision_id?: string | null;
};

export function OriginTrail({
  origin,
  labels = {},
}: {
  origin: Origin | undefined;
  labels?: { idea?: string; decision?: string; session?: string };
}) {
  if (!origin) return null;
  const entries = [
    { key: "decision", id: origin.decision_id, label: labels.decision ?? "Decision" },
    { key: "idea", id: origin.idea_id, label: labels.idea ?? "Idea" },
    { key: "session", id: origin.session_id, label: labels.session ?? "Session" },
  ].filter((entry) => Boolean(entry.id));

  if (entries.length === 0) {
    return (
      <Card className="bg-ink-50">
        <p className="text-sm text-ink-600">
          This was not born in a meeting. It was created directly.
        </p>
      </Card>
    );
  }

  return (
    <Card>
      <h2 className="mb-3 text-sm font-semibold text-ink-800">Why does this exist?</h2>
      <ol className="space-y-2">
        {entries.map((entry, index) => (
          <li key={entry.key} className="flex items-center gap-2 text-sm">
            <span className="text-ink-600">{index + 1}.</span>
            <Link
              className="font-medium text-ember-700 hover:underline"
              to={`/${entry.key === "session" ? "sessions" : `${entry.key}s`}/${entry.id}`}
            >
              {entry.label}
            </Link>
          </li>
        ))}
      </ol>
      <p className="mt-3 text-xs text-ink-600">
        The chain is kept even if something along it is deleted.
      </p>
    </Card>
  );
}
