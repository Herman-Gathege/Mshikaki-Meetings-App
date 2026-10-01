/**
 * Play: the library, the start sheet, and the game itself.

 * One question is live for the whole room at once. The facilitator's screen is
 * the projector; everybody else answers on their own phone. The clock lives on
 * the server, so it is the same for the host, for the person who answers in two
 * seconds and for the person who is still deciding - answering never stops it.

 * The lifecycle is: question -> options and a shared timer -> each player locks
 * an answer in -> reveal -> points -> next -> results -> back into the meeting.
 */

import { type ReactNode, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  useContentPacks,
  useGameActions,
  useGames,
  useMe,
  usePlay,
  useSessionLeaderboard,
  useSessionLifecycle,
  useSessionPlayers,
  useSessions,
  useStartPlay,
} from "@/api/hooks";
import type { GamePlay, Standing } from "@/api/types";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/states";
import { Button, ButtonLink, Card, Field, Input, Modal, Select } from "@/components/ui/kit";
import { cn } from "@/lib/utils";

export function PlayPage() {
  const games = useGames();
  const [startOpen, setStartOpen] = useState(false);

  return (
    <>
      <PageHeader
        title="🎲 Play"
        subtitle="Games are the warm-up, not the work. Nothing here is work-related on purpose."
        actions={<Button size="lg" onClick={() => setStartOpen(true)}>Let's play</Button>}
      />

      {games.isPending ? <LoadingState label="Getting the games ready…" /> : null}
      {games.isError ? <ErrorState error={games.error} /> : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {(games.data?.items ?? []).map((game) => (
          <Card key={game.key} className="flex flex-col gap-2">
            <div className="flex items-start justify-between gap-2">
              <h2 className="font-medium">{game.name}</h2>
              <span className="rounded-full bg-ink-100 px-2 py-0.5 text-xs">
                {game.typical_minutes} min
              </span>
            </div>
            <p className="text-sm text-ink-600">{game.description}</p>
            <p className="mt-auto text-xs text-ink-600">{game.how_to_play}</p>
          </Card>
        ))}
      </div>

      <StartGameModal open={startOpen} onClose={() => setStartOpen(false)} />
    </>
  );
}

function StartGameModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const sessions = useSessions();
  const games = useGames();
  const packs = useContentPacks();
  const [sessionId, setSessionId] = useState("");
  const [gameKey, setGameKey] = useState("");
  const [packId, setPackId] = useState("");
  const start = useStartPlay(sessionId);
  const lifecycle = useSessionLifecycle(sessionId);
  const navigate = useNavigate();

  const ORDER: Record<string, number> = { active: 0, paused: 1, planned: 2 };
  const selectable = (sessions.data?.items ?? [])
    .filter((session) => session.status in ORDER)
    .sort((a, b) => (ORDER[a.status] ?? 9) - (ORDER[b.status] ?? 9));
  const selected = selectable.find((session) => session.id === sessionId);
  const notStarted = selected?.status === "planned";

  const chosenGame = (games.data?.items ?? []).find((game) => game.key === gameKey);
  const packsForGame = (packs.data?.items ?? []).filter((pack) => pack.game_key === gameKey);
  const packRequired = Boolean(chosenGame) && chosenGame?.family !== "host_scored";

  useEffect(() => {
    setPackId(packsForGame[0]?.id ?? "");
  }, [gameKey, packsForGame.length]);

  return (
    <Modal open={open} title="🎲 Let's play" onClose={onClose}>
      <div className="space-y-4">
        <Field label="Which meeting?">
          <Select value={sessionId} onChange={(event) => setSessionId(event.target.value)}>
            <option value="">Pick a meeting</option>
            {selectable.map((session) => (
              <option key={session.id} value={session.id}>
                {session.title} · {session.status}
              </option>
            ))}
          </Select>
        </Field>
        {selectable.length === 0 ? (
          <p className="text-sm text-ink-600">
            Nothing is scheduled yet. Plan one from{" "}
            <Link className="underline" to="/sessions">
              Sessions
            </Link>
            .
          </p>
        ) : null}
        {notStarted ? (
          <div className="rounded-lg border border-ember-500/40 bg-ember-500/10 p-3">
            <p className="text-sm text-ink-800">
              <strong>{selected?.title}</strong> has not been started yet. Start it so the game
              results land in the right meeting.
            </p>
            <Button
              size="sm"
              className="mt-2"
              disabled={lifecycle.start.isPending}
              onClick={() => void lifecycle.start.mutateAsync()}
            >
              {lifecycle.start.isPending ? "Starting…" : "Start this meeting"}
            </Button>
          </div>
        ) : null}

        <Field label="Which game?">
          <Select value={gameKey} onChange={(event) => setGameKey(event.target.value)}>
            <option value="">Pick a game</option>
            {(games.data?.items ?? []).map((game) => (
              <option key={game.key} value={game.key}>
                {game.name} · {game.typical_minutes} min
              </option>
            ))}
          </Select>
        </Field>

        <Field
          label="Questions from"
          hint="Everybody answers on their own phone. The host screen shows the question and the clock."
        >
          <Select value={packId} onChange={(event) => setPackId(event.target.value)}>
            {packRequired ? (
              <option value="">Pick a pack</option>
            ) : (
              <option value="">No pack (you run it and enter the scores)</option>
            )}
            {packsForGame.map((pack) => (
              <option key={pack.id} value={pack.id}>
                {pack.title} · {pack.items} items
              </option>
            ))}
          </Select>
        </Field>
        {packRequired && !packId ? (
          <p className="text-sm text-red-700">
            This game asks questions, so it needs a pack to ask them from.
          </p>
        ) : null}

        <Button
          size="xl"
          className="w-full"
          disabled={!sessionId || !gameKey || (packRequired && !packId) || start.isPending}
          onClick={() =>
            void start
              .mutateAsync({ game_key: gameKey, content_pack_id: packId || undefined })
              .then((play) => navigate(`/play/${play.id}`))
          }
        >
          {start.isPending ? "Getting ready…" : "Start the game"}
        </Button>
      </div>
    </Modal>
  );
}

/** The answer counts as right if it matches, or if the answer line begins with it. */
function choiceMatches(choice: string, answer: string | null): boolean {
  if (!answer) return false;
  const clean = answer.trim().toLowerCase();
  const picked = choice.trim().toLowerCase();
  return (
    clean === picked || clean.startsWith(picked) || picked.startsWith(clean.split(" - ")[0] ?? clean)
  );
}

export function GamePlayPage() {
  const { playId } = useParams<{ playId: string }>();
  const play = usePlay(playId);
  const me = useMe();
  const actions = useGameActions(playId ?? "");

  if (play.isPending) return <LoadingState label="Getting the game ready…" />;
  if (play.isError) return <ErrorState error={play.error} onRetry={() => play.refetch()} />;
  if (!play.data) return null;
  const data = play.data;

  const role = me.data?.role;
  const canDrive = Boolean(
    data.host_id === me.data?.user.id || role === "owner" || role === "admin",
  );

  if (data.total === 0 && data.game.family !== "host_scored") {
    if (!canDrive) {
      return (
        <PlayerShell data={data}>
          <Card className="bg-white/5 text-center text-white">
            <p className="text-5xl">🎲</p>
            <h1 className="mt-3 text-3xl font-semibold">Waiting for the questions</h1>
            <p className="mt-2 text-white/70">
              This game came without questions. The facilitator will sort that out.
            </p>
          </Card>
        </PlayerShell>
      );
    }
    return (
      <main className="mx-auto max-w-2xl p-6">
        <PageHeader title={data.game.name} subtitle="This game has no questions loaded" />
        <EmptyState
          title="No questions came with this game"
          body="Quiz and prompt games read their questions from a pack. Start it again and choose a pack, and the questions will appear one at a time."
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <ButtonLink to="/play" size="lg">
                Start again with a pack
              </ButtonLink>
              <Button variant="outline" onClick={() => void actions.finish.mutateAsync()}>
                Finish without scoring
              </Button>
            </div>
          }
        />
      </main>
    );
  }

  if (data.status === "finished") return <ResultsScreen data={data} />;

  return canDrive ? <HostScreen data={data} /> : <PlayerScreen data={data} />;
}

/**
 * The room's clock, drawn from the server's answer.

 * Every poll re-syncs to `seconds_left`, and the local tick only fills the gap
 * between two polls. Nothing a player does stops it: their own answer, or
 * anybody else's, must never freeze the room.
 */
function useLiveClock(data: GamePlay): number {
  const server = data.question?.seconds_left ?? 0;
  const revealed = Boolean(data.question?.revealed);
  const [left, setLeft] = useState(server);

  useEffect(() => setLeft(server), [server]);

  useEffect(() => {
    if (revealed) return;
    const tick = setInterval(() => setLeft((value) => Math.max(0, value - 1)), 1000);
    return () => clearInterval(tick);
  }, [revealed, data.id, data.index]);

  return left;
}

/** The options wear different colours so a glance is enough to find yours. */
const OPTION_TONES = [
  "border-ember-500/60 bg-ember-500/10",
  "border-nile-500/60 bg-nile-500/10",
  "border-emerald-400/60 bg-emerald-400/10",
  "border-violet-400/60 bg-violet-400/10",
];

function Timer({ left, className }: { left: number; className?: string }) {
  const out = left <= 0;
  return (
    <div
      role="timer"
      aria-live="off"
      className={cn(
        "shrink-0 rounded-2xl px-5 py-3 text-center",
        out ? "bg-red-500/20 text-red-200" : "bg-ember-500 text-ink-900",
        className,
      )}
    >
      <span className="block text-3xl font-bold tabular-nums">{out ? "⏰" : left}</span>
      <span className="text-xs">{out ? "Time!" : "seconds"}</span>
    </div>
  );
}

function ScoreChip({ data }: { data: GamePlay }) {
  const me = useMe();
  const mine = data.scores.find((row) => row.user_id === me.data?.user.id);
  return (
    <span className="rounded-full bg-white/10 px-3 py-1 text-sm">
      {mine ? `You: ${mine.points} points` : "You: no points yet"}
    </span>
  );
}

// --- the player's phone ---------------------------------------------------------

function PlayerShell({ data, children }: { data: GamePlay; children: ReactNode }) {
  return (
    <div className="min-h-dvh bg-ink-900 px-4 py-6 text-white">
      <main className="mx-auto max-w-2xl space-y-4">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs tracking-widest text-white/50 uppercase">
              Playing · {data.pack?.title ?? data.game.name}
            </p>
            <h1 className="text-xl font-semibold">{data.game.name}</h1>
          </div>
          <div className="flex items-center gap-2">
            {data.total > 0 ? (
              <span className="rounded-full bg-white/10 px-3 py-1 text-sm">
                {data.index + 1} of {data.total}
              </span>
            ) : null}
            <ScoreChip data={data} />
            <ButtonLink
              to={`/sessions/${data.session_id}/run`}
              variant="ghost"
              size="sm"
              className="text-white hover:bg-white/10"
            >
              Back
            </ButtonLink>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}

function PlayerScreen({ data }: { data: GamePlay }) {
  const actions = useGameActions(data.id);
  const question = data.question;
  const left = useLiveClock(data);
  const mine = data.you.answer;
  const revealed = Boolean(question?.revealed);
  const ranOut = left <= 0;

  if (!question) {
    return (
      <PlayerShell data={data}>
        <Card className="bg-white/5 text-center text-white">
          <p className="text-5xl">🍢</p>
          <h1 className="mt-3 text-3xl font-semibold">You're in. Hang on…</h1>
          <p className="mt-2 text-white/70">
            The facilitator is getting the game ready. The first question appears here by
            itself.
          </p>
        </Card>
      </PlayerShell>
    );
  }

  const choices = question.choices ?? [];
  const canAnswer = Boolean(mine) === false && !revealed && !ranOut && choices.length > 0;
  const isCorrect = mine !== null && choiceMatches(mine, question.answer);
  const isLast = data.total > 0 && data.index + 1 >= data.total;

  return (
    <PlayerShell data={data}>
      <Card className="bg-white/5 text-white">
        <div className="flex items-start justify-between gap-4">
          <h2 className="text-2xl leading-snug font-semibold">{question.prompt}</h2>
          {choices.length > 0 && !revealed ? <Timer left={left} /> : null}
        </div>

        {choices.length > 0 ? (
          <ul className="mt-5 grid gap-3" aria-label="Answer options">
            {choices.map((choice, index) => {
              const picked = mine === choice;
              const correctOne = revealed && choiceMatches(choice, question.answer);
              return (
                <li key={choice}>
                  <button
                    type="button"
                    aria-pressed={picked}
                    disabled={!canAnswer || actions.answer.isPending}
                    onClick={() => void actions.answer.mutateAsync({ choice })}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-xl border-2 p-4 text-left text-lg transition-colors",
                      correctOne
                        ? "border-emerald-400 bg-emerald-400/25"
                        : picked
                          ? revealed && !isCorrect
                            ? "border-red-400 bg-red-400/25"
                            : "border-emerald-400 bg-emerald-400/20"
                          : OPTION_TONES[index % OPTION_TONES.length],
                      !canAnswer && !picked && !correctOne ? "opacity-60" : "",
                      canAnswer ? "hover:brightness-125" : "",
                    )}
                  >
                    <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-white/15 font-semibold">
                      {String.fromCharCode(65 + index)}
                    </span>
                    <span>{choice}</span>
                    {picked ? <span className="ml-auto text-sm">Your answer</span> : null}
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="mt-5 text-lg text-white/70">
            Answer out loud — the facilitator scores this one.
          </p>
        )}

        {mine && !revealed ? (
          <p className="mt-5 rounded-xl bg-emerald-400/15 p-3 text-lg text-emerald-200">
            ✅ Locked in: <strong>{mine}</strong>. The clock keeps running for everybody else —
            watch the big screen.
          </p>
        ) : null}
        {!mine && ranOut && !revealed ? (
          <p className="mt-5 rounded-xl bg-red-500/15 p-3 text-lg text-red-200">
            ⏰ Time! Nothing was locked in this round.
          </p>
        ) : null}
        {revealed ? (
          <div className="mt-5 space-y-2">
            <p className="text-2xl font-semibold">
              {!mine ? "No answer this round" : isCorrect ? "✅ Correct!" : "❌ Not quite!"}
            </p>
            <p className="text-xl">
              The answer: <strong>{question.answer ?? "—"}</strong>
            </p>
            {question.explanation ? <p className="text-white/70">{question.explanation}</p> : null}
            {!isLast ? (
              <p className="text-white/60">Waiting for the next question…</p>
            ) : (
              <p className="text-white/60">Waiting for the results…</p>
            )}
          </div>
        ) : null}
      </Card>
    </PlayerShell>
  );
}

// --- the facilitator's screen ---------------------------------------------------

function HostScreen({ data }: { data: GamePlay }) {
  const actions = useGameActions(data.id);
  const players = useSessionPlayers(data.session_id);
  const [lastAward, setLastAward] = useState<string | null>(null);
  const question = data.question;
  const choices = question?.choices ?? [];
  const left = useLiveClock(data);
  const revealed = Boolean(question?.revealed);
  const ranOut = left <= 0;
  const hasAnswer = Boolean(question?.answer);
  const isLast = data.total > 0 && data.index + 1 >= data.total;
  const everyoneIsIn = data.answered.of > 0 && data.answered.count >= data.answered.of;
  const roomIsDone = ranOut || everyoneIsIn;

  useEffect(() => setLastAward(null), [data.index, data.id]);

  if (!question) {
    return (
      <div className="min-h-dvh bg-ink-900 px-4 py-6 text-white">
        <main className="mx-auto max-w-3xl">
          <Card className="bg-white/5 text-center text-white">
            <h1 className="text-3xl font-semibold">{data.game.name}</h1>
            <p className="mt-2 text-white/70">That was the last question.</p>
            <Button size="xl" className="mt-5" onClick={() => void actions.finish.mutateAsync()}>
              See the results →
            </Button>
          </Card>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-ink-900 px-4 py-6 text-white">
      <main className="mx-auto max-w-4xl space-y-5">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs tracking-widest text-white/50 uppercase">
              {data.pack?.title ?? data.game.name}
              {question.category ? ` · ${question.category}` : ""}
            </p>
            <h1 className="text-2xl font-semibold sm:text-3xl">{data.game.name}</h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="rounded-full bg-white/10 px-4 py-2 text-lg font-medium">
              Question {data.index + 1} of {data.total}
            </span>
            <ButtonLink
              to={`/sessions/${data.session_id}/run`}
              variant="ghost"
              className="text-white hover:bg-white/10"
            >
              Leave game
            </ButtonLink>
          </div>
        </header>

        <Card className="bg-white/5 text-white">
          <div className="flex items-start justify-between gap-4">
            <h2 className="text-2xl leading-snug font-semibold sm:text-4xl">{question.prompt}</h2>
            {choices.length > 0 && !revealed ? <Timer left={left} /> : null}
          </div>

          <p className="mt-3 text-lg text-white/70">
            {choices.length > 0
              ? revealed
                ? `The room answered on their phones — ${data.answered.count} of ${data.answered.of} locked in an answer.`
                : `${data.answered.count} of ${data.answered.of} have answered. The clock is still running for the rest.`
              : (data.game.how_to_play ?? "The room answers out loud. Score it below.")}
          </p>

          {choices.length > 0 ? (
            <ul className="mt-5 grid gap-3 sm:grid-cols-2" aria-label="Answer options">
              {choices.map((choice, index) => {
                const correctOne = revealed && choiceMatches(choice, question.answer);
                return (
                  <li key={choice}>
                    <div
                      className={cn(
                        "flex w-full items-center gap-3 rounded-xl border-2 p-4 text-left text-lg",
                        correctOne
                          ? "border-emerald-400 bg-emerald-400/20"
                          : OPTION_TONES[index % OPTION_TONES.length],
                        revealed && !correctOne ? "opacity-60" : "",
                      )}
                    >
                      <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-white/15 font-semibold">
                        {String.fromCharCode(65 + index)}
                      </span>
                      <span>{choice}</span>
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : null}

          {hasAnswer && !revealed ? (
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <Button size="xl" onClick={() => void actions.reveal.mutateAsync()}>
                {roomIsDone ? "Reveal the answer" : "Skip to the answer"}
              </Button>
              <span className="text-white/60">
                {ranOut
                  ? "Time is up."
                  : everyoneIsIn
                    ? "Everybody is in."
                    : `${data.answered.of - data.answered.count} still thinking — ${left}s left.`}
              </span>
            </div>
          ) : null}
          {!hasAnswer && choices.length === 0 ? (
            <p className="mt-5 text-lg text-white/70">
              Read the card aloud, give the room a moment, then score whoever answered well and
              move on.
            </p>
          ) : null}
          {revealed && hasAnswer ? (
            <div className="mt-5 space-y-3">
              <p className="text-2xl font-semibold">The answer</p>
              <p className="text-xl">
                <strong>{question.answer}</strong>
              </p>
              {question.explanation ? (
                <p className="text-white/70">{question.explanation}</p>
              ) : null}
            </div>
          ) : null}
        </Card>

        <Card className="bg-white/5 text-white">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-white/70">
              {revealed && hasAnswer ? "Scored automatically" : "Scores"}
            </h2>
            {lastAward ? <span className="text-sm text-emerald-300">{lastAward}</span> : null}
          </div>
          <ul className="grid gap-2 sm:grid-cols-2">
            {(players.data?.items ?? []).map((player) => {
              const key = player.user_id ?? player.guest_id ?? player.name;
              const score = data.scores.find(
                (row) => row.user_id === player.user_id && row.guest_id === player.guest_id,
              );
              return (
                <li
                  key={key}
                  className="flex items-center justify-between gap-2 rounded-xl bg-white/5 p-3"
                >
                  <span className="truncate">
                    {player.name}
                    <span className="ml-2 text-white/50">{score?.points ?? 0}</span>
                  </span>
                  {/* A quiz question scores itself. Prompt decks keep the host's taps. */}
                  {hasAnswer ? null : (
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        disabled={actions.score.isPending}
                        onClick={() =>
                          void actions.score
                            .mutateAsync({
                              user_id: player.user_id ?? undefined,
                              guest_id: player.guest_id ?? undefined,
                              points: 10,
                            })
                            .then(() => setLastAward(`+10 for ${player.name}`))
                        }
                      >
                        +10
                      </Button>
                      <FixScoreButton
                        playId={data.id}
                        user_id={player.user_id ?? undefined}
                        guest_id={player.guest_id ?? undefined}
                        name={player.name}
                      />
                    </div>
                  )}
                </li>
              );
            })}
          </ul>

          <div className="mt-5 flex flex-wrap gap-3">
            <Button
              variant="ghost"
              className="text-white hover:bg-white/10"
              onClick={() => void actions.previous.mutateAsync()}
            >
              ← Back
            </Button>
            {hasAnswer && !revealed ? null : isLast ? (
              <Button size="xl" onClick={() => void actions.finish.mutateAsync()}>
                See results →
              </Button>
            ) : (
              <Button size="xl" onClick={() => void actions.next.mutateAsync()}>
                Next question →
              </Button>
            )}
            <Button
              variant="ghost"
              className="text-white hover:bg-white/10"
              onClick={() => void actions.finish.mutateAsync()}
            >
              End the game
            </Button>
          </div>
        </Card>
      </main>
    </div>
  );
}

/** Correcting a score is allowed, and the reason is recorded. */
function FixScoreButton({
  playId,
  user_id,
  guest_id,
  name,
}: {
  playId: string;
  user_id?: string;
  guest_id?: string;
  name: string;
}) {
  const actions = useGameActions(playId);
  const [open, setOpen] = useState(false);
  const [points, setPoints] = useState("10");
  const [reason, setReason] = useState("");

  return (
    <>
      <Button
        size="sm"
        variant="ghost"
        className="text-white hover:bg-white/10"
        onClick={() => setOpen(true)}
      >
        Fix
      </Button>
      <Modal open={open} title={`Correct ${name}'s score`} onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <Field label="Score">
            <Input
              inputMode="numeric"
              value={points}
              onChange={(event) => setPoints(event.target.value)}
            />
          </Field>
          <Field label="Why?" hint="Recorded in the trail so nobody has to remember.">
            <Input value={reason} onChange={(event) => setReason(event.target.value)} />
          </Field>
          <Button
            disabled={reason.trim().length < 3 || actions.override.isPending}
            onClick={() =>
              void actions
                .override
                .mutateAsync({ user_id, guest_id, points: Number(points), reason })
                .then(() => {
                  setOpen(false);
                  setReason("");
                })
            }
          >
            Save the correction
          </Button>
        </div>
      </Modal>
    </>
  );
}

function ResultsScreen({ data }: { data: GamePlay }) {
  const leaderboard = useSessionLeaderboard(data.session_id);
  const ranked = [...data.scores].sort((a, b) => b.points - a.points);
  const winner = ranked[0];

  return (
    <div className="min-h-dvh bg-ink-900 px-4 py-8 text-white">
      <main className="mx-auto max-w-3xl space-y-5">
        <div className="text-center">
          <p className="text-5xl">🎉</p>
          <h1 className="mt-2 text-3xl font-semibold sm:text-5xl">Game complete!</h1>
          <p className="mt-1 text-white/70">{data.pack?.title ?? data.game.name}</p>
        </div>

        {winner ? (
          <Card className="bg-ember-500 text-center text-ink-900">
            <p className="text-sm font-medium">🏆 Winner</p>
            <p className="text-3xl font-bold">{winner.player_name}</p>
            <p className="text-lg">
              {winner.points} points
              {winner.correct_count > 0 ? ` · ${winner.correct_count} correct` : ""}
            </p>
          </Card>
        ) : null}

        <Card className="bg-white/5 text-white">
          <h2 className="mb-3 text-sm font-semibold text-white/70">Final scores</h2>
          <ol className="space-y-2">
            {ranked.map((score, index) => (
              <li key={score.id} className="flex items-center justify-between text-lg">
                <span>
                  {["🥇", "🥈", "🥉"][index] ?? `${index + 1}.`} {score.player_name}
                </span>
                <span className="text-white/80">
                  {score.points} points
                  {score.correct_count > 0 ? ` · ${score.correct_count} correct` : ""}
                </span>
              </li>
            ))}
            {ranked.length === 0 ? <li className="text-white/60">No scores were recorded.</li> : null}
          </ol>
        </Card>

        {leaderboard.data?.items.length ? (
          <Card className="bg-white/5 text-white">
            <h2 className="mb-3 text-sm font-semibold text-white/70">
              Session bragging rights so far
            </h2>
            <ol className="space-y-2">
              {leaderboard.data.items.slice(0, 5).map((row: Standing, index: number) => (
                <li key={row.id} className="flex items-center justify-between">
                  <span>
                    {["🥇", "🥈", "🥉"][index] ?? `${index + 1}.`} {row.name}
                  </span>
                  <span className="text-white/70">{row.points} XP</span>
                </li>
              ))}
            </ol>
          </Card>
        ) : null}

        <Card className="bg-white/5 text-center text-white">
          <p className="text-xl">🎉 Nice work!</p>
          <p className="mt-1 text-white/70">Ready to turn that energy into something useful?</p>
          <ButtonLink to={`/sessions/${data.session_id}/run`} size="xl" className="mt-4">
            Continue the meeting →
          </ButtonLink>
        </Card>
      </main>
    </div>
  );
}
