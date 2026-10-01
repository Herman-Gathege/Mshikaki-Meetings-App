/**
 * Run Mode: one facilitator drives, everybody follows.

 * The stage lives on the session, not in the facilitator's browser, so a
 * participant who opens the meeting, or joins late by scanning the code, arrives
 * on the same screen. Participants see the meeting without the controls that
 * advance it, and when the facilitator wraps up everybody is released back to
 * normal navigation.

 * Screen-first by design: large type, one action per step, readable from three
 * metres. Capture still works from a phone regardless of what this screen shows.
 */

import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  useCreateTask,
  useGames,
  useIdeas,
  useMe,
  useRecordDecision,
  useSession,
  useSessionLifecycle,
  useSessionParticipants,
  useStartPlay,
  useTasks,
  useUpdateIdea,
} from "@/api/hooks";
import type { SessionDetail } from "@/api/types";
import { CaptureSheet } from "@/components/CaptureSheet";
import { StatusBadge } from "@/components/badges";
import { ErrorState, LoadingState } from "@/components/states";
import { toast } from "@/components/toast";
import { Button, ButtonLink, Card, Field, Input, Select } from "@/components/ui/kit";
import { formatDateTime } from "@/lib/dates";

// The journey is stated in the words a facilitator would use out loud.
const STEPS = [
  { key: "play", label: "🎲 Let's play" },
  { key: "capture", label: "💡 What are we thinking" },
  { key: "decide", label: "🧠 What did we decide" },
  { key: "assign", label: "🎯 Who's got this" },
  { key: "close", label: "🍢 That's a wrap" },
] as const;
type Step = (typeof STEPS)[number]["key"];

const STAGE_KEYS = STEPS.map((entry) => entry.key) as readonly Step[];

function isStage(value: string | null | undefined): value is Step {
  return Boolean(value) && STAGE_KEYS.includes(value as Step);
}

export function RunModePage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  // Poll while the meeting runs: this is how the room converges on the stage.
  const session = useSession(sessionId, 4000);
  const me = useMe();
  const navigate = useNavigate();
  const lifecycle = useSessionLifecycle(sessionId ?? "");
  const [draftStage, setDraftStage] = useState<Step | null>(null);
  const [captureOpen, setCaptureOpen] = useState(false);
  const released = useRef(false);

  const data = session.data;
  const serverStage: Step = isStage(data?.run_mode_stage) ? data.run_mode_stage : "play";
  const isStaff = me.data?.role === "owner" || me.data?.role === "admin";
  const canDrive = Boolean(
    data && (data.facilitator?.id === me.data?.user.id || isStaff),
  );
  // The facilitator may move ahead of the server for a moment; everybody else
  // only ever sees what the server says.
  const stage: Step = canDrive ? (draftStage ?? serverStage) : serverStage;

  // When the server moves, stop holding a local opinion about it.
  useEffect(() => {
    setDraftStage(null);
  }, [serverStage]);

  // Released: the meeting ended, was cancelled, or has not started.
  useEffect(() => {
    if (!data || released.current) return;
    if (data.status === "completed" || data.status === "cancelled") {
      released.current = true;
      toast("🍢 That's a wrap! Back to normal Mshikaki.");
      navigate(`/sessions/${data.id}`, { replace: true });
    } else if (data.status === "planned") {
      released.current = true;
      navigate(`/sessions/${data.id}`, { replace: true });
    }
  }, [data, navigate]);

  if (session.isPending) return <LoadingState label="Joining the meeting…" />;
  if (session.isError) return <ErrorState error={session.error} />;
  if (!data) return null;

  const index = STEPS.findIndex((entry) => entry.key === stage);
  const previous = index > 0 ? STEPS[index - 1]?.key : undefined;
  const next = index + 1 < STEPS.length ? STEPS[index + 1]?.key : undefined;

  const goToStage = (target: Step) => {
    setDraftStage(target);
    lifecycle.setStage.mutate(target);
  };

  return (
    <div className="min-h-dvh bg-ink-900 pb-24 text-white">
      <header className="border-b border-white/10 px-5 py-4">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs tracking-widest text-white/50 uppercase">
              Run Mode
              {data.status === "paused" ? " · paused" : ""}
            </p>
            <h1 className="text-2xl font-semibold">{data.title}</h1>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="rounded-full bg-white/10 px-3 py-1">
              {data.counts.ideas} ideas · {data.counts.decisions} decisions · {data.counts.tasks} tasks
            </span>
            <ButtonLink
              to={`/sessions/${data.id}`}
              variant="ghost"
              size="sm"
              className="text-white hover:bg-white/10"
            >
              Leave
            </ButtonLink>
          </div>
        </div>
      </header>

      {canDrive ? null : (
        <p className="mx-auto max-w-5xl px-5 pt-4 text-lg text-white/70">
          You're in the meeting. Follow along with the facilitator. 🍢
        </p>
      )}

      <nav className="mx-auto flex max-w-5xl gap-2 px-5 py-4">
        {STEPS.map((entry, position) => {
          const current = position === index;
          const shared = { key: entry.key, className: "" };
          const classes =
            "flex-1 rounded-xl px-3 py-3 text-sm font-medium " +
            (current
              ? "bg-ember-500 text-ink-900"
              : position < index
                ? "bg-white/20 text-white/80"
                : "bg-white/10 text-white/60");
          return canDrive ? (
            <button
              {...shared}
              type="button"
              aria-current={current ? "step" : undefined}
              onClick={() => goToStage(entry.key)}
              className={classes}
            >
              {entry.label}
            </button>
          ) : (
            <div
              {...shared}
              aria-current={current ? "step" : undefined}
              className={`${classes} text-center`}
            >
              {entry.label}
            </div>
          );
        })}
      </nav>

      <main className="mx-auto max-w-5xl px-5">
        {stage === "play" ? <PlayStep session={data} canDrive={canDrive} /> : null}
        {stage === "capture" ? (
          <CaptureStep
            sessionId={data.id}
            canDrive={canDrive}
            onOpenCapture={() => setCaptureOpen(true)}
          />
        ) : null}
        {stage === "decide" ? <DecideStep sessionId={data.id} canDrive={canDrive} /> : null}
        {stage === "assign" ? <AssignStep sessionId={data.id} canDrive={canDrive} /> : null}
        {stage === "close" ? <CloseStep sessionId={data.id} canDrive={canDrive} /> : null}
      </main>

      {canDrive ? (
        <footer className="fixed inset-x-0 bottom-0 border-t border-white/10 bg-ink-900/95 px-5 py-4 backdrop-blur">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-3">
            <Button
              variant="ghost"
              className="text-white hover:bg-white/10"
              disabled={!previous}
              onClick={() => previous && goToStage(previous)}
            >
              Back
            </Button>
            <div className="flex gap-2">
              {data.status === "paused" ? (
                <Button
                  variant="ghost"
                  className="text-white hover:bg-white/10"
                  onClick={() => void lifecycle.resume.mutateAsync()}
                >
                  Resume
                </Button>
              ) : (
                <Button
                  variant="ghost"
                  className="text-white hover:bg-white/10"
                  onClick={() => void lifecycle.pause.mutateAsync()}
                >
                  Pause
                </Button>
              )}
              <Button
                size="lg"
                onClick={() => (next ? goToStage(next) : goToStage("close"))}
              >
                {next ? `Next: ${STEPS[index + 1]?.label}` : "Finish"}
              </Button>
            </div>
          </div>
        </footer>
      ) : null}

      <CaptureSheet
        open={captureOpen}
        onClose={() => setCaptureOpen(false)}
        defaultSessionId={data.id}
      />
    </div>
  );
}

function PlayStep({ session, canDrive }: { session: SessionDetail; canDrive: boolean }) {
  const games = useGames();
  const startPlay = useStartPlay(session.id);
  const navigate = useNavigate();
  const [gameKey, setGameKey] = useState("");

  const running = session.games.find((game) => game.status === "running");
  const quickGames = (games.data?.items ?? []).filter((game) => game.typical_minutes <= 15);

  if (!canDrive) {
    return (
      <Card className="bg-white/5 text-white">
        <h2 className="text-3xl font-semibold">🎲 The game</h2>
        {running ? (
          <p className="mt-3 text-xl text-white/80">
            The facilitator is running a game. Watch the shared screen.
          </p>
        ) : (
          <p className="mt-3 text-xl text-white/80">
            The facilitator is choosing a game to warm the room up.
          </p>
        )}
      </Card>
    );
  }

  const start = async () => {
    const pick = gameKey || quickGames[0]?.key;
    if (!pick) return;
    const play = await startPlay.mutateAsync({ game_key: pick });
    navigate(`/play/${play.id}`);
  };

  return (
    <Card className="bg-white/5 text-white">
      <h2 className="text-3xl font-semibold">🎲 Let's play</h2>
      <p className="mt-2 max-w-2xl text-white/70">
        Pick something short and get people laughing. The games are not work-related on purpose.
      </p>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <Field label="Game">
          <Select
            className="bg-white text-ink-900"
            value={gameKey}
            onChange={(event) => setGameKey(event.target.value)}
          >
            {quickGames.map((game) => (
              <option key={game.key} value={game.key}>
                {game.name} · {game.typical_minutes} min · {game.energy} energy
              </option>
            ))}
          </Select>
        </Field>
        <div className="flex items-end">
          <Button size="xl" className="w-full" onClick={() => void start()} disabled={startPlay.isPending}>
            {startPlay.isPending ? "Starting..." : "Start the game"}
          </Button>
        </div>
      </div>

      <div className="mt-5 grid gap-2 sm:grid-cols-3">
        {quickGames.slice(0, 6).map((game) => (
          <div key={game.key} className="rounded-xl bg-white/5 p-3 text-sm">
            <p className="font-medium">{game.name}</p>
            <p className="text-white/60">{game.description}</p>
          </div>
        ))}
      </div>
      <p className="mt-4 text-sm text-white/50">
        The host runs the game on this screen. Nobody needs to install anything.
      </p>
    </Card>
  );
}

function CaptureStep({
  sessionId,
  canDrive,
  onOpenCapture,
}: {
  sessionId: string;
  canDrive: boolean;
  onOpenCapture: () => void;
}) {
  const ideas = useIdeas({ session_id: sessionId });
  return (
    <Card className="bg-white/5 text-white">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-3xl font-semibold">💡 What are the ideas?</h2>
        {/* Everyone in the room can add one, which is the point of the step. */}
        <Button size="lg" onClick={onOpenCapture}>
          + Capture an idea
        </Button>
      </div>
      <p className="mt-2 text-white/70">
        {canDrive
          ? "Anyone can add from their phone. This list refreshes by itself."
          : "Add yours from your phone. The room sees it on the shared screen."}
      </p>
      <ul className="mt-5 grid gap-3 sm:grid-cols-2">
        {(ideas.data?.items ?? []).map((idea) => (
          <li key={idea.id} className="rounded-xl bg-white/5 p-4">
            <p className="text-lg">{idea.title}</p>
            <p className="text-sm text-white/50">{idea.author.name}</p>
          </li>
        ))}
        {(ideas.data?.items ?? []).length === 0 ? (
          <li className="text-white/60">Nothing captured yet. Start with one sentence.</li>
        ) : null}
      </ul>
    </Card>
  );
}

function DecideStep({ sessionId, canDrive }: { sessionId: string; canDrive: boolean }) {
  const ideas = useIdeas({ session_id: sessionId });
  const record = useRecordDecision();
  const update = useUpdateIdea();
  const [selected, setSelected] = useState<string | null>(null);
  const [statement, setStatement] = useState("");

  if (!canDrive) {
    return (
      <Card className="bg-white/5 text-white">
        <h2 className="text-3xl font-semibold">🧠 What did we decide?</h2>
        <p className="mt-2 text-white/70">
          The facilitator is recording the agreements. Speak up if something is missing.
        </p>
        <ul className="mt-5 space-y-2">
          {(ideas.data?.items ?? []).map((idea) => (
            <li key={idea.id} className="rounded-xl bg-white/5 p-3 text-lg">
              {idea.title}
            </li>
          ))}
        </ul>
      </Card>
    );
  }

  const openDecide = (ideaId: string, title: string) => {
    setSelected(ideaId);
    setStatement(title);
  };

  return (
    <Card className="bg-white/5 text-white">
      <h2 className="text-3xl font-semibold">🧠 What did we decide?</h2>
      <p className="mt-2 text-white/70">
        Record the agreement, not the discussion. The idea is promoted automatically.
      </p>

      <ul className="mt-5 space-y-3">
        {(ideas.data?.items ?? []).map((idea) => (
          <li key={idea.id} className="rounded-xl bg-white/5 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-lg">{idea.title}</p>
                <p className="text-sm text-white/50">
                  {idea.author.name} · <StatusBadge status={idea.status} />
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  className="text-white hover:bg-white/10"
                  onClick={() =>
                    void update
                      .mutateAsync({ id: idea.id, status: "parked" })
                      .then(() => toast("Parked for later"))
                  }
                >
                  Park
                </Button>
                <Button onClick={() => openDecide(idea.id, idea.title)}>Record decision</Button>
              </div>
            </div>

            {selected === idea.id ? (
              <div className="mt-4 space-y-3 border-t border-white/10 pt-4">
                <Field label="The decision">
                  <Input
                    className="bg-white text-ink-900"
                    value={statement}
                    onChange={(event) => setStatement(event.target.value)}
                  />
                </Field>
                <Button
                  size="lg"
                  disabled={!statement.trim() || record.isPending}
                  onClick={() => {
                    void record
                      .mutateAsync({ statement, session_id: sessionId, idea_id: idea.id })
                      .then(() => {
                        setSelected(null);
                        setStatement("");
                        toast("🧠 Decision saved!");
                      });
                  }}
                >
                  {record.isPending ? "Saving..." : "Save decision"}
                </Button>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </Card>
  );
}

function AssignStep({ sessionId, canDrive }: { sessionId: string; canDrive: boolean }) {
  const participants = useSessionParticipants(sessionId);
  const tasks = useTasks({ session_id: sessionId });
  const createTask = useCreateTask();
  const [title, setTitle] = useState("");
  const [ownerId, setOwnerId] = useState("");
  const [dueDate, setDueDate] = useState("");

  const assigned = tasks.data?.items ?? [];

  if (!canDrive) {
    return (
      <Card className="bg-white/5 text-white">
        <h2 className="text-3xl font-semibold">🎯 Who's got this?</h2>
        <p className="mt-2 text-white/70">The facilitator is assigning owners.</p>
        <ul className="mt-5 space-y-2">
          {assigned.map((task) => (
            <li key={task.id} className="flex items-center justify-between rounded-xl bg-white/5 p-3">
              <span>{task.title}</span>
              <span className="text-sm text-white/70">{task.owner?.name ?? "unassigned"}</span>
            </li>
          ))}
          {assigned.length === 0 ? (
            <li className="text-white/60">No work has been assigned yet.</li>
          ) : null}
        </ul>
      </Card>
    );
  }

  const assign = async () => {
    if (!title.trim() || !ownerId) return;
    await createTask.mutateAsync({
      title: title.trim(),
      owner_id: ownerId,
      status: "in_progress",
      session_id: sessionId,
      due_date: dueDate || null,
    });
    setTitle("");
    setDueDate("");
    toast("🎯 Task assigned!");
  };

  return (
    <Card className="bg-white/5 text-white">
      <h2 className="text-3xl font-semibold">🎯 Who's got this?</h2>
      <p className="mt-2 text-white/70">One owner per task. If it needs two people, name the owner.</p>

      <div className="mt-5 grid gap-3 sm:grid-cols-4">
        <div className="sm:col-span-2">
          <Field label="Task">
            <Input
              className="bg-white text-ink-900"
              value={title}
              placeholder="Draft the notification spec"
              onChange={(event) => setTitle(event.target.value)}
            />
          </Field>
        </div>
        <Field label="Owner">
          <Select
            className="bg-white text-ink-900"
            value={ownerId}
            onChange={(event) => setOwnerId(event.target.value)}
          >
            <option value="">Pick a person</option>
            {(participants.data?.items ?? [])
              .filter((participant) => participant.user_id)
              .map((participant) => (
                <option key={participant.id} value={participant.user_id ?? ""}>
                  {participant.name}
                </option>
              ))}
          </Select>
        </Field>
        <Field label="Due">
          <Input
            className="bg-white text-ink-900"
            type="date"
            value={dueDate}
            onChange={(event) => setDueDate(event.target.value)}
          />
        </Field>
      </div>

      <Button
        size="lg"
        className="mt-3"
        disabled={!title.trim() || !ownerId || createTask.isPending}
        onClick={() => void assign()}
      >
        {createTask.isPending ? "Assigning..." : "Assign it"}
      </Button>

      <ul className="mt-5 space-y-2">
        {assigned.map((task) => (
          <li key={task.id} className="flex items-center justify-between rounded-xl bg-white/5 p-3">
            <span>{task.title}</span>
            <span className="text-sm text-white/70">
              {task.owner?.name ?? "unassigned"}
              {task.due_date ? ` · ${task.due_date}` : ""}
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function CloseStep({ sessionId, canDrive }: { sessionId: string; canDrive: boolean }) {
  const session = useSession(sessionId, 4000);
  const lifecycle = useSessionLifecycle(sessionId);
  const [reopenReason, setReopenReason] = useState("");
  const data = session.data;

  if (!canDrive) {
    return (
      <Card className="bg-white/5 text-white">
        <h2 className="text-3xl font-semibold">🍢 That's a wrap!</h2>
        <p className="mt-2 text-white/70">
          The facilitator is closing the meeting and writing the minutes. You'll be back to normal
          Mshikaki in a moment.
        </p>
      </Card>
    );
  }

  return (
    <Card className="bg-white/5 text-white">
      <h2 className="text-3xl font-semibold">🍢 That's a wrap!</h2>
      <p className="mt-2 text-white/70">
        Closing writes the summary from everything that happened, and releases everybody back to
        normal Mshikaki. Nobody takes minutes.
      </p>

      <dl className="mt-5 grid gap-3 sm:grid-cols-4">
        {[
          ["Ideas", data?.counts.ideas ?? 0],
          ["Decisions", data?.counts.decisions ?? 0],
          ["Tasks", data?.counts.tasks ?? 0],
          ["Games", data?.counts.games ?? 0],
        ].map(([label, value]) => (
          <div key={String(label)} className="rounded-xl bg-white/5 p-4">
            <dt className="text-sm text-white/60">{label}</dt>
            <dd className="text-3xl font-semibold">{value}</dd>
          </div>
        ))}
      </dl>

      {data?.status === "completed" ? (
        <div className="mt-5 space-y-4">
          <p className="text-white/70">
            Closed {formatDateTime(data.ended_at)}. The summary is on the session page.
          </p>
          <ButtonLink to={`/sessions/${sessionId}`} size="lg">
            Read the summary
          </ButtonLink>
          <div className="max-w-md space-y-2 border-t border-white/10 pt-4">
            <Field label="Reopen the meeting" hint="Audited, and it marks the summary stale.">
              <Input
                className="bg-white text-ink-900"
                value={reopenReason}
                placeholder="We are continuing after lunch"
                onChange={(event) => setReopenReason(event.target.value)}
              />
            </Field>
            <Button
              variant="ghost"
              className="text-white hover:bg-white/10"
              disabled={reopenReason.trim().length < 3}
              onClick={() => void lifecycle.reopen.mutateAsync(reopenReason)}
            >
              Reopen
            </Button>
          </div>
        </div>
      ) : (
        <Button
          size="xl"
          className="mt-5"
          disabled={lifecycle.close.isPending}
          onClick={() => void lifecycle.close.mutateAsync()}
        >
          {lifecycle.close.isPending ? "Closing..." : "Close the session and write the summary"}
        </Button>
      )}
    </Card>
  );
}
