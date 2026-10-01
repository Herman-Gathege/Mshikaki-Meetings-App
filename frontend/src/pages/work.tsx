import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  useBlockers,
  useChangeTaskStatus,
  useCreateComment,
  useCreateProject,
  useCreateTask,
  useMembers,
  useMyTasks,
  useProject,
  useProjects,
  useRaiseBlocker,
  useResolveBlocker,
  useTask,
  useTasks,
  useUpdateTask,
} from "@/api/hooks";
import type { Task } from "@/api/types";
import { ActivityFeed } from "@/components/ActivityFeed";
import { OriginTrail } from "@/components/OriginTrail";
import { StatusBadge } from "@/components/badges";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/states";
import { toast } from "@/components/toast";
import { Button, Card, Field, Input, Modal, Select, Textarea } from "@/components/ui/kit";
import { formatDateTime, isOverdue } from "@/lib/dates";

const NEXT_STATUS: Record<string, string> = {
  backlog: "in_progress",
  in_progress: "done",
  blocked: "in_progress",
  done: "in_progress",
};

export function WorkPage() {
  const [tab, setTab] = useState<"mine" | "all" | "board">("mine");
  const [status, setStatus] = useState("");
  const mine = useMyTasks();
  const all = useTasks(status ? { status } : {});
  const tasks = tab === "mine" ? mine.data?.items ?? [] : all.data?.items ?? [];

  return (
    <>
      <PageHeader title="Work" subtitle="Simple on purpose: backlog, in progress, blocked, done." />
      <nav className="mb-4 flex flex-wrap gap-2">
        {(["mine", "all", "board"] as const).map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => setTab(value)}
            className={
              "rounded-lg px-3 py-2 text-sm " +
              (tab === value ? "bg-ink-900 text-white" : "bg-white text-ink-600 hover:bg-ink-100")
            }
          >
            {value === "mine" ? "My work" : value === "all" ? "All tasks" : "Board"}
          </button>
        ))}
        {tab !== "mine" ? (
          <Select className="w-40" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Any status</option>
            {["backlog", "in_progress", "blocked", "done", "cancelled"].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </Select>
        ) : null}
      </nav>

      {(mine.isPending || all.isPending) && tab !== "board" ? <LoadingState /> : null}
      {(mine.isError || all.isError) && tab !== "board" ? (
        <ErrorState error={mine.error ?? all.error} />
      ) : null}

      {tab === "board" ? (
        <div className="grid gap-3 sm:grid-cols-4">
          {["backlog", "in_progress", "blocked", "done"].map((column) => (
            <div key={column} className="space-y-2">
              <h2 className="text-sm font-semibold text-ink-800">
                {column.replace("_", " ")} ({all.data?.items.filter((task) => task.status === column).length ?? 0})
              </h2>
              {all.data?.items
                .filter((task) => task.status === column)
                .map((task) => (
                  <TaskCard key={task.id} task={task} />
                ))}
            </div>
          ))}
        </div>
      ) : (
        <ul className="space-y-3">
          {tasks.length === 0 ? (
            <EmptyState
              title={tab === "mine" ? "🎯 Nothing to do yet" : "🎯 Nothing here yet"}
              body={
                tab === "mine"
                  ? "Enjoy the peace while it lasts. Work assigned to you lands here."
                  : "Tasks created in a meeting show up here."
              }
            />
          ) : null}
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} detailed />
          ))}
        </ul>
      )}

      <div className="mt-8">
        <BlockersCard />
      </div>
      <div className="mt-8">
        <ProjectsSection />
      </div>
    </>
  );
}

function TaskCard({ task, detailed = false }: { task: Task; detailed?: boolean }) {
  const change = useChangeTaskStatus();
  return (
    <Card as="li">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <Link className="font-medium hover:underline" to={`/tasks/${task.id}`}>
            {task.title}
          </Link>
          <p className="text-xs text-ink-400">
            {task.owner?.name ?? "unassigned"}
            {task.due_date
              ? ` · ${isOverdue(task.due_date, task.status) ? "overdue since" : "due"} ${task.due_date}`
              : ""}
            {detailed && task.origin.session_id ? " · from a session" : ""}
          </p>
          {task.open_blockers.length > 0 ? (
            <p className="mt-1 text-xs text-red-700">
              Blocked: {task.open_blockers[0]?.reason}
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={task.status} />
          <Button
            size="sm"
            variant="outline"
            disabled={change.isPending}
            onClick={() => {
              const next = NEXT_STATUS[task.status] ?? "in_progress";
              void change.mutateAsync({ id: task.id, status: next }).then(() =>
                toast(
                  next === "done"
                    ? "✅ Done!"
                    : task.status === "done"
                      ? "🔁 Reopened"
                      : "▶ In progress",
                ),
              );
            }}
          >
            {task.status === "done" ? "Reopen" : "Advance"}
          </Button>
        </div>
      </div>
    </Card>
  );
}

function BlockersCard() {
  const blockers = useBlockers(true);
  const resolve = useResolveBlocker();
  const [open, setOpen] = useState<string | null>(null);
  const [resolution, setResolution] = useState("");

  if (!blockers.data?.items.length) {
    return (
      <Card>
        <h2 className="text-sm font-semibold text-ink-800">Blockers</h2>
        <p className="mt-1 text-sm text-ink-600">
          🟢 Smooth sailing. Nothing is blocking the team.
        </p>
      </Card>
    );
  }

  return (
    <Card>
      <h2 className="mb-3 text-sm font-semibold text-ink-800">Blockers ({blockers.data.items.length})</h2>
      <ul className="space-y-3">
        {blockers.data.items.map((blocker) => (
          <li key={blocker.id} className="rounded-lg border border-ink-200 p-3">
            <p className="text-sm font-medium">{blocker.task_title ?? "A task"}</p>
            <p className="text-sm text-ink-600">{blocker.reason}</p>
            <p className="text-xs text-ink-400">raised by {blocker.raised_by}</p>
            {open === blocker.id ? (
              <div className="mt-2 space-y-2">
                <Input
                  value={resolution}
                  placeholder="What cleared it?"
                  onChange={(event) => setResolution(event.target.value)}
                />
                <Button
                  size="sm"
                  disabled={resolution.trim().length < 2}
                  onClick={() => {
                    void resolve
                      .mutateAsync({ blockerId: blocker.id, resolution })
                      .then(() => {
                        setOpen(null);
                        setResolution("");
                        toast("🧯 Blocker cleared!");
                      });
                  }}
                >
                  Resolve
                </Button>
              </div>
            ) : (
              <Button size="sm" variant="outline" className="mt-2" onClick={() => setOpen(blocker.id)}>
                Resolve
              </Button>
            )}
          </li>
        ))}
      </ul>
    </Card>
  );
}

function ProjectsSection() {
  const projects = useProjects();
  const create = useCreateProject();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ink-800">Projects</h2>
        <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
          New project
        </Button>
      </div>
      <ul className="space-y-2">
        {(projects.data?.items ?? []).map((project) => (
          <li key={project.id}>
            <Link className="text-sm hover:underline" to={`/projects/${project.id}`}>
              {project.name}
            </Link>
            <span className="ml-2 text-xs text-ink-400">{project.status}</span>
          </li>
        ))}
        {projects.data?.items.length === 0 ? (
          <li className="text-sm text-ink-600">
            Projects group work that outlives a single meeting.
          </li>
        ) : null}
      </ul>

      <Modal open={open} title="New project" onClose={() => setOpen(false)}>
        <Field label="Name">
          <Input value={name} onChange={(event) => setName(event.target.value)} />
        </Field>
        <Button
          className="mt-4"
          disabled={!name.trim()}
          onClick={() =>
            void create.mutateAsync({ name }).then(() => {
              setName("");
              setOpen(false);
            })
          }
        >
          Create
        </Button>
      </Modal>
    </Card>
  );
}

export function TaskPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const task = useTask(taskId);
  const members = useMembers();
  const change = useChangeTaskStatus();
  const update = useUpdateTask();
  const raise = useRaiseBlocker();
  const comment = useCreateComment();
  const [reason, setReason] = useState("");
  const [body, setBody] = useState("");

  if (task.isPending) return <LoadingState />;
  if (task.isError) return <ErrorState error={task.error} />;
  if (!task.data) return null;
  const data = task.data;

  return (
    <>
      <PageHeader
        title={data.title}
        subtitle={`${data.owner?.name ?? "unassigned"}${data.due_date ? ` · due ${data.due_date}` : ""}`}
        actions={<StatusBadge status={data.status} />}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <div className="flex flex-wrap gap-2">
              {["backlog", "in_progress", "blocked", "done", "cancelled"].map((value) => (
                <Button
                  key={value}
                  size="sm"
                  variant={value === data.status ? "secondary" : "outline"}
                  onClick={() => void change.mutateAsync({ id: data.id, status: value })}
                >
                  {value.replace("_", " ")}
                </Button>
              ))}
            </div>
            {data.description ? (
              <p className="mt-3 text-sm whitespace-pre-wrap">{data.description}</p>
            ) : null}
          </Card>

          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink-800">Owner and dates</h2>
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Owner">
                <Select
                  value={data.owner?.id ?? ""}
                  onChange={(event) =>
                    void update.mutateAsync({ id: data.id, ...{} }).then(() =>
                      // Owner changes go through the assign endpoint on the server.
                      fetch(`/api/tasks/${data.id}/assign`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json", "X-Mshikaki-Request": "1" },
                        body: JSON.stringify({ owner_id: event.target.value || null }),
                      }),
                    )
                  }
                >
                  <option value="">Unassigned</option>
                  {(members.data?.items ?? []).map((member) => (
                    <option key={member.user_id} value={member.user_id}>
                      {member.name}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Due date">
                <Input
                  type="date"
                  defaultValue={data.due_date ?? ""}
                  onChange={(event) =>
                    void update.mutateAsync({ id: data.id, due_date: event.target.value || null })
                  }
                />
              </Field>
              <Field label="Priority">
                <Select
                  defaultValue={data.priority}
                  onChange={(event) =>
                    void update.mutateAsync({ id: data.id, priority: event.target.value })
                  }
                >
                  {["low", "normal", "high", "urgent"].map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
          </Card>

          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink-800">Blockers</h2>
            <ul className="space-y-2">
              {data.open_blockers.map((blocker) => (
                <li key={blocker.id} className="text-sm text-red-700">
                  {blocker.reason} — raised by {blocker.raised_by}
                </li>
              ))}
            </ul>
            {data.status !== "done" ? (
              <div className="mt-3 space-y-2">
                <Input
                  value={reason}
                  placeholder="What is stopping this?"
                  onChange={(event) => setReason(event.target.value)}
                />
                <Button
                  size="sm"
                  variant="danger"
                  disabled={reason.trim().length < 3}
                  onClick={() =>
                    void raise.mutateAsync({ taskId: data.id, reason }).then(() => setReason(""))
                  }
                >
                  Mark blocked
                </Button>
              </div>
            ) : null}
          </Card>

          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink-800">Comments</h2>
            <ul className="space-y-2 text-sm">
              {data.comments.map((item) => (
                <li key={item.id}>
                  <span className="font-medium">{item.author}</span>{" "}
                  <span className="text-ink-400">{formatDateTime(item.created_at)}</span>
                  <p>{item.body}</p>
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
                  .mutateAsync({ target_type: "task", target_id: data.id, body })
                  .then(() => setBody(""))
              }
            >
              Comment
            </Button>
          </Card>
        </div>

        <div className="space-y-4">
          <OriginTrail origin={data.origin} />
          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink-800">History</h2>
            <ActivityFeed items={data.activity} />
          </Card>
        </div>
      </div>
    </>
  );
}

export function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const project = useProject(projectId);
  const createTask = useCreateTask();
  const [title, setTitle] = useState("");

  if (project.isPending) return <LoadingState />;
  if (project.isError) return <ErrorState error={project.error} />;
  if (!project.data) return null;
  const data = project.data;

  return (
    <>
      <PageHeader title={data.name} subtitle={data.description ?? "No description"} />
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink-800">Tasks</h2>
            <ul className="space-y-2">
              {data.tasks.map((task) => (
                <li key={task.id} className="flex items-center justify-between gap-2 text-sm">
                  <Link className="hover:underline" to={`/tasks/${task.id}`}>
                    {task.title}
                  </Link>
                  <StatusBadge status={task.status} />
                </li>
              ))}
              {data.tasks.length === 0 ? (
                <li className="text-sm text-ink-600">
                  🎯 Nothing here yet. Add the first piece of work.
                </li>
              ) : null}
            </ul>
            <div className="mt-3 flex gap-2">
              <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Add a task" />
              <Button
                disabled={!title.trim()}
                onClick={() =>
                  void createTask
                    .mutateAsync({ title, project_id: data.id, status: "backlog" })
                    .then(() => setTitle(""))
                }
              >
                Add
              </Button>
            </div>
          </Card>
          <Card>
            <h2 className="mb-3 text-sm font-semibold text-ink-800">Linked decisions</h2>
            <ul className="space-y-2 text-sm">
              {data.decisions.map((decision) => (
                <li key={decision.id}>
                  <Link className="hover:underline" to={`/decisions/${decision.id}`}>
                    {decision.statement}
                  </Link>
                </li>
              ))}
              {data.decisions.length === 0 ? (
                <li className="text-ink-600">No decisions linked yet.</li>
              ) : null}
            </ul>
          </Card>
        </div>
        <Card>
          <h2 className="mb-3 text-sm font-semibold text-ink-800">Activity</h2>
          <ActivityFeed items={data.activity} />
        </Card>
      </div>
    </>
  );
}
