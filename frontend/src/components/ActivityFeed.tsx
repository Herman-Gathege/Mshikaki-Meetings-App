/** The one renderer for activity, used by every screen. */

import { Link } from "react-router-dom";

import type { ActivityItem } from "@/api/types";
import { formatRelative } from "@/lib/dates";
import { Card } from "@/components/ui/kit";

function targetLink(item: ActivityItem): string | null {
  if (!item.target_id) return null;
  switch (item.target_type) {
    case "task":
      return `/tasks/${item.target_id}`;
    case "idea":
      return `/ideas/${item.target_id}`;
    case "decision":
      return `/decisions/${item.target_id}`;
    case "session":
      return `/sessions/${item.target_id}`;
    case "project":
      return `/projects/${item.target_id}`;
    default:
      return null;
  }
}

export function ActivityFeed({
  items,
  emptyLabel = "Nothing has happened yet.",
}: {
  items: ActivityItem[];
  emptyLabel?: string;
}) {
  if (items.length === 0) {
    return <p className="py-6 text-center text-sm text-ink-600">{emptyLabel}</p>;
  }

  return (
    <ol className="space-y-3">
      {items.map((item) => {
        const href = targetLink(item);
        return (
          <li key={item.id} className="flex gap-3">
            <span
              aria-hidden
              className="mt-1.5 size-2 shrink-0 rounded-full bg-ember-500/60"
            />
            <div className="min-w-0">
              <p className="text-sm text-ink-900">
                <span className="font-medium">{item.actor_name}</span>{" "}
                {href ? (
                  <Link className="hover:underline" to={href}>
                    {item.description}
                  </Link>
                ) : (
                  item.description
                )}
              </p>
              <p className="text-xs text-ink-400">{formatRelative(item.occurred_at)}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export function ActivityCard({
  items,
  title = "Activity",
  emptyLabel,
}: {
  items: ActivityItem[];
  title?: string;
  emptyLabel?: string;
}) {
  return (
    <Card>
      <h2 className="mb-3 text-sm font-semibold text-ink-800">{title}</h2>
      <ActivityFeed items={items} emptyLabel={emptyLabel} />
    </Card>
  );
}
