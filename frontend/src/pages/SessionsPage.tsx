/**
 * The list of meetings.

 * Every row has exactly one obvious action, and it is the action that makes sense
 * for that state: start a planned meeting, open a running one, read a finished one.
 */

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useCreateSession, useSessionLifecycle, useSessions } from "@/api/hooks";
import type { SessionListItem } from "@/api/types";
import { StatusBadge } from "@/components/badges";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/states";
import { toast } from "@/components/toast";
import { Button, Card, Field, Input, Modal, Textarea } from "@/components/ui/kit";
import { formatDateTime } from "@/lib/dates";

export function SessionsPage() {
  const sessions = useSessions();
  const create = useCreateSession();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [location, setLocation] = useState("");
  const [agenda, setAgenda] = useState("");

  const submit = async () => {
    await create.mutateAsync({
      title: title || undefined,
      scheduled_at: scheduledAt ? new Date(scheduledAt).toISOString() : undefined,
      location: location || undefined,
      agenda: agenda
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean),
    });
    setTitle("");
    setAgenda("");
    setScheduledAt("");
    setLocation("");
    setOpen(false);
    toast("🍢 Session planned!");
  };

  return (
    <>
      <PageHeader
        title="🍢 Sessions"
        subtitle="Every meeting, and everything it produced."
        actions={
          <Button size="lg" onClick={() => setOpen(true)}>
            Plan a session
          </Button>
        }
      />

      {sessions.isPending ? <LoadingState label="Loading your meetings…" /> : null}
      {sessions.isError ? <ErrorState error={sessions.error} /> : null}

      {sessions.data?.items.length === 0 ? (
        <EmptyState
          title="🍢 No Mshikaki planned yet"
          body="Get the team together. A meeting needs a title, a time and an agenda."
          action={<Button size="lg" onClick={() => setOpen(true)}>Plan a session</Button>}
        />
      ) : null}

      <ul className="space-y-3">
        {(sessions.data?.items ?? []).map((session) => (
          <SessionRow key={session.id} session={session} />
        ))}
      </ul>

      <Modal open={open} title="Plan a session" onClose={() => setOpen(false)}>
        <div className="space-y-4">
          <Field label="What are we calling it?" hint="Leave it blank and Mshikaki numbers it.">
            <Input
              autoFocus
              value={title}
              placeholder="Innovations weekly catch-up"
              onChange={(event) => setTitle(event.target.value)}
            />
          </Field>
          <Field label="When?">
            <Input
              type="datetime-local"
              value={scheduledAt}
              onChange={(event) => setScheduledAt(event.target.value)}
            />
          </Field>
          <Field label="Where?">
            <Input
              value={location}
              placeholder="Boardroom, or online"
              onChange={(event) => setLocation(event.target.value)}
            />
          </Field>
          <Field label="Agenda" hint="One item per line. You can change it later.">
            <Textarea
              rows={4}
              value={agenda}
              placeholder={"Warm up\nAutomation ideas\nAssignments"}
              onChange={(event) => setAgenda(event.target.value)}
            />
          </Field>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button size="lg" onClick={() => void submit()} disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create the meeting"}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}

function SessionRow({ session }: { session: SessionListItem }) {
  const lifecycle = useSessionLifecycle(session.id);
  const navigate = useNavigate();
  const { ideas, decisions, tasks, games } = session.counts;

  const startAndRun = async () => {
    await lifecycle.start.mutateAsync();
    toast("🍢 Session started!");
    navigate(`/sessions/${session.id}/run`);
  };

  return (
    <Card as="li">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <Link className="text-lg font-medium hover:underline" to={`/sessions/${session.id}`}>
            {session.title}
          </Link>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-ink-600">
            <StatusBadge status={session.status} />
            {formatDateTime(session.scheduled_at)}
            {session.location ? ` · ${session.location}` : ""}
            {session.facilitator ? ` · ${session.facilitator}` : ""}
          </p>
          <p className="mt-1 text-sm text-ink-600">
            {session.status === "completed"
              ? `What happened: ${ideas} ideas, ${decisions} decisions, ${tasks} tasks, ${games} games`
              : `${ideas} ideas · ${decisions} decisions · ${tasks} tasks · ${games} games so far`}
          </p>
        </div>

        <div className="shrink-0">
          {session.status === "planned" ? (
            <Button size="lg" onClick={() => void startAndRun()} disabled={lifecycle.start.isPending}>
              {lifecycle.start.isPending ? "Starting…" : "Start →"}
            </Button>
          ) : null}
          {session.status === "active" ? (
            <Link to={`/sessions/${session.id}/run`}>
              <Button size="lg">Run Mode →</Button>
            </Link>
          ) : null}
          {session.status === "paused" ? (
            <Link to={`/sessions/${session.id}/run`}>
              <Button size="lg">Resume →</Button>
            </Link>
          ) : null}
          {session.status === "completed" ? (
            <Link to={`/sessions/${session.id}`}>
              <Button size="lg" variant="outline">
                Read what happened →
              </Button>
            </Link>
          ) : null}
        </div>
      </div>
    </Card>
  );
}
