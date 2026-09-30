import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  useCreateComment,
  useCreateTask,
  useDecision,
  useIdea,
  useIdeas,
  useRecordDecision,
  useUpdateIdea,
} from "@/api/hooks";
import { ActivityFeed } from "@/components/ActivityFeed";
import { OriginTrail } from "@/components/OriginTrail";
import { StatusBadge } from "@/components/badges";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/states";
import { Button, Card, Field, Input, Select, Textarea } from "@/components/ui/kit";
import { formatDateTime } from "@/lib/dates";

const STATUSES = ["new", "discussing", "accepted", "parked", "rejected"] as const;

export function IdeasPage() {
  const [status, setStatus] = useState("");
  const ideas = useIdeas(status ? { status } : {});

  return (
    <>
      <PageHeader
        title="Ideas"
        subtitle="Not every idea becomes work, and that is fine."
        actions={
          <Select className="w-40" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">All statuses</option>
            {STATUSES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </Select>
        }
      />

      {ideas.isPending ? <LoadingState /> : null}
      {ideas.isError ? <ErrorState error={ideas.error} /> : null}
      {ideas.data?.items.length === 0 ? (
        <EmptyState title="No ideas yet" body="Capture the first one with the + Idea button." />
      ) : null}

      <ul className="space-y-3">
        {(ideas.data?.items ?? []).map((idea) => (
          <Card as="li" key={idea.id}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <Link className="font-medium hover:underline" to={`/ideas/${idea.id}`}>
                  {idea.title}
                </Link>
                {idea.description ? (
                  <p className="mt-1 line-clamp-2 text-sm text-ink-600">{idea.description}</p>
                ) : null}
                <p className="mt-1 text-xs text-ink-400">
                  {idea.author.name} · {formatDateTime(idea.created_at)}
                  {idea.converted_to ? ` · became a ${idea.converted_to.type}` : ""}
                </p>
              </div>
              <StatusBadge status={idea.status} />
            </div>
          </Card>
        ))}
      </ul>
    </>
  );
}

export function IdeaPage() {
  const { ideaId } = useParams<{ ideaId: string }>();
  const idea = useIdea(ideaId);
  const update = useUpdateIdea();
  const comment = useCreateComment();
  const record = useRecordDecision();
  const createTask = useCreateTask();
  const [body, setBody] = useState("");
  const [deciding, setDeciding] = useState(false);
  const [statement, setStatement] = useState("");
  const [taskTitle, setTaskTitle] = useState("");

  if (idea.isPending) return <LoadingState />;
  if (idea.isError) return <ErrorState error={idea.error} />;
  if (!idea.data) return null;
  const data = idea.data;

  return (
    <>
      <PageHeader
        title={data.title}
        subtitle={`${data.author.name} · ${formatDateTime(data.created_at)}`}
        actions={<StatusBadge status={data.status} />}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card>
            {data.description ? (
              <p className="text-sm whitespace-pre-wrap">{data.description}</p>
            ) : (
              <p className="text-sm text-ink-600">No description yet.</p>
            )}
          </Card>

          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink-800">Move it along</h2>
            <div className="flex flex-wrap gap-2">
              {STATUSES.filter((value) => value !== data.status).map((value) => (
                <Button
                  key={value}
                  variant="outline"
                  size="sm"
                  onClick={() => void update.mutateAsync({ id: data.id, status: value })}
                >
                  Mark {value}
                </Button>
              ))}
              <Button size="sm" onClick={() => setDeciding((open) => !open)}>
                Record decision
              </Button>
            </div>

            {deciding ? (
              <div className="mt-4 space-y-2">
                <Field label="The decision">
                  <Input
                    value={statement || data.title}
                    onChange={(event) => setStatement(event.target.value)}
                  />
                </Field>
                <Button
                  disabled={record.isPending}
                  onClick={() =>
                    void record.mutateAsync({
                      statement: statement || data.title,
                      idea_id: data.id,
                      session_id: data.session_id ?? undefined,
                    })
                  }
                >
                  Save decision
                </Button>
              </div>
            ) : null}

            <div className="mt-5 border-t border-ink-200 pt-4">
              <Field label="Or turn it straight into a task">
                <Input
                  value={taskTitle}
                  placeholder="Task title"
                  onChange={(event) => setTaskTitle(event.target.value)}
                />
              </Field>
              <Button
                className="mt-2"
                variant="outline"
                disabled={!taskTitle.trim() || createTask.isPending}
                onClick={() =>
                  void createTask.mutateAsync({
                    title: taskTitle,
                    idea_id: data.id,
                    session_id: data.session_id,
                    status: "backlog",
                  })
                }
              >
                Create task
              </Button>
            </div>
          </Card>

          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink-800">Comments</h2>
            <ul className="space-y-3">
              {data.comments.map((item) => (
                <li key={item.id} className="text-sm">
                  <span className="font-medium">{item.author}</span>{" "}
                  <span className="text-ink-400">{formatDateTime(item.created_at)}</span>
                  <p className="text-ink-900">{item.body}</p>
                </li>
              ))}
              {data.comments.length === 0 ? (
                <li className="text-sm text-ink-600">No comments yet.</li>
              ) : null}
            </ul>
            <div className="mt-3 space-y-2">
              <Textarea
                rows={2}
                value={body}
                placeholder="Add a thought"
                onChange={(event) => setBody(event.target.value)}
              />
              <Button
                size="sm"
                disabled={!body.trim() || comment.isPending}
                onClick={() => {
                  void comment
                    .mutateAsync({ target_type: "idea", target_id: data.id, body })
                    .then(() => setBody(""));
                }}
              >
                Comment
              </Button>
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <OriginTrail
            origin={{ session_id: data.session_id, idea_id: data.id }}
            labels={{ session: "Session where this was captured" }}
          />
          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink-800">History</h2>
            <ActivityFeed items={data.activity} />
          </Card>
        </div>
      </div>
    </>
  );
}

export function DecisionPage() {
  const { decisionId } = useParams<{ decisionId: string }>();
  const decision = useDecision(decisionId);
  const comment = useCreateComment();
  const [body, setBody] = useState("");

  if (decision.isPending) return <LoadingState />;
  if (decision.isError) return <ErrorState error={decision.error} />;
  if (!decision.data) return null;
  const data = decision.data;

  return (
    <>
      <PageHeader
        title="Decision"
        subtitle={`Recorded by ${data.recorded_by} · ${formatDateTime(data.decided_at)}`}
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <p className="text-lg">{data.statement}</p>
            {data.rationale ? (
              <p className="mt-2 text-sm text-ink-600">{data.rationale}</p>
            ) : null}
            {data.is_superseded ? (
              <p className="mt-3 text-sm text-ember-600">
                This decision was superseded by a later one.
              </p>
            ) : null}
          </Card>
          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink-800">Comments</h2>
            <ul className="space-y-2 text-sm">
              {data.comments.map((item) => (
                <li key={item.id}>
                  <span className="font-medium">{item.author}</span>: {item.body}
                </li>
              ))}
            </ul>
            <Textarea
              className="mt-3"
              rows={2}
              value={body}
              onChange={(event) => setBody(event.target.value)}
            />
            <Button
              className="mt-2"
              size="sm"
              disabled={!body.trim()}
              onClick={() =>
                void comment
                  .mutateAsync({ target_type: "decision", target_id: data.id, body })
                  .then(() => setBody(""))
              }
            >
              Comment
            </Button>
          </Card>
        </div>
        <div className="space-y-4">
          <OriginTrail origin={{ session_id: data.session_id, idea_id: data.idea_id }} />
          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink-800">History</h2>
            <ActivityFeed items={data.activity} />
          </Card>
        </div>
      </div>
    </>
  );
}
