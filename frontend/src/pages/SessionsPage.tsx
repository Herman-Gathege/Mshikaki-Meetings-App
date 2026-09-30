import { useState } from "react";
import { Link } from "react-router-dom";

import { useCreateSession, useSessions } from "@/api/hooks";
import { StatusBadge } from "@/components/badges";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/states";
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
  };

  return (
    <>
      <PageHeader
        title="Sessions"
        subtitle="Every meeting, and everything it produced."
        actions={<Button onClick={() => setOpen(true)}>Plan a session</Button>}
      />

      {sessions.isPending ? <LoadingState /> : null}
      {sessions.isError ? <ErrorState error={sessions.error} /> : null}

      {sessions.data?.items.length === 0 ? (
        <EmptyState
          title="No sessions yet"
          body="Plan the first one: a title, a date, and the agenda as lines of text."
          action={<Button onClick={() => setOpen(true)}>Plan a session</Button>}
        />
      ) : null}

      <ul className="space-y-3">
        {(sessions.data?.items ?? []).map((session) => (
          <Card as="li" key={session.id}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <Link className="text-lg font-medium hover:underline" to={`/sessions/${session.id}`}>
                  {session.title}
                </Link>
                <p className="text-sm text-ink-600">
                  {formatDateTime(session.scheduled_at)}
                  {session.location ? ` · ${session.location}` : ""}
                  {session.facilitator ? ` · ${session.facilitator}` : ""}
                </p>
                <p className="mt-1 text-xs text-ink-400">
                  {session.counts.ideas} ideas · {session.counts.decisions} decisions ·{" "}
                  {session.counts.tasks} tasks · {session.counts.games} games
                </p>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={session.status} />
                {session.status === "active" ? (
                  <Link to={`/sessions/${session.id}/run`}>
                    <Button size="sm">Run Mode</Button>
                  </Link>
                ) : null}
              </div>
            </div>
          </Card>
        ))}
      </ul>

      <Modal open={open} title="Plan a session" onClose={() => setOpen(false)}>
        <div className="space-y-4">
          <Field label="Title" hint="Leave blank and we will number it for you.">
            <Input value={title} onChange={(event) => setTitle(event.target.value)} />
          </Field>
          <Field label="When">
            <Input
              type="datetime-local"
              value={scheduledAt}
              onChange={(event) => setScheduledAt(event.target.value)}
            />
          </Field>
          <Field label="Where">
            <Input
              value={location}
              placeholder="Boardroom, or online"
              onChange={(event) => setLocation(event.target.value)}
            />
          </Field>
          <Field label="Agenda" hint="One item per line. You can add or reorder later.">
            <Textarea
              rows={4}
              value={agenda}
              placeholder={"Icebreaker\nAutomation ideas\nAssignments"}
              onChange={(event) => setAgenda(event.target.value)}
            />
          </Field>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => void submit()} disabled={create.isPending}>
              {create.isPending ? "Creating..." : "Create session"}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
