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
  useAgenda,
  useContentPacks,
  useDecisions,
  useCreateTask,
  useDeleteNote,
  useGames,
  useIdeas,
  useMe,
  useRecordDecision,
  useSession,
  useSessionLifecycle,
  useDeleteQuestion,
  useSessionNotes,
  useSessionParticipants,
  useSessionQuestions,
  useSuggestQuestion,
  useUpdateQuestion,
  useUpdateNote,
  useStartPlay,
  useTasks,
  useUpdateIdea,
} from "@/api/hooks";
import type { SessionDetail } from "@/api/types";
import { CaptureSheet } from "@/components/CaptureSheet";
import { StartSessionButton } from "@/components/StartSessionButton";
import { StatusBadge } from "@/components/badges";
import { ErrorState, LoadingState } from "@/components/states";
import { toast } from "@/components/toast";
import { Button, ButtonLink, Card, Field, Input, Select } from "@/components/ui/kit";
import { formatDateTime } from "@/lib/dates";
import { cn } from "@/lib/utils";

// The journey is stated in the words a facilitator would use out loud.
const STEPS = [
  { key: "play", label: "🎲 Let's play" },
  { key: "agenda", label: "📋 The agenda" },
  { key: "capture", label: "💡 What are we thinking" },
  { key: "decide", label: "🧠 What did we decide" },
  { key: "assign", label: "🎯 Who's got this" },
  { key: "close", label: "🍢 That's a wrap" },
] as const;
type Step = (typeof STEPS)[number]["key"];

const STAGE_KEYS = STEPS.map((entry) => entry.key) as readonly Step[];

// The agenda carries the meeting now. The three older topic screens stay
// reachable so a meeting already sitting on one is never stranded, but they are
// not part of the walk a facilitator is asked to take.
const MAIN_PATH: readonly Step[] = ["play", "agenda", "close"];

function isStage(value: string | null | undefined): value is Step {
  return Boolean(value) && STAGE_KEYS.includes(value as Step);
}

export function RunModePage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  // Poll while the meeting runs: this is how the room converges on the stage.
  const session = useSession(sessionId, 4000);
  const me = useMe();
  const room = useSessionParticipants(sessionId ?? "");
  const navigate = useNavigate();
  const lifecycle = useSessionLifecycle(sessionId ?? "");
  const [draftStage, setDraftStage] = useState<Step | null>(null);
  const [captureOpen, setCaptureOpen] = useState(false);
  const released = useRef(false);
  const firstStatus = useRef<string | null>(null);

  const data = session.data;
  if (data && firstStatus.current === null) firstStatus.current = data.status;
  // Arrived after the wrap versus watched the wrap happen: the first gets the
  // record to read, the second gets their navigation back.
  const arrivedAfterTheWrap = firstStatus.current === "completed";
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

  // Released: the meeting ended or was cancelled. Only act on data fetched since
  // this page mounted, or a stale cached "planned" bounces the facilitator
  // straight back out of the meeting they just started.
  const settled = session.isFetchedAfterMount;
  useEffect(() => {
    if (!data || released.current || !settled) return;
    if (data.status === "completed" && arrivedAfterTheWrap) return;
    if (data.status === "completed" || data.status === "cancelled") {
      released.current = true;
      toast("🍢 That's a wrap! Back to normal Mshikaki.");
      navigate(`/sessions/${data.id}`, { replace: true });
    }
  }, [data, settled, navigate, arrivedAfterTheWrap]);

  if (session.isPending) return <LoadingState label="Joining the meeting…" />;
  if (session.isError) return <ErrorState error={session.error} />;
  if (!data) return null;

  // A meeting that had already finished when you opened it is a record to read,
  // not a room to run. This is what "Review Run Mode" opens.
  if (data.status === "completed" && arrivedAfterTheWrap) {
    return <MeetingReview session={data} />;
  }

  // A planned meeting is not a live screen. Say so rather than showing steps that
  // cannot do anything yet.
  if (data.status === "planned") {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-ink-900 px-5 text-white">
        <Card className="max-w-lg bg-white/5 text-white">
          <h2 className="text-3xl font-semibold">🍢 Not started yet</h2>
          <p className="mt-2 text-white/70">
            {canDrive
              ? "Start the meeting and the room follows you into Run Mode."
              : "Waiting for the facilitator to start the meeting."}
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            {canDrive ? (
              <StartSessionButton sessionId={data.id} label="Start the meeting →" />
            ) : null}
            <ButtonLink
              to={`/sessions/${data.id}`}
              variant="ghost"
              className="text-white hover:bg-white/10"
            >
              Leave
            </ButtonLink>
          </div>
        </Card>
      </div>
    );
  }

  // The walk the facilitator is actually on. A meeting parked on one of the
  // older topic screens still sees the whole list so it can get back out.
  const walk: readonly Step[] = MAIN_PATH.includes(stage)
    ? MAIN_PATH
    : STEPS.map((entry) => entry.key);
  const index = walk.indexOf(stage);
  const previous = index > 0 ? walk[index - 1] : undefined;
  const next = index >= 0 && index + 1 < walk.length ? walk[index + 1] : undefined;

  const goToStage = (target: Step) => {
    setDraftStage(target);
    lifecycle.setStage.mutate(target);
  };

  return (
    <div className="min-h-dvh bg-ink-900 pb-24 text-white">
      <header className="border-b border-white/10 px-5 py-4">
        <div className="mx-auto flex max-w-5xl flex-wrap items-start justify-between gap-x-4 gap-y-2">
          {/* The title takes the width it can and no more: a long meeting name
              must not push the room's counters off the screen or grow the
              header over the meeting itself. */}
          <div className="min-w-0 flex-1">
            <p className="text-xs tracking-widest text-white/50 uppercase">
              Run Mode
              {data.status === "paused" ? " · paused" : ""}
            </p>
            <h1
              className="line-clamp-2 text-xl font-semibold break-words sm:line-clamp-3 sm:text-2xl"
              title={data.title}
            >
              {data.title}
            </h1>
          </div>
          {/* The pills keep their shape; the row itself is allowed to shrink and
              wrap, or it drags the whole page wider than the phone. */}
          <div className="flex min-w-0 flex-wrap items-center justify-end gap-2 text-sm">
            <span className="rounded-full bg-white/10 px-3 py-1 whitespace-nowrap">
              {room.data?.items.length ?? 0} in the room
            </span>
            <span className="rounded-full bg-white/10 px-3 py-1 whitespace-nowrap">
              {data.counts.ideas} ideas · {data.counts.decisions} decisions · {data.counts.tasks} tasks
            </span>
            <ButtonLink
              to={`/sessions/${data.id}`}
              variant="ghost"
              size="sm"
              className="whitespace-nowrap text-white hover:bg-white/10"
            >
              Leave
            </ButtonLink>
          </div>
        </div>
      </header>

      {canDrive ? null : (
        <p className="mx-auto max-w-5xl px-5 pt-4 text-lg text-white/70">
          You're in <strong className="text-white">{data.title}</strong>
          {data.facilitator ? ` with ${data.facilitator.name}` : ""}. Follow along — the screen
          moves with the room until that's a wrap. 🍢
        </p>
      )}

      <nav className="mx-auto flex max-w-5xl gap-2 px-5 py-4">
        {walk.map((key) => {
          const entry = STEPS.find((item) => item.key === key);
          if (!entry) return null;
          const position = STEPS.findIndex((item) => item.key === key);
          const current = position === index;
          const shared = { key: entry.key, className: "" };
          const classes =
            "flex-1 rounded-xl px-2 py-3 text-xs font-medium whitespace-nowrap sm:px-3 sm:text-sm " +
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
        {stage === "agenda" ? (
          <AgendaStep
            session={data}
            canDrive={canDrive}
            onOpenCapture={() => setCaptureOpen(true)}
          />
        ) : null}
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
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-3 gap-y-2">
            <Button
              variant="ghost"
              className="whitespace-nowrap text-white hover:bg-white/10"
              disabled={!previous}
              onClick={() => previous && goToStage(previous)}
            >
              Back
            </Button>
            <div className="flex flex-wrap items-center justify-end gap-2">
              {data.status === "paused" ? (
                <Button
                  variant="ghost"
                  className="whitespace-nowrap text-white hover:bg-white/10"
                  onClick={() => void lifecycle.resume.mutateAsync()}
                >
                  Resume
                </Button>
              ) : (
                <Button
                  variant="ghost"
                  className="whitespace-nowrap text-white hover:bg-white/10"
                  onClick={() => void lifecycle.pause.mutateAsync()}
                >
                  Pause
                </Button>
              )}
              <Button
                size="lg"
                className="whitespace-nowrap"
                onClick={() => (next ? goToStage(next) : goToStage("close"))}
              >
                {/* On the agenda the room moves item by item, so the footer must
                    not look like it advances one item. It skips to the wrap. */}
                {stage === "agenda"
                  ? "Skip to the wrap"
                  : next
                    ? `Next: ${STEPS.find((item) => item.key === next)?.label}`
                    : "Finish"}
              </Button>
            </div>
          </div>
        </footer>
      ) : null}

      <CaptureSheet
        open={captureOpen}
        onClose={() => setCaptureOpen(false)}
        defaultSessionId={data.id}
        // An idea raised while the room is on an item belongs to that item.
        agendaItemId={stage === "agenda" ? data.current_agenda_item_id : undefined}
      />
    </div>
  );
}

const REVIEW_OUTCOMES: Record<string, string> = {
  accomplished: "done with this",
  pending: "still pending",
  assigned: "someone is taking this",
  none: "nothing decided",
};

/**
 * A meeting that has finished, shown as the record it left behind.

 * Read-only on purpose: the room is gone, and the minutes are the frozen
 * document. This exists so "Review Run Mode" shows the meeting instead of
 * bouncing back to where it came from.
 */
function MeetingReview({ session }: { session: SessionDetail }) {
  const tasks = useTasks({ session_id: session.id });
  const ideas = useIdeas({ session_id: session.id });

  const notesFor = (itemId: string) => session.notes.filter((note) => note.agenda_item_id === itemId);
  const ideasFor = (itemId: string) =>
    (ideas.data?.items ?? []).filter((idea) => idea.agenda_item_id === itemId);
  const actionsFor = (itemId: string) =>
    (tasks.data?.items ?? []).filter((task) => task.origin?.agenda_item_id === itemId);

  const counts: [string, number][] = [
    ["Agenda items", session.agenda.length],
    ["Notes", session.notes.length],
    ["Ideas", session.counts.ideas],
    ["Decisions", session.counts.decisions],
    ["Actions", session.counts.tasks],
  ];

  return (
    <div className="min-h-dvh bg-ink-900 px-4 py-8 text-white">
      <main className="mx-auto max-w-3xl space-y-5">
        <header className="space-y-2">
          <p className="text-xs tracking-widest text-white/50 uppercase">Meeting record</p>
          <h1 className="flex items-center gap-3 text-3xl font-semibold">
            <img src="/mshikaki-mark.png" alt="" aria-hidden className="size-[72px]" />
            {session.title}
          </h1>
          <p className="text-white/70">
            Finished {formatDateTime(session.ended_at)}
            {session.facilitator ? ` · ${session.facilitator.name} facilitated` : ""}
          </p>
        </header>

        <Card className="bg-white/5 text-white">
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            {counts.map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs text-white/50 uppercase">{label}</dt>
                <dd className="text-2xl font-semibold">{value}</dd>
              </div>
            ))}
          </dl>
        </Card>

        {session.agenda.map((item, index) => {
          const notes = notesFor(item.id);
          const ideasHere = ideasFor(item.id);
          const actions = actionsFor(item.id);
          const nothing = notes.length === 0 && ideasHere.length === 0 && actions.length === 0;
          return (
            <Card key={item.id} className="bg-white/5 text-white">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-xl font-semibold">
                  {index + 1}. {item.title}
                </h2>
                <span className="text-sm text-white/60">
                  {item.outcome ? REVIEW_OUTCOMES[item.outcome] : item.covered ? "discussed" : "not reached"}
                </span>
              </div>
              {nothing ? (
                <p className="mt-2 text-sm text-white/50">Nothing was recorded on this item.</p>
              ) : (
                <ul className="mt-3 space-y-2 text-sm">
                  {notes.map((note) => (
                    <li key={note.id} className="rounded-lg bg-white/5 p-2">
                      📝 {note.body}
                    </li>
                  ))}
                  {ideasHere.map((idea) => (
                    <li key={idea.id} className="rounded-lg bg-white/5 p-2">
                      💡 {idea.title} · {idea.status}
                    </li>
                  ))}
                  {actions.map((task) => (
                    <li key={task.id} className="rounded-lg bg-white/5 p-2">
                      🎯 {task.title} · {task.owner?.name ?? "unassigned"} · {task.status}
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          );
        })}

        <Card className="bg-white/5 text-white">
          <div className="flex flex-wrap gap-3">
            <ButtonLink to={`/sessions/${session.id}`} size="lg">
              Open the minutes →
            </ButtonLink>
            <ButtonLink
              href={`/api/sessions/${session.id}/summary.pdf`}
              download
              variant="secondary"
              size="lg"
            >
              🖨️ Download PDF
            </ButtonLink>
            <ButtonLink to="/" variant="ghost" className="text-white hover:bg-white/10">
              Leave
            </ButtonLink>
          </div>
        </Card>
      </main>
    </div>
  );
}

function PlayStep({ session, canDrive }: { session: SessionDetail; canDrive: boolean }) {
  const games = useGames();
  const packs = useContentPacks();
  const startPlay = useStartPlay(session.id);
  const agenda = useAgenda(session.id);
  const navigate = useNavigate();
  const [gameKey, setGameKey] = useState("");
  const [packId, setPackId] = useState("");
  // Remembered across screens: somebody who deliberately steps back out of a
  // game is not dragged in again, but a new game still pulls them in.
  const joinedKey = `mshikaki.joined.${session.id}`;
  const joined = useRef<string | null>(window.sessionStorage.getItem(joinedKey));

  const running = session.games.find((game) => game.status === "running");
  const quickGames = (games.data?.items ?? []).filter((game) => game.typical_minutes <= 15);
  const chosen = quickGames.find((game) => game.key === gameKey) ?? quickGames[0];
  const packsForGame = (packs.data?.items ?? []).filter((pack) => pack.game_key === chosen?.key);
  // A quiz with no questions is an empty room. Ask for the pack here, so the
  // facilitator never has to leave the meeting to start a real game.
  const needsPack = Boolean(chosen) && chosen?.family !== "host_scored";

  useEffect(() => {
    setPackId(packsForGame[0]?.id ?? "");
  }, [chosen?.key, packsForGame.length]);

  // A game that is running is a game everybody plays. Pull each person onto the
  // question screen once per game, so nobody is left looking at a notice while
  // the room is answering.
  useEffect(() => {
    if (canDrive || !running || joined.current === running.id) return;
    joined.current = running.id;
    window.sessionStorage.setItem(joinedKey, running.id);
    navigate(`/play/${running.id}`);
  }, [canDrive, running, navigate, joinedKey]);

  if (!canDrive) {
    return (
      <Card className="bg-white/5 text-white">
        <h2 className="text-3xl font-semibold">🎲 The game</h2>
        {running ? (
          <>
            <p className="mt-3 text-xl text-white/80">
              You're being taken to the question. Answer on your own phone.
            </p>
            <ButtonLink to={`/play/${running.id}`} size="xl" className="mt-4">
              Play now →
            </ButtonLink>
          </>
        ) : (
          <p className="mt-3 text-xl text-white/80">
            The facilitator is choosing a game to warm the room up.
          </p>
        )}
      </Card>
    );
  }

  const start = async () => {
    if (!chosen) return;
    const play = await startPlay.mutateAsync({
      game_key: chosen.key,
      content_pack_id: packId || undefined,
    });
    navigate(`/play/${play.id}`);
  };

  return (
    <Card className="bg-white/5 text-white">
      <h2 className="flex items-center gap-3 text-3xl font-semibold">
        <img src="/mshikaki-mark.png" alt="" aria-hidden className="size-[60px]" />
        Ready to begin?
      </h2>
      <p className="mt-2 max-w-2xl text-white/70">
        Play is the warm-up, not the meeting. Serious meetings can go straight to the agenda.
      </p>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-ember-500/40 bg-ember-500/10 p-4">
          <p className="text-lg font-semibold">🎲 Let's play</p>
          <p className="mt-1 text-sm text-white/70">Warm the room up first.</p>
          <Button
            size="lg"
            className="mt-3 w-full"
            disabled={startPlay.isPending || !quickGames.length}
            onClick={() => void start()}
          >
            {startPlay.isPending ? "Starting..." : "Start the game"}
          </Button>
        </div>
        <div className="rounded-xl border border-white/15 bg-white/5 p-4">
          <p className="text-lg font-semibold">▶️ Start meeting</p>
          <p className="mt-1 text-sm text-white/70">Go straight to the agenda.</p>
          <Button
            size="lg"
            variant="secondary"
            className="mt-3 w-full"
            disabled={agenda.startMeeting.isPending}
            onClick={() =>
              void agenda.startMeeting.mutateAsync().then(() => toast("📋 Meeting started"))
            }
          >
            {agenda.startMeeting.isPending ? "Starting..." : "Start meeting"}
          </Button>
        </div>
      </div>

      <div className="mt-5 rounded-xl border border-white/15 bg-white/5 p-4">
        <p className="text-lg font-semibold">❓ Play the room's questions</p>
        <p className="mt-1 text-sm text-white/70">
          Uses the questions people added during this meeting.
        </p>
        <Button
          size="lg"
          variant="secondary"
          className="mt-3"
          disabled={startPlay.isPending}
          onClick={() =>
            void startPlay
              .mutateAsync({ game_key: "trivia-general", use_session_questions: true })
              .then((play) => navigate(`/play/${play.id}`))
              .catch(() => toast("The room has not written any questions yet"))
          }
        >
          Play their questions
        </Button>
      </div>

      <h3 className="mt-8 text-lg font-semibold text-white/80">Or pick the game yourself</h3>

      {running ? (
        <div className="mt-4 rounded-xl border border-ember-500/40 bg-ember-500/10 p-3">
          <p className="text-sm text-white/80">
            A game is running. The room is in it — go back to the question screen when you are
            ready. Starting another game ends this one for everybody.
          </p>
          <ButtonLink to={`/play/${running.id}`} size="lg" className="mt-2">
            Back to the game →
          </ButtonLink>
        </div>
      ) : null}

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <Field label="Game">
          <Select
            className="bg-white text-ink-900"
            value={chosen?.key ?? ""}
            onChange={(event) => setGameKey(event.target.value)}
          >
            {quickGames.map((game) => (
              <option key={game.key} value={game.key}>
                {game.name} · {game.typical_minutes} min · {game.energy} energy
              </option>
            ))}
          </Select>
        </Field>
        <Field
          label="Questions from"
          hint={needsPack ? "The room answers these on their phones." : "You score this one yourself."}
        >
          <Select
            className="bg-white text-ink-900"
            value={packId}
            onChange={(event) => setPackId(event.target.value)}
            disabled={!needsPack}
          >
            {needsPack ? null : <option value="">No questions — you run it</option>}
            {packsForGame.map((pack) => (
              <option key={pack.id} value={pack.id}>
                {pack.title} · {pack.items} questions
              </option>
            ))}
          </Select>
        </Field>
        <div className="flex items-end">
          <Button
            size="xl"
            className="w-full"
            variant="secondary"
            onClick={() => void start()}
            disabled={!chosen || (needsPack && !packId) || startPlay.isPending}
          >
            {startPlay.isPending ? "Starting..." : "Start this game"}
          </Button>
        </div>
      </div>
      {needsPack && !packId ? (
        <p className="mt-3 text-sm text-red-200">
          Pick a question pack — a quiz with no questions would leave the room waiting.
        </p>
      ) : null}

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

/** How an item ended, said the way a facilitator would say it out loud. */
const OUTCOME_CHOICES = [
  { key: "accomplished", label: "Done with this" },
  { key: "pending", label: "Still pending" },
  { key: "assigned", label: "Someone is taking this" },
  { key: "none", label: "Nothing decided" },
] as const;

const OUTCOME_WORDS: Record<string, string> = Object.fromEntries(
  OUTCOME_CHOICES.map((choice) => [choice.key, choice.label]),
);

/**
 * The agenda step: one item, and everything the room can do with it.

 * This is where a serious meeting lives. The facilitator sets the outcome, can
 * record a decision, can hand one action to one person, and moves on. Everybody
 * else sees the same item and can note or propose something without leaving the
 * meeting. Deliberately not a dashboard: one item, four quiet choices.
 */
function AgendaStep({
  session,
  canDrive,
  onOpenCapture,
}: {
  session: SessionDetail;
  canDrive: boolean;
  onOpenCapture: () => void;
}) {
  const agenda = useAgenda(session.id);
  const addNote = useSessionNotes(session.id);
  const deleteNote = useDeleteNote(session.id);
  const updateNote = useUpdateNote(session.id);
  const updateIdea = useUpdateIdea();
  const questions = useSessionQuestions(session.id);
  const suggestQuestion = useSuggestQuestion(session.id);
  const updateQuestion = useUpdateQuestion(session.id);
  const deleteQuestion = useDeleteQuestion(session.id);
  const record = useRecordDecision();
  const createTask = useCreateTask();
  const participants = useSessionParticipants(session.id);
  const ideas = useIdeas({ session_id: session.id });
  const tasks = useTasks({ session_id: session.id });
  const decisions = useDecisions({ session_id: session.id });

  const [panel, setPanel] = useState<"note" | "decide" | "action" | "question" | null>("note");
  const [note, setNote] = useState("");
  const [questionPrompt, setQuestionPrompt] = useState("");
  const [questionChoices, setQuestionChoices] = useState("");
  const [questionAnswer, setQuestionAnswer] = useState("");
  const [decisionIdeaId, setDecisionIdeaId] = useState("");
  const [actionIdeaId, setActionIdeaId] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [editBody, setEditBody] = useState("");
  const [statement, setStatement] = useState("");
  const [action, setAction] = useState("");
  const [ownerId, setOwnerId] = useState("");

  const item = session.agenda.find((row) => row.is_current) ?? null;
  const position = session.agenda_position;

  if (!item) {
    return (
      <Card className="bg-white/5 text-white">
        <h2 className="text-3xl font-semibold">📋 The agenda</h2>
        {session.agenda.length === 0 ? (
          <p className="mt-3 text-xl text-white/80">
            {canDrive
              ? "This meeting has no agenda items yet. Add them on the session page, then come back."
              : "The facilitator has not set an agenda for this meeting."}
          </p>
        ) : (
          <p className="mt-3 text-xl text-white/80">
            The agenda is finished. {canDrive ? "Wrap the meeting up when you are ready." : "The facilitator will wrap up."}
          </p>
        )}
        {canDrive ? (
          <div className="mt-5 flex flex-wrap gap-3">
            <ButtonLink to={`/sessions/${session.id}`} size="lg">
              Edit the agenda
            </ButtonLink>
            {session.agenda.length > 0 ? (
              <Button
                size="lg"
                disabled={agenda.next.isPending}
                onClick={() => void agenda.next.mutateAsync()}
              >
                That&apos;s a wrap
              </Button>
            ) : null}
          </div>
        ) : null}
      </Card>
    );
  }

  const itemNotes = session.notes.filter((row) => row.agenda_item_id === item.id);
  const itemIdeas = (ideas.data?.items ?? []).filter((idea) => idea.agenda_item_id === item.id);
  const itemActions = (tasks.data?.items ?? []).filter(
    (task) => task.origin?.agenda_item_id === item.id,
  );
  const itemDecisions = (decisions.data?.items ?? []).filter(
    (decision) => decision.agenda_item_id === item.id,
  );
  const people = (participants.data?.items ?? []).filter((person) => person.user_id);
  const progress = position.total > 0 ? (position.position / position.total) * 100 : 0;

  return (
    <>
      <Card className="bg-white/5 text-white">
        <div className="flex items-baseline justify-between gap-4">
          <p className="text-xs tracking-widest text-white/50 uppercase">
            Agenda {position.position} of {position.total}
          </p>
          <p className="text-sm text-white/50">
            {position.remaining === 0 ? "last item" : `${position.remaining} to go`}
          </p>
        </div>
        <div className="mt-2 h-1.5 w-full rounded-full bg-white/10">
          <div className="h-1.5 rounded-full bg-ember-500" style={{ width: `${progress}%` }} />
        </div>

        <h2 className="mt-5 text-3xl leading-tight font-semibold sm:text-4xl">{item.title}</h2>
        <p className="mt-2 text-lg text-white/70">
          {canDrive
            ? "What are we doing with this item?"
            : "The facilitator is leading this item. Add a note or an idea whenever it helps."}
        </p>

        {canDrive ? (
          <div className="mt-5">
            <p className="text-sm text-white/60">How does this item end?</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {OUTCOME_CHOICES.map((choice) => (
                <Button
                  key={choice.key}
                  variant={item.outcome === choice.key ? "primary" : "ghost"}
                  className={item.outcome === choice.key ? "" : "text-white hover:bg-white/10"}
                  disabled={agenda.outcome.isPending}
                  onClick={() =>
                    void agenda.outcome
                      .mutateAsync({ itemId: item.id, outcome: choice.key })
                      .then(() => toast(`📋 ${choice.label}`))
                  }
                >
                  {choice.label}
                </Button>
              ))}
            </div>
          </div>
        ) : item.outcome ? (
          <p className="mt-4 text-white/70">This item ended as: {OUTCOME_WORDS[item.outcome]}</p>
        ) : null}

        <div className="mt-6 flex flex-wrap gap-2">
          <Button
            variant={panel === "question" ? "primary" : "ghost"}
            className={panel === "question" ? "" : "text-white hover:bg-white/10"}
            onClick={() => setPanel(panel === "question" ? null : "question")}
          >
            ❓ Add a question
          </Button>
          <Button
            variant={panel === "note" ? "primary" : "ghost"}
            className={panel === "note" ? "" : "text-white hover:bg-white/10"}
            onClick={() => setPanel(panel === "note" ? null : "note")}
          >
            📝 Add a note
          </Button>
          {canDrive ? (
            <Button
              variant={panel === "decide" ? "primary" : "ghost"}
              className={panel === "decide" ? "" : "text-white hover:bg-white/10"}
              onClick={() => setPanel(panel === "decide" ? null : "decide")}
            >
              🧠 Record a decision
            </Button>
          ) : null}
          {canDrive ? (
            <Button
              variant={panel === "action" ? "primary" : "ghost"}
              className={panel === "action" ? "" : "text-white hover:bg-white/10"}
              onClick={() => setPanel(panel === "action" ? null : "action")}
            >
              🎯 Give someone an action
            </Button>
          ) : null}
          <Button variant="ghost" className="text-white hover:bg-white/10" onClick={onOpenCapture}>
            💡 Add an idea
          </Button>
        </div>

        {panel === "question" ? (
          <div className="mt-4 rounded-xl bg-white/5 p-4">
            <p className="text-sm text-white/60">
              Anybody can add one. Accepted questions can be played straight away.
            </p>
            <div className="mt-3 space-y-3">
              <Field label="The question">
                <Input
                  className="bg-white text-ink-900"
                  value={questionPrompt}
                  placeholder="Which studio opened first?"
                  onChange={(event) => setQuestionPrompt(event.target.value)}
                />
              </Field>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Options" hint="Comma separated, optional.">
                  <Input
                    className="bg-white text-ink-900"
                    value={questionChoices}
                    placeholder="A, B, C, D"
                    onChange={(event) => setQuestionChoices(event.target.value)}
                  />
                </Field>
                <Field label="Right answer" hint="Optional, for a scored question.">
                  <Input
                    className="bg-white text-ink-900"
                    value={questionAnswer}
                    placeholder="A"
                    onChange={(event) => setQuestionAnswer(event.target.value)}
                  />
                </Field>
              </div>
              <Button
                size="lg"
                disabled={questionPrompt.trim().length < 3 || suggestQuestion.isPending}
                onClick={() =>
                  void suggestQuestion
                    .mutateAsync({
                      prompt: questionPrompt.trim(),
                      choices: questionChoices
                        .split(",")
                        .map((choice) => choice.trim())
                        .filter(Boolean),
                      answer: questionAnswer.trim() || undefined,
                      agenda_item_id: item.id,
                    })
                    .then(() => {
                      setQuestionPrompt("");
                      setQuestionChoices("");
                      setQuestionAnswer("");
                      toast("❓ Question added");
                    })
                }
              >
                {suggestQuestion.isPending ? "Adding..." : "Add the question"}
              </Button>
            </div>

            <ul className="mt-4 space-y-2">
              {(questions.data?.items ?? []).map((row) => (
                <li key={row.id} className="rounded-lg bg-white/5 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <span>
                      {row.prompt}
                      {row.answer ? (
                        <span className="ml-2 text-xs text-white/50">answer: {row.answer}</span>
                      ) : null}
                    </span>
                    <span className="text-xs text-white/50">
                      {row.author} · {row.status}
                    </span>
                  </div>
                  {canDrive ? (
                    <div className="mt-2 flex flex-wrap gap-2 text-xs">
                      {["accepted", "rejected"].map((next) => (
                        <button
                          key={next}
                          type="button"
                          className="rounded-full bg-white/10 px-2 py-1 text-white/70 hover:bg-white/20"
                          onClick={() =>
                            void updateQuestion.mutateAsync({ questionId: row.id, status: next })
                          }
                        >
                          {next}
                        </button>
                      ))}
                      <button
                        type="button"
                        className="rounded-full bg-white/10 px-2 py-1 text-white/50 hover:bg-white/20"
                        onClick={() => void deleteQuestion.mutateAsync(row.id)}
                      >
                        remove
                      </button>
                    </div>
                  ) : null}
                </li>
              ))}
              {(questions.data?.items ?? []).length === 0 ? (
                <li className="text-sm text-white/50">No questions from the room yet.</li>
              ) : null}
            </ul>
          </div>
        ) : null}

        {panel === "note" ? (
          <div className="mt-4 rounded-xl bg-white/5 p-4">
            <div className="flex flex-col gap-3 sm:flex-row">
              <Input
                className="bg-white text-ink-900"
                value={note}
                // The placeholder is an example, not a name: say what the field is.
                aria-label="Note for this agenda item"
                placeholder="Finance will confirm the figure tomorrow"
                onChange={(event) => setNote(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && note.trim()) {
                    void addNote
                      .mutateAsync({ body: note.trim(), agenda_item_id: item.id })
                      .then(() => setNote(""));
                  }
                }}
              />
              <Button
                size="lg"
                disabled={!note.trim() || addNote.isPending}
                onClick={() =>
                  void addNote
                    .mutateAsync({ body: note.trim(), agenda_item_id: item.id })
                    .then(() => setNote(""))
                }
              >
                {addNote.isPending ? "Saving..." : "Note it"}
              </Button>
            </div>
            {people.length ? (
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-white/60">
                <span>Give it to somebody:</span>
                {people.map((person) => (
                  <button
                    key={person.id}
                    type="button"
                    className="rounded-full bg-white/10 px-2 py-1 hover:bg-white/20"
                    onClick={() => setNote((value) => `${value.trim()} @${person.name} `.trimStart())}
                  >
                    @{person.name}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {panel === "decide" && canDrive ? (
          <div className="mt-4 rounded-xl bg-white/5 p-4">
            {itemIdeas.length ? (
              <Field label="About which idea?" hint="Optional. It keeps the trail connected.">
                <Select
                  className="bg-white text-ink-900"
                  value={decisionIdeaId}
                  onChange={(event) => setDecisionIdeaId(event.target.value)}
                >
                  <option value="">Not about one idea</option>
                  {itemIdeas.map((idea) => (
                    <option key={idea.id} value={idea.id}>
                      {idea.title}
                    </option>
                  ))}
                </Select>
              </Field>
            ) : null}
            <Field label="The decision" hint="One sentence. The room hears what was agreed.">
              <Input
                className="bg-white text-ink-900"
                value={statement}
                placeholder="Proceed with the website launch plan"
                onChange={(event) => setStatement(event.target.value)}
              />
            </Field>
            <Button
              size="lg"
              className="mt-3"
              disabled={!statement.trim() || record.isPending}
              onClick={() =>
                void record
                  .mutateAsync({
                    statement: statement.trim(),
                    session_id: session.id,
                    agenda_item_id: item.id,
                    idea_id: decisionIdeaId || undefined,
                  })
                  .then(() => {
                    setStatement("");
                    setDecisionIdeaId("");
                    toast("🧠 Decision recorded");
                  })
              }
            >
              {record.isPending ? "Saving..." : "Record it"}
            </Button>
          </div>
        ) : null}

        {panel === "action" && canDrive ? (
          <div className="mt-4 rounded-xl bg-white/5 p-4">
            <p className="text-sm text-white/60">
              Only if it needs doing. One owner, one action. No action is a fine outcome.
            </p>
            {itemIdeas.length ? (
              <Field label="Because of which idea?" hint="Optional.">
                <Select
                  className="bg-white text-ink-900"
                  value={actionIdeaId}
                  onChange={(event) => setActionIdeaId(event.target.value)}
                >
                  <option value="">Nothing in particular</option>
                  {itemIdeas.map((idea) => (
                    <option key={idea.id} value={idea.id}>
                      {idea.title}
                    </option>
                  ))}
                </Select>
              </Field>
            ) : null}
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              <div className="sm:col-span-2">
                <Field label="What needs to happen?">
                  <Input
                    className="bg-white text-ink-900"
                    value={action}
                    placeholder="Prepare the final launch checklist"
                    onChange={(event) => setAction(event.target.value)}
                  />
                </Field>
              </div>
              <Field label="Who?">
                <Select
                  className="bg-white text-ink-900"
                  value={ownerId}
                  onChange={(event) => setOwnerId(event.target.value)}
                >
                  <option value="">Pick a person</option>
                  {people.map((person) => (
                    <option key={person.id} value={person.user_id ?? ""}>
                      {person.name}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <Button
              size="lg"
              className="mt-3"
              disabled={!action.trim() || !ownerId || createTask.isPending}
              onClick={() =>
                void createTask
                  .mutateAsync({
                    title: action.trim(),
                    owner_id: ownerId,
                    status: "in_progress",
                    session_id: session.id,
                    agenda_item_id: item.id,
                    idea_id: actionIdeaId || undefined,
                  })
                  .then(() => {
                    setAction("");
                    setActionIdeaId("");
                    toast("🎯 Action assigned");
                  })
              }
            >
              {createTask.isPending ? "Assigning..." : "Assign it"}
            </Button>
          </div>
        ) : null}

        {itemNotes.length > 0 ||
        itemIdeas.length > 0 ||
        itemActions.length > 0 ||
        itemDecisions.length > 0 ? (
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div>
              <h3 className="text-sm font-semibold text-white/60">Notes on this item</h3>
              <ul className="mt-2 space-y-2">
                {itemNotes.map((row) => (
                  <li key={row.id} className="rounded-xl bg-white/5 p-3">
                    {editing === row.id ? (
                      <div className="flex flex-col gap-2 sm:flex-row">
                        <Input
                          className="bg-white text-ink-900"
                          aria-label="Edit this note"
                          value={editBody}
                          onChange={(event) => setEditBody(event.target.value)}
                        />
                        <Button
                          size="sm"
                          disabled={!editBody.trim() || updateNote.isPending}
                          onClick={() =>
                            void updateNote
                              .mutateAsync({ noteId: row.id, body: editBody })
                              .then(() => setEditing(null))
                          }
                        >
                          Save
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-white hover:bg-white/10"
                          onClick={() => setEditing(null)}
                        >
                          Cancel
                        </Button>
                      </div>
                    ) : (
                      <div className="flex items-start justify-between gap-3">
                        <span>
                          {row.body}
                          {row.edited ? (
                            <span className="ml-2 text-xs text-white/40">edited</span>
                          ) : null}
                        </span>
                        <span className="flex shrink-0 items-center gap-2">
                          <button
                            type="button"
                            className="text-sm text-white/50 hover:text-white"
                            onClick={() => {
                              setEditing(row.id);
                              setEditBody(row.body);
                            }}
                          >
                            edit
                          </button>
                          {canDrive ? (
                            <button
                              type="button"
                              className="text-sm text-white/50 hover:text-white"
                              onClick={() => void deleteNote.mutateAsync(row.id)}
                            >
                              remove
                            </button>
                          ) : null}
                        </span>
                      </div>
                    )}
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5",
                          row.status === "done"
                            ? "bg-emerald-400/20 text-emerald-200"
                            : row.status === "pending"
                              ? "bg-ember-500/20 text-ember-200"
                              : "bg-white/10 text-white/60",
                        )}
                      >
                        {row.status === "open" ? "no state yet" : row.status}
                      </span>
                      {row.assignee_name ? (
                        <span className="text-white/70">👤 {row.assignee_name}</span>
                      ) : null}
                      {canDrive ? (
                        <>
                          <select
                            aria-label="Who has this note"
                            className="rounded-lg bg-white/10 px-2 py-1 text-white"
                            value={row.assignee_id ?? ""}
                            onChange={(event) =>
                              void updateNote.mutateAsync({
                                noteId: row.id,
                                assignee_id: event.target.value || null,
                                clear_assignee: !event.target.value,
                              })
                            }
                          >
                            <option value="">nobody yet</option>
                            {people.map((person) => (
                              <option key={person.id} value={person.user_id ?? ""}>
                                {person.name}
                              </option>
                            ))}
                          </select>
                          <select
                            aria-label="Where this note got to"
                            className="rounded-lg bg-white/10 px-2 py-1 text-white"
                            value={row.status}
                            onChange={(event) =>
                              void updateNote.mutateAsync({
                                noteId: row.id,
                                status: event.target.value,
                              })
                            }
                          >
                            <option value="open">open</option>
                            <option value="pending">pending</option>
                            <option value="done">done</option>
                            <option value="backlog">backlog</option>
                          </select>
                        </>
                      ) : null}
                    </div>
                  </li>
                ))}
                {itemNotes.length === 0 ? (
                  <li className="text-sm text-white/50">Nothing noted yet.</li>
                ) : null}
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white/60">From this item</h3>
              <ul className="mt-2 space-y-2">
                {itemIdeas.map((idea) => (
                  <li key={idea.id} className="rounded-xl bg-white/5 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <span>💡 {idea.title}</span>
                      <span className="shrink-0 text-xs text-white/60">{idea.status}</span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs">
                      {["discussing", "accepted", "parked", "rejected"].map((next) => (
                        <button
                          key={next}
                          type="button"
                          disabled={idea.status === next}
                          className={cn(
                            "rounded-full px-2 py-1",
                            idea.status === next
                              ? "bg-ember-500/30 text-white"
                              : "bg-white/10 text-white/70 hover:bg-white/20",
                          )}
                          onClick={() =>
                            void updateIdea.mutateAsync({ id: idea.id, status: next })
                          }
                        >
                          {next}
                        </button>
                      ))}
                    </div>
                  </li>
                ))}
                {itemDecisions.map((decision) => (
                  <li key={decision.id} className="rounded-xl bg-emerald-400/10 p-3">
                    🧠 {decision.statement}
                  </li>
                ))}
                {itemActions.map((task) => (
                  <li key={task.id} className="rounded-xl bg-white/5 p-3">
                    🎯 {task.title} · {task.owner?.name ?? "unassigned"}
                  </li>
                ))}
                {itemIdeas.length === 0 &&
                itemActions.length === 0 &&
                itemDecisions.length === 0 ? (
                  <li className="text-sm text-white/50">Nothing came out of this item yet.</li>
                ) : null}
              </ul>
            </div>
          </div>
        ) : null}
      </Card>

      {canDrive ? (
        <Card className="mt-4 bg-white/5 text-white">
          <div className="mb-3 flex flex-wrap gap-2">
            {session.agenda.map((row, index) => (
              <button
                key={row.id}
                type="button"
                aria-current={row.is_current ? "step" : undefined}
                className={cn(
                  "rounded-full px-3 py-1 text-sm",
                  row.is_current
                    ? "bg-ember-500 text-ink-900"
                    : row.covered
                      ? "bg-white/5 text-white/40"
                      : "bg-white/10 text-white/70 hover:bg-white/20",
                )}
                onClick={() => void agenda.jumpTo.mutateAsync(row.id)}
              >
                {index + 1}. {row.title}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-white/70">
              {position.is_last
                ? "That was the last item. Close the meeting and the minutes write themselves."
                : "Move the room to the next item when this one is done."}
            </p>
            <Button
              variant="ghost"
              className="text-white hover:bg-white/10"
              disabled={position.position <= 1 || agenda.jumpTo.isPending}
              onClick={() => {
                const earlier = session.agenda[position.position - 2];
                if (earlier) void agenda.jumpTo.mutateAsync(earlier.id);
              }}
            >
              ← Previous
            </Button>
            <Button
              size="xl"
              disabled={agenda.next.isPending}
              onClick={() => void agenda.next.mutateAsync()}
            >
              {agenda.next.isPending
                ? "Moving..."
                : position.is_last
                  ? "That's a wrap"
                  : "Next agenda →"}
            </Button>
          </div>
        </Card>
      ) : null}
    </>
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
      <h2 className="flex items-center gap-3 text-3xl font-semibold">
        <img src="/mshikaki-mark.png" alt="" aria-hidden className="size-[72px]" />
        That's a wrap!
      </h2>
      <p className="mt-2 text-white/70">
        Closing writes the summary from everything that happened, and releases everybody back to
        normal Mshikaki. Nobody takes minutes.
      </p>

      <dl className="mt-5 grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {[
          ["Agenda items", data?.agenda.length ?? 0],
          ["Notes", data?.notes.length ?? 0],
          ["Ideas", data?.counts.ideas ?? 0],
          ["Decisions", data?.counts.decisions ?? 0],
          ["Actions", data?.counts.tasks ?? 0],
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
