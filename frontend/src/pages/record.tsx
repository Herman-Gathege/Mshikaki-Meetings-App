import { useState } from "react";
import { Link } from "react-router-dom";

import { useLeaderboard, useMetrics, useSearch, useTeamActivity } from "@/api/hooks";
import { ActivityFeed } from "@/components/ActivityFeed";
import { StatusBadge } from "@/components/badges";
import { LoadingState, PageHeader, ErrorState } from "@/components/states";
import { Button, Card, Input, Select } from "@/components/ui/kit";

export function ActivityPage() {
  const [targetType, setTargetType] = useState("");
  const activity = useTeamActivity({ target_type: targetType || undefined, limit: 100 });
  const metrics = useMetrics();

  return (
    <>
      <PageHeader title="Activity" subtitle="Who did what, and when. Written automatically." />

      <Card className="mb-4">
        <h2 className="text-sm font-semibold text-ink-800">Serious numbers (not a ranking)</h2>
        {metrics.isPending ? <LoadingState label="Loading" /> : null}
        {metrics.data ? (
          <>
            <p className="mt-2 text-xs text-ink-600">{metrics.data.note}</p>
            <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-5">
              {[
                ["Open", metrics.data.open_tasks],
                ["Blocked", metrics.data.blocked],
                ["Completed", metrics.data.completed],
                ["Overdue", metrics.data.overdue],
                ["Open blockers", metrics.data.open_blockers],
              ].map(([label, value]) => (
                <div key={String(label)} className="rounded-lg bg-ink-50 p-3">
                  <dt className="text-xs text-ink-600">{label}</dt>
                  <dd className="text-2xl font-semibold">{value}</dd>
                </div>
              ))}
            </dl>
          </>
        ) : null}
      </Card>

      <div className="mb-4 flex flex-wrap gap-2">
        <Select className="w-48" value={targetType} onChange={(event) => setTargetType(event.target.value)}>
          <option value="">Everything</option>
          {["session", "idea", "decision", "task", "project"].map((value) => (
            <option key={value} value={value}>
              {value}s
            </option>
          ))}
        </Select>
      </div>

      <Card>
        {activity.isPending ? <LoadingState /> : null}
        {activity.isError ? <ErrorState error={activity.error} /> : null}
        <ActivityFeed items={activity.data?.items ?? []} />
      </Card>
    </>
  );
}

export function SearchPage() {
  const [term, setTerm] = useState("");
  const search = useSearch(term);

  return (
    <>
      <PageHeader title="Search" subtitle="Ideas, decisions and tasks." />
      <Card className="mb-4">
        <Input
          autoFocus
          value={term}
          placeholder="What did we decide about notifications?"
          onChange={(event) => setTerm(event.target.value)}
        />
      </Card>

      {search.isPending && term.length > 1 ? <LoadingState /> : null}
      {search.data ? (
        <div className="space-y-4">
          <ResultGroup title="Ideas" items={search.data.ideas.map((idea) => ({
            id: idea.id,
            to: `/ideas/${idea.id}`,
            label: idea.title,
            meta: idea.status,
          }))} />
          <ResultGroup title="Decisions" items={search.data.decisions.map((decision) => ({
            id: decision.id,
            to: `/decisions/${decision.id}`,
            label: decision.statement,
            meta: decision.recorded_by,
          }))} />
          <ResultGroup title="Tasks" items={search.data.tasks.map((task) => ({
            id: task.id,
            to: `/tasks/${task.id}`,
            label: task.title,
            meta: task.status,
          }))} />
        </div>
      ) : null}
    </>
  );
}

function ResultGroup({
  title,
  items,
}: {
  title: string;
  items: { id: string; to: string; label: string; meta: string }[];
}) {
  if (items.length === 0) return null;
  return (
    <Card>
      <h2 className="mb-3 text-sm font-semibold text-ink-800">
        {title} ({items.length})
      </h2>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item.id} className="flex items-center justify-between gap-3">
            <Link className="text-sm hover:underline" to={item.to}>
              {item.label}
            </Link>
            <StatusBadge status={item.meta} />
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function LeaderboardPage() {
  const [scope, setScope] = useState<"season" | "all">("season");
  const leaderboard = useLeaderboard(scope);

  return (
    <>
      <PageHeader
        title="🏆 Bragging rights"
        subtitle="For fun. Not a performance measure."
        actions={
          <>
            <Button
              size="sm"
              variant={scope === "season" ? "secondary" : "outline"}
              onClick={() => setScope("season")}
            >
              Season
            </Button>
            <Button
              size="sm"
              variant={scope === "all" ? "secondary" : "outline"}
              onClick={() => setScope("all")}
            >
              All time
            </Button>
          </>
        }
      />

      <Card>
        {leaderboard.isPending ? <LoadingState /> : null}
        <ol className="space-y-2">
          {(leaderboard.data?.items ?? []).map((row, index) => (
            <li key={row.id} className="flex items-center justify-between text-sm">
              <span>
                {["🥇", "🥈", "🥉"][index] ?? `${index + 1}.`} {row.name}
              </span>
              <span className="text-ink-600">{row.points} XP</span>
            </li>
          ))}
        </ol>
        <p className="mt-4 text-xs text-ink-600">
          Capped so nobody can farm it. Opt out any time on the Team page.
        </p>
      </Card>
    </>
  );
}
