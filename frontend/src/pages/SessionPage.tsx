import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  useAddAgendaItem,
  useCoverAgendaItem,
  useIdeas,
  useMe,
  useRegenerateSummary,
  useSession,
  useSessionActivity,
  useSessionExport,
  useSessionLifecycle,
  useSessionSummary,
  useTasks,
} from "@/api/hooks";
import { ActivityFeed } from "@/components/ActivityFeed";
import { StartSessionButton } from "@/components/StartSessionButton";
import { StatusBadge } from "@/components/badges";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/states";
import { toast } from "@/components/toast";
import { Button, ButtonLink, Card, Field, Input } from "@/components/ui/kit";
import { formatDateTime } from "@/lib/dates";

const TABS = ["Overview", "Agenda", "Ideas", "Tasks", "Summary", "Activity"] as const;
type Tab = (typeof TABS)[number];

export function SessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const session = useSession(sessionId);
  const me = useMe();
  const [tab, setTab] = useState<Tab>("Overview");

  if (session.isPending) return <LoadingState />;
  if (session.isError) return <ErrorState error={session.error} />;
  if (!session.data) return null;

  const data = session.data;
  // Starting, closing and cancelling belong to the facilitator or an admin. The
  // controls used to be shown to everybody, and a member who pressed one got
  // nothing at all: no action and no explanation.
  const isFacilitator = data.facilitator?.id === me.data?.user.id;
  const isStaff = me.data?.role === "owner" || me.data?.role === "admin";
  const canRun = isFacilitator || isStaff;

  return (
    <>
      <PageHeader
        title={data.title}
        subtitle={`${formatDateTime(data.scheduled_at)}${data.location ? ` · ${data.location}` : ""} · facilitated by ${data.facilitator?.name ?? "nobody yet"}`}
        actions={
          <>
            <StatusBadge status={data.status} />
            {data.status === "planned" && canRun ? <StartButton sessionId={data.id} /> : null}
            {data.status === "active" || data.status === "paused" ? (
              <>
                {canRun ? <ButtonLink to={`/sessions/${data.id}/run`}>Run Mode</ButtonLink> : null}
                {canRun ? <CloseButton sessionId={data.id} /> : null}
              </>
            ) : null}
            {data.status === "completed" && canRun ? (
              <ButtonLink to={`/sessions/${data.id}/run`} variant="outline">
                Review Run Mode
              </ButtonLink>
            ) : null}
            {!canRun ? (
              <span className="self-center text-sm text-ink-600">
                {data.facilitator
                  ? `${data.facilitator.name} runs this meeting`
                  : "Waiting for a facilitator"}
              </span>
            ) : null}
          </>
        }
      />

      <nav className="mb-4 flex gap-1 overflow-x-auto">
        {TABS.map((name) => (
          <button
            key={name}
            type="button"
            onClick={() => setTab(name)}
            className={
              "rounded-lg px-3 py-2 text-sm whitespace-nowrap " +
              (tab === name ? "bg-ink-900 text-white" : "bg-white text-ink-600 hover:bg-ink-100")
            }
          >
            {name}
          </button>
        ))}
      </nav>

      {tab === "Overview" ? <Overview sessionId={data.id} /> : null}
      {tab === "Agenda" ? <AgendaTab sessionId={data.id} /> : null}
      {tab === "Ideas" ? <IdeasTab sessionId={data.id} /> : null}
      {tab === "Tasks" ? <TasksTab sessionId={data.id} /> : null}
      {tab === "Summary" ? <SummaryTab sessionId={data.id} hasSummary={data.has_summary} /> : null}
      {tab === "Activity" ? <ActivityTab sessionId={data.id} /> : null}
    </>
  );
}

function StartButton({ sessionId }: { sessionId: string }) {
  return <StartSessionButton sessionId={sessionId} />;
}

function CloseButton({ sessionId }: { sessionId: string }) {
  const lifecycle = useSessionLifecycle(sessionId);
  return (
    <Button
      variant="outline"
      onClick={() => void lifecycle.close.mutateAsync().then(() => toast("🎉 That's a wrap!"))}
      disabled={lifecycle.close.isPending}
    >
      {lifecycle.close.isPending ? "Closing..." : "Close session"}
    </Button>
  );
}

function Overview({ sessionId }: { sessionId: string }) {
  const session = useSession(sessionId);
  const data = session.data;
  if (!data) return null;
  const cancellable = ["planned", "active", "paused"].includes(data.status);
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Card>
        <h2 className="mb-2 text-sm font-semibold text-ink-800">What came out of this</h2>
        <ul className="space-y-1 text-sm">
          <li>{data.counts.ideas} ideas</li>
          <li>{data.counts.decisions} decisions</li>
          <li>
            {data.counts.tasks} tasks, {data.tasks_open} still open
          </li>
          <li>{data.counts.games} games played</li>
        </ul>
      </Card>
      <Card>
        <h2 className="mb-2 text-sm font-semibold text-ink-800">The record</h2>
        <p className="text-sm text-ink-600">
          Started {formatDateTime(data.started_at) || "not yet"}
          {data.ended_at ? `, closed ${formatDateTime(data.ended_at)}` : ""}.
        </p>
        <p className="mt-2 text-sm text-ink-600">
          {data.has_summary ? "The summary was generated at close." : "No summary yet."}
        </p>
      </Card>
      {cancellable ? <CancelMeeting sessionId={sessionId} /> : null}
    </div>
  );
}

/** A meeting that is not going to happen. It stays in the record either way. */
function CancelMeeting({ sessionId }: { sessionId: string }) {
  const lifecycle = useSessionLifecycle(sessionId);
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");

  if (!open) {
    return (
      <Card className="sm:col-span-2">
        <p className="text-sm text-ink-600">
          Not going ahead? Cancelling keeps the meeting in the record with the reason.
        </p>
        <Button variant="danger" size="sm" className="mt-2" onClick={() => setOpen(true)}>
          Cancel this meeting
        </Button>
      </Card>
    );
  }

  return (
    <Card className="sm:col-span-2">
      <Field label="Why is it cancelled?" hint="Optional, and it goes in the record.">
        <Input value={reason} onChange={(event) => setReason(event.target.value)} />
      </Field>
      <div className="mt-3 flex gap-2">
        <Button
          variant="danger"
          disabled={lifecycle.cancel.isPending}
          onClick={() =>
            void lifecycle.cancel.mutateAsync(reason).then(() => toast("🚫 Meeting cancelled"))
          }
        >
          {lifecycle.cancel.isPending ? "Cancelling…" : "Yes, cancel it"}
        </Button>
        <Button variant="ghost" onClick={() => setOpen(false)}>
          Keep it
        </Button>
      </div>
    </Card>
  );
}

function AgendaTab({ sessionId }: { sessionId: string }) {
  const session = useSession(sessionId);
  const add = useAddAgendaItem(sessionId);
  const cover = useCoverAgendaItem(sessionId);
  const [title, setTitle] = useState("");

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex gap-2">
          <Input
            value={title}
            placeholder="Add an agenda item"
            onChange={(event) => setTitle(event.target.value)}
          />
          <Button
            disabled={!title.trim() || add.isPending}
            onClick={() => {
              void add.mutateAsync(title.trim());
              setTitle("");
            }}
          >
            Add
          </Button>
        </div>
      </Card>
      <ul className="space-y-2">
        {(session.data?.agenda ?? []).map((item) => (
          <Card as="li" key={item.id} className="flex items-center justify-between gap-3">
            <span className={item.covered ? "text-ink-600 line-through" : ""}>{item.title}</span>
            {!item.covered ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => void cover.mutateAsync(item.id)}
              >
                Covered
              </Button>
            ) : (
              <StatusBadge status="done" />
            )}
          </Card>
        ))}
      </ul>
    </div>
  );
}

function IdeasTab({ sessionId }: { sessionId: string }) {
  const ideas = useIdeas({ session_id: sessionId });
  if (ideas.data?.items.length === 0) {
    return <EmptyState title="No ideas captured yet" body="Use the + Idea button from anywhere." />;
  }
  return (
    <ul className="space-y-3">
      {(ideas.data?.items ?? []).map((idea) => (
        <Card as="li" key={idea.id}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <Link className="font-medium hover:underline" to={`/ideas/${idea.id}`}>
                {idea.title}
              </Link>
              <p className="text-xs text-ink-600">by {idea.author.name}</p>
            </div>
            <StatusBadge status={idea.status} />
          </div>
        </Card>
      ))}
    </ul>
  );
}

function TasksTab({ sessionId }: { sessionId: string }) {
  const tasks = useTasks({ session_id: sessionId });
  if (tasks.data?.items.length === 0) {
    return <EmptyState title="No tasks from this session" body="Assign work in Run Mode." />;
  }
  return (
    <ul className="space-y-3">
      {(tasks.data?.items ?? []).map((task) => (
        <Card as="li" key={task.id}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <Link className="font-medium hover:underline" to={`/tasks/${task.id}`}>
                {task.title}
              </Link>
              <p className="text-xs text-ink-600">
                {task.owner ? task.owner.name : "unassigned"}
                {task.due_date ? ` · due ${task.due_date}` : ""}
              </p>
            </div>
            <StatusBadge status={task.status} />
          </div>
        </Card>
      ))}
    </ul>
  );
}

function SummaryTab({ sessionId, hasSummary }: { sessionId: string; hasSummary: boolean }) {
  const summary = useSessionSummary(sessionId, hasSummary);
  const regenerate = useRegenerateSummary(sessionId);
  const exportText = useSessionExport(sessionId);
  const [copied, setCopied] = useState(false);
  const [fallbackText, setFallbackText] = useState<string | null>(null);

  const copy = async () => {
    const result = await exportText.mutateAsync();
    // navigator.clipboard needs a secure origin; on http://10.x.x.x it is absent.
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(result);
      setCopied(true);
      return;
    }
    setFallbackText(result);
  };

  if (!hasSummary) {
    return (
      <EmptyState
        title="No summary yet"
        body="Close the session and Mshikaki writes the summary for you."
        action={
          <Button onClick={() => void regenerate.mutateAsync()} disabled={regenerate.isPending}>
            Generate now
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => void copy()} disabled={exportText.isPending}>
          {copied ? "Copied" : "Copy for WhatsApp"}
        </Button>
        <ButtonLink
          href={`/api/sessions/${sessionId}/minutes.html`}
          download
          variant="secondary"
        >
          📄 Download minutes
        </ButtonLink>
        <ButtonLink
          href={`/api/sessions/${sessionId}/export.txt`}
          target="_blank"
          rel="noreferrer"
          variant="outline"
        >
          Open plain text
        </ButtonLink>
        <Button
          variant="outline"
          onClick={() => void regenerate.mutateAsync()}
          disabled={regenerate.isPending}
        >
          Regenerate
        </Button>
      </div>

      <Card>
        <pre className="font-sans text-sm whitespace-pre-wrap text-ink-900">
          {summary.data?.text ?? "Loading..."}
        </pre>
      </Card>

      {fallbackText ? (
        <Card>
          <p className="mb-2 text-sm text-ink-600">
            Copying is blocked on an insecure connection. Select and copy this text:
          </p>
          <textarea
            readOnly
            className="h-48 w-full rounded-lg border border-ink-200 p-3 font-sans text-sm"
            value={fallbackText}
            onFocus={(event) => event.currentTarget.select()}
          />
        </Card>
      ) : null}
    </div>
  );
}

function ActivityTab({ sessionId }: { sessionId: string }) {
  const activity = useSessionActivity(sessionId);
  return (
    <Card>
      <ActivityFeed items={activity.data?.items ?? []} />
    </Card>
  );
}
