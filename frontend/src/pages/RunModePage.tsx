/**
 * Run Mode: the room's screen.

 * Screen-first by design - large type, one action per step, readable from three
 * metres. The facilitator drives; the room talks. Capture always works from a
 * phone regardless of what this screen is showing.
 */

import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  useCreateTask,
  useGames,
  useIdeas,
  useRecordDecision,
  useSession,
  useSessionLifecycle,
  useSessionParticipants,
  useStartPlay,
  useTasks,
  useUpdateIdea,
} from "@/api/hooks";
import { CaptureSheet } from "@/components/CaptureSheet";
import { StatusBadge } from "@/components/badges";
import { LoadingState, ErrorState } from "@/components/states";
import { toast } from "@/components/toast";
import { Button, Card, Field, Input, Select } from "@/components/ui/kit";
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

export function RunModePage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const session = useSession(sessionId);
  const lifecycle = useSessionLifecycle(sessionId ?? "");
  const [step, setStep] = useState<Step>("play");
  const [captureOpen, setCaptureOpen] = useState(false);

  if (session.isPending) return <LoadingState />;
  if (session.isError) return <ErrorState error={session.error} />;
  if (!session.data) return null;

  const data = session.data;
  const index = STEPS.findIndex((entry) => entry.key === step);

  return (
    <div className="min-h-dvh bg-ink-900 pb-24 text-white">
      <header className="border-b border-white/10 px-5 py-4">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs tracking-widest text-white/50 uppercase">Run Mode</p>
            <h1 className="text-2xl font-semibold">{data.title}</h1>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="rounded-full bg-white/10 px-3 py-1">
              {data.counts.ideas} ideas · {data.counts.decisions} decisions · {data.counts.tasks} tasks
            </span>
            <Link to={`/sessions/${data.id}`}>
              <Button variant="ghost" size="sm" className="text-white hover:bg-white/10">
                Leave
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <nav className="mx-auto flex max-w-5xl gap-2 px-5 py-4">
        {STEPS.map((entry, position) => (
          <button
            key={entry.key}
            type="button"
            onClick={() => setStep(entry.key)}
            className={
              "flex-1 rounded-xl px-3 py-3 text-sm font-medium " +
              (position === index
                ? "bg-ember-500 text-ink-900"
                : "bg-white/10 text-white/70 hover:bg-white/20")
            }
          >
            {entry.label}
          </button>
        ))}
      </nav>

      <main className="mx-auto max-w-5xl px-5">
        {step === "play" ? <PlayStep sessionId={data.id} /> : null}
        {step === "capture" ? (
          <CaptureStep sessionId={data.id} onOpenCapture={() => setCaptureOpen(true)} />
        ) : null}
        {step === "decide" ? <DecideStep sessionId={data.id} /> : null}
        {step === "assign" ? <AssignStep sessionId={data.id} /> : null}
        {step === "close" ? <CloseStep sessionId={data.id} /> : null}
      </main>

      <footer className="fixed inset-x-0 bottom-0 border-t border-white/10 bg-ink-900/95 px-5 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3">
          <Button
            variant="ghost"
            className="text-white hover:bg-white/10"
            disabled={index === 0}
            onClick={() => setStep(STEPS[Math.max(0, index - 1)]?.key ?? "play")}
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
            ) : null}
            {data.status === "active" ? (
              <Button
                variant="ghost"
                className="text-white hover:bg-white/10"
                onClick={() => void lifecycle.pause.mutateAsync()}
              >
                Pause
              </Button>
            ) : null}
            <Button
              size="lg"
              onClick={() =>
                setStep(STEPS[Math.min(STEPS.length - 1, index + 1)]?.key ?? "close")
              }
            >
              {index === STEPS.length - 1
                ? "Finish"
                : `Next: ${STEPS[index + 1]?.label ?? ""}`}
            </Button>
          </div>
        </div>
      </footer>

      <CaptureSheet
        open={captureOpen}
        onClose={() => setCaptureOpen(false)}
        defaultSessionId={data.id}
      />
    </div>
  );
}

function PlayStep({ sessionId }: { sessionId: string }) {
  const games = useGames();
  const startPlay = useStartPlay(sessionId);
  const navigate = useNavigate();
  const [gameKey, setGameKey] = useState("");

  const quickGames = (games.data?.items ?? []).filter((game) => game.typical_minutes <= 15);

  const start = async () => {
    const pick = gameKey || quickGames[0]?.key;
    if (!pick) return;
    const play = await startPlay.mutateAsync({ game_key: pick });
    navigate(`/play/${play.id}`);
  };

  return (
    <Card className="bg-white/5 text-white">
      <h2 className="text-3xl font-semibold">Warm up the room</h2>
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
  onOpenCapture,
}: {
  sessionId: string;
  onOpenCapture: () => void;
}) {
  const ideas = useIdeas({ session_id: sessionId });
  return (
    <Card className="bg-white/5 text-white">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-3xl font-semibold">What are the ideas?</h2>
        <Button size="lg" onClick={onOpenCapture}>
          + Capture an idea
        </Button>
      </div>
      <p className="mt-2 text-white/70">
        Anyone can add from their phone. This list refreshes by itself.
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

function DecideStep({ sessionId }: { sessionId: string }) {
  const ideas = useIdeas({ session_id: sessionId });
  const record = useRecordDecision();
  const update = useUpdateIdea();
  const [selected, setSelected] = useState<string | null>(null);
  const [statement, setStatement] = useState("");

  const openDecide = (ideaId: string, title: string) => {
    setSelected(ideaId);
    setStatement(title);
  };

  return (
    <Card className="bg-white/5 text-white">
      <h2 className="text-3xl font-semibold">What did we decide?</h2>
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
                  onClick={() => void update.mutateAsync({ id: idea.id, status: "parked" })}
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

function AssignStep({ sessionId }: { sessionId: string }) {
  const participants = useSessionParticipants(sessionId);
  const tasks = useTasks({ session_id: sessionId });
  const createTask = useCreateTask();
  const [title, setTitle] = useState("");
  const [ownerId, setOwnerId] = useState("");
  const [dueDate, setDueDate] = useState("");

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
  };

  return (
    <Card className="bg-white/5 text-white">
      <h2 className="text-3xl font-semibold">Who is doing what?</h2>
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
        {(tasks.data?.items ?? []).map((task) => (
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

function CloseStep({ sessionId }: { sessionId: string }) {
  const session = useSession(sessionId);
  const lifecycle = useSessionLifecycle(sessionId);
  const [reopenReason, setReopenReason] = useState("");
  const data = session.data;

  return (
    <Card className="bg-white/5 text-white">
      <h2 className="text-3xl font-semibold">🎉 That's a wrap!</h2>
      <p className="mt-2 text-white/70">
        Closing writes the summary from everything that happened. Nobody takes minutes.
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
          <Link to={`/sessions/${sessionId}`}>
            <Button size="lg">Read the summary</Button>
          </Link>
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
          onClick={() =>
            void lifecycle.close.mutateAsync().then(() => toast("🎉 Session wrapped up!"))
          }
        >
          {lifecycle.close.isPending ? "Closing..." : "Close the session and write the summary"}
        </Button>
      )}
    </Card>
  );
}
