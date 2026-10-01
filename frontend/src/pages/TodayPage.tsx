/**
 * Today answers three questions, in this order:

 *   1. What is happening?
 *   2. What do I need to do?
 *   3. What happened recently?

 * Everything else on the page is deliberately secondary. A person opening
 * Mshikaki before a meeting should know what to do without reading anything twice.
 */

import { Link } from "react-router-dom";

import { useMarkAttendance, useSessionParticipants, useSessions, useToday } from "@/api/hooks";
import { ActivityFeed } from "@/components/ActivityFeed";
import { StatusBadge } from "@/components/badges";
import { StartSessionButton } from "@/components/StartSessionButton";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/states";
import { ButtonLink, Card } from "@/components/ui/kit";
import { formatDateTime, formatRelative, isOverdue } from "@/lib/dates";

export function TodayPage() {
  const today = useToday();
  const sessions = useSessions();

  if (today.isPending) return <LoadingState label="Loading your meeting…" />;
  if (today.isError) return <ErrorState error={today.error} onRetry={() => today.refetch()} />;

  const data = today.data;
  const session = data.session;
  const lastDone = sessions.data?.items.find((item) => item.status === "completed");

  return (
    <>
      <PageHeader
        title="👋 Today's Mshikaki"
        subtitle={`${data.my_points.season.name} · ${data.my_points.season.points} XP`}
      />

      <h2 className="mb-2 text-sm font-semibold tracking-wide text-ink-600 uppercase">
        Your next session
      </h2>
      <Card className="mb-6 border-ember-500/30 p-5">
        {session ? (
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="min-w-0">
              <h3 className="text-2xl font-semibold">{session.title}</h3>
              <p className="mt-1 flex flex-wrap items-center gap-2 text-ink-600">
                {session.status === "active" ? "Happening now" : formatDateTime(session.scheduled_at)}
                <StatusBadge status={session.status} />
              </p>
              <AttendanceLine sessionId={session.id} />
            </div>
            {session.status === "active" ? (
              <ButtonLink to={`/sessions/${session.id}/run`} size="xl">
                Open Run Mode →
              </ButtonLink>
            ) : (
              <StartSessionButton sessionId={session.id} size="xl" />
            )}
          </div>
        ) : (
          <EmptyState
            title="🍢 No Mshikaki planned yet"
            body="Get the team together. A meeting needs a title, a time and an agenda."
            action={
              <ButtonLink to="/sessions" size="lg">
                Plan a session
              </ButtonLink>
            }
          />
        )}
      </Card>

      {session?.status === "active" ? <AttendanceCard sessionId={session.id} /> : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <h2 className="text-sm font-semibold tracking-wide text-ink-600 uppercase">
              🎯 Your things
            </h2>
            <Link className="text-sm text-ember-700 hover:underline" to="/work/mine">
              All {data.my_open_count}
            </Link>
          </div>
          {data.my_tasks.length === 0 ? (
            <p className="text-sm text-ink-600">
              🎯 Nothing to do yet. Enjoy the peace while it lasts.
            </p>
          ) : (
            <ul className="space-y-3">
              {data.my_tasks.slice(0, 5).map((task) => (
                <li key={task.id} className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <Link className="font-medium hover:underline" to={`/tasks/${task.id}`}>
                      {task.title}
                    </Link>
                    <p className="text-xs text-ink-600">
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
          <h2 className="mb-3 text-sm font-semibold tracking-wide text-ink-600 uppercase">
            💡 From the last session
          </h2>
          {lastDone ? (
            <div className="space-y-2">
              <Link className="font-medium hover:underline" to={`/sessions/${lastDone.id}`}>
                {lastDone.title}
              </Link>
              <p className="text-sm text-ink-600">
                {lastDone.counts.ideas} ideas · {lastDone.counts.decisions} decisions ·{" "}
                {lastDone.counts.tasks} tasks
              </p>
              <Link
                className="inline-block text-sm text-ember-700 hover:underline"
                to={`/sessions/${lastDone.id}`}
              >
                Read what happened →
              </Link>
            </div>
          ) : (
            <p className="text-sm text-ink-600">
              Nothing has finished yet. Your first meeting will show up here.
            </p>
          )}
        </Card>

        <Card>
          <h2 className="mb-3 text-sm font-semibold tracking-wide text-ink-600 uppercase">
            Blockers
          </h2>
          {data.blockers.length === 0 ? (
            <p className="text-sm text-ink-600">
              🟢 Smooth sailing. Nothing is blocking the team.
            </p>
          ) : (
            <ul className="space-y-3">
              {data.blockers.map((blocker) => (
                <li key={blocker.id}>
                  <Link className="font-medium hover:underline" to={`/tasks/${blocker.task_id}`}>
                    {blocker.task_title ?? "A task"}
                  </Link>
                  <p className="text-sm text-ink-600">{blocker.reason}</p>
                  <p className="text-xs text-ink-600">
                    {blocker.raised_by} · {formatRelative(blocker.raised_at)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <h2 className="mb-3 text-sm font-semibold tracking-wide text-ink-600 uppercase">
            🏆 Bragging rights
          </h2>
          {data.leaderboard.length === 0 ? (
            <p className="text-sm text-ink-600">Nobody has earned anything yet. Play a game.</p>
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
        </Card>

        <Card className="lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold tracking-wide text-ink-600 uppercase">
            Recently
          </h2>
          <ActivityFeed items={data.activity} emptyLabel="Nothing has happened yet." />
        </Card>
      </div>
    </>
  );
}

function AttendanceLine({ sessionId }: { sessionId: string }) {
  const participants = useSessionParticipants(sessionId);
  const count = participants.data?.items.length ?? 0;
  if (count === 0) return null;
  return <p className="mt-1 text-sm text-ink-600">👥 {count} expected</p>;
}

function AttendanceCard({ sessionId }: { sessionId: string }) {
  const participants = useSessionParticipants(sessionId);
  const mark = useMarkAttendance(sessionId);

  return (
    <Card className="mb-6">
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-ink-600 uppercase">
        Who is here
      </h2>
      <p className="mb-3 text-sm text-ink-600">Tap a name as people arrive.</p>
      <ul className="flex flex-wrap gap-2">
        {(participants.data?.items ?? []).map((participant) => (
          <li key={participant.id}>
            <button
              type="button"
              aria-pressed={participant.attended}
              onClick={() =>
                void mark.mutateAsync({
                  participantId: participant.id,
                  attended: !participant.attended,
                })
              }
              className={
                "rounded-full border px-4 py-3 text-base " +
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
