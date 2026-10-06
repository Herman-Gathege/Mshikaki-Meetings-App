/**
 * Today answers three questions, in this order:

 *   1. What is happening?
 *   2. What do I need to do?
 *   3. What happened recently?

 * Everything else on the page is deliberately secondary. A person opening
 * Mshikaki before a meeting should know what to do without reading anything twice.
 */

import { useState } from "react";
import { Link } from "react-router-dom";

import {
  useAddParticipant,
  useMarkAttendance,
  useMembers,
  useMe,
  useSessionParticipants,
  useSessions,
  useToday,
} from "@/api/hooks";
import { toast } from "@/components/toast";
import type { Participant } from "@/api/types";
import { ActivityFeed } from "@/components/ActivityFeed";
import { StatusBadge } from "@/components/badges";
import { StartSessionButton } from "@/components/StartSessionButton";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/states";
import { Button, ButtonLink, Card, Select } from "@/components/ui/kit";
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
            title="No Mshikaki planned yet"
            body="Get the team together. A meeting needs a title, a time and an agenda."
            mark
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
  const members = useMembers();
  const me = useMe();
  const mark = useMarkAttendance(sessionId);
  const add = useAddParticipant(sessionId);
  const [missing, setMissing] = useState("");

  // Somebody who is in the room but was never recorded: an account made before
  // the join fix, or a phone that never opened the code. The facilitator can put
  // them in the meeting from here.
  const room = participants.data?.items ?? [];
  const canManage = ["owner", "admin", "facilitator"].includes(me.data?.role ?? "");
  const elsewhere = (members.data?.items ?? []).filter(
    (member) => !room.some((participant) => participant.user_id === member.user_id),
  );

  return (
    <Card className="mb-6">
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-ink-600 uppercase">
        Who is here
      </h2>
      <p className="mb-3 text-sm text-ink-600">Tap a name as people arrive.</p>
      <ul className="flex flex-wrap gap-2">
        {room.map((participant) => (
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

      {canManage && elsewhere.length > 0 ? (
        <div className="mt-4 border-t border-ink-200 pt-3">
          <p className="text-sm text-ink-600">
            Somebody here whose name is not on the list? Add them to this meeting.
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <Select
              className="w-56"
              aria-label="Add somebody to this meeting"
              value={missing}
              onChange={(event) => setMissing(event.target.value)}
            >
              <option value="">Pick a person</option>
              {elsewhere.map((member) => (
                <option key={member.user_id} value={member.user_id}>
                  {member.name}
                </option>
              ))}
            </Select>
            <Button
              disabled={!missing || add.isPending || mark.isPending}
              onClick={() => {
                const member = elsewhere.find((row) => row.user_id === missing);
                if (!member) return;
                void add
                  .mutateAsync({ user_id: member.user_id, role: "participant" })
                  .then((result: unknown) => {
                    // Adding somebody who is standing here means they are present,
                    // so tick them in the same breath.
                    const items = (result as { items?: Participant[] })?.items ?? [];
                    const theirs = items.find((row) => row.user_id === member.user_id);
                    if (theirs) {
                      return mark.mutateAsync({ participantId: theirs.id, attended: true });
                    }
                    return undefined;
                  })
                  .then(() => {
                    setMissing("");
                    toast(`✅ ${member.name} is in this meeting now`);
                  })
                  .catch(() => toast("Only the facilitator can add somebody here"));
              }}
            >
              {add.isPending ? "Adding…" : "Add to the meeting"}
            </Button>
          </div>
        </div>
      ) : null}
    </Card>
  );
}
