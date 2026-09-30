import { Link } from "react-router-dom";

import { useMarkAttendance, useSessionParticipants, useToday } from "@/api/hooks";
import { ActivityFeed } from "@/components/ActivityFeed";
import { StatusBadge } from "@/components/badges";
import { LoadingState, PageHeader, ErrorState, EmptyState } from "@/components/states";
import { Button, Card } from "@/components/ui/kit";
import { formatDateTime, formatRelative, isOverdue } from "@/lib/dates";

export function TodayPage() {
  const today = useToday();

  if (today.isPending) return <LoadingState label="Loading your day" />;
  if (today.isError) return <ErrorState error={today.error} onRetry={() => today.refetch()} />;
  const data = today.data;

  return (
    <>
      <PageHeader
        title="Today"
        subtitle={data.my_points.season.name + " · " + data.my_points.season.points + " XP"}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="lg:col-span-2">
          {data.session ? (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm text-ink-600">
                  {data.session.status === "active" ? "Happening now" : "Next up"}
                </p>
                <h2 className="text-lg font-semibold">{data.session.title}</h2>
                <p className="text-sm text-ink-600">
                  {formatDateTime(data.session.scheduled_at)} · <StatusBadge status={data.session.status} />
                </p>
              </div>
              <Link
                to={
                  data.session.status === "active"
                    ? `/sessions/${data.session.id}/run`
                    : `/sessions/${data.session.id}`
                }
              >
                <Button size="lg">
                  {data.session.status === "active" ? "Open Run Mode" : "Open session"}
                </Button>
              </Link>
            </div>
          ) : (
            <EmptyState
              title="No session scheduled"
              body="Create the next meeting and it will show up here for everyone."
              action={
                <Link to="/sessions">
                  <Button>Plan a session</Button>
                </Link>
              }
            />
          )}
        </Card>

        {data.session?.status === "active" ? <AttendanceCard sessionId={data.session.id} /> : null}

        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-ink-800">
              My work ({data.my_open_count})
            </h2>
            <Link className="text-sm text-ember-600 hover:underline" to="/work/mine">
              All
            </Link>
          </div>
          {data.my_tasks.length === 0 ? (
            <p className="text-sm text-ink-600">Nothing assigned to you right now.</p>
          ) : (
            <ul className="space-y-3">
              {data.my_tasks.map((task) => (
                <li key={task.id} className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <Link className="font-medium hover:underline" to={`/tasks/${task.id}`}>
                      {task.title}
                    </Link>
                    <p className="text-xs text-ink-400">
                      {task.due_date
                        ? isOverdue(task.due_date, task.status)
                          ? `Overdue · due ${task.due_date}`
                          : `Due ${task.due_date}`
                        : "No due date"}
                    </p>
                  </div>
                  <StatusBadge status={task.status} />
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <h2 className="mb-3 text-sm font-semibold text-ink-800">Blockers</h2>
          {data.blockers.length === 0 ? (
            <p className="text-sm text-ink-600">Nothing is blocked. Nice.</p>
          ) : (
            <ul className="space-y-3">
              {data.blockers.map((blocker) => (
                <li key={blocker.id}>
                  <Link className="font-medium hover:underline" to={`/tasks/${blocker.task_id}`}>
                    {blocker.task_title ?? "A task"}
                  </Link>
                  <p className="text-sm text-ink-600">{blocker.reason}</p>
                  <p className="text-xs text-ink-400">
                    raised by {blocker.raised_by} · {formatRelative(blocker.raised_at)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <h2 className="mb-3 text-sm font-semibold text-ink-800">Bragging rights</h2>
          {data.leaderboard.length === 0 ? (
            <p className="text-sm text-ink-600">Nobody has earned anything yet.</p>
          ) : (
            <ol className="space-y-2">
              {data.leaderboard.map((row, index) => (
                <li key={row.id} className="flex items-center justify-between text-sm">
                  <span>
                    {["🥇", "🥈", "🥉"][index] ?? "•"} {row.name}
                  </span>
                  <span className="text-ink-600">{row.points} XP</span>
                </li>
              ))}
            </ol>
          )}
          <Link className="mt-3 inline-block text-sm text-ember-600 hover:underline" to="/leaderboard">
            Full leaderboard
          </Link>
        </Card>

        <Card className="lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold text-ink-800">Recent activity</h2>
          <ActivityFeed items={data.activity} />
        </Card>
      </div>
    </>
  );
}

function AttendanceCard({ sessionId }: { sessionId: string }) {
  const participants = useSessionParticipants(sessionId);
  const mark = useMarkAttendance(sessionId);

  return (
    <Card className="lg:col-span-2">
      <h2 className="mb-3 text-sm font-semibold text-ink-800">Who is here</h2>
      <ul className="flex flex-wrap gap-2">
        {(participants.data?.items ?? []).map((participant) => (
          <li key={participant.id}>
            <button
              type="button"
              onClick={() =>
                void mark.mutateAsync({
                  participantId: participant.id,
                  attended: !participant.attended,
                })
              }
              className={
                "rounded-full border px-3 py-2 text-sm " +
                (participant.attended
                  ? "border-nile-500 bg-nile-500/10 font-medium"
                  : "border-ink-200 bg-white text-ink-600")
              }
            >
              {participant.attended ? "✓ " : ""}
              {participant.name}
            </button>
          </li>
        ))}
      </ul>
    </Card>
  );
}
