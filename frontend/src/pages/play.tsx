import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  useContentPacks,
  useGameActions,
  useGames,
  usePlay,
  useSessionPlayers,
  useSessions,
  useStartPlay,
} from "@/api/hooks";
import { LoadingState, ErrorState, PageHeader, EmptyState } from "@/components/states";
import { Button, Card, Field, Modal, Select } from "@/components/ui/kit";

export function PlayPage() {
  const games = useGames();
  const [startOpen, setStartOpen] = useState(false);

  return (
    <>
      <PageHeader
        title="Play"
        subtitle="Games are the warm-up, not the work. Nothing here is work-related on purpose."
        actions={<Button onClick={() => setStartOpen(true)}>Start a game</Button>}
      />

      {games.isPending ? <LoadingState /> : null}
      {games.isError ? <ErrorState error={games.error} /> : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {(games.data?.items ?? []).map((game) => (
          <Card key={game.key}>
            <div className="flex items-start justify-between gap-2">
              <h2 className="font-medium">{game.name}</h2>
              <span className="rounded-full bg-ink-100 px-2 py-0.5 text-xs">{game.typical_minutes} min</span>
            </div>
            <p className="mt-1 text-sm text-ink-600">{game.description}</p>
            <p className="mt-2 text-xs text-ink-400">
              {game.family.replace("_", " ")} · {game.energy} energy
            </p>
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
  const navigate = useNavigate();

  const active = (sessions.data?.items ?? []).filter((session) => session.status === "active");

  return (
    <Modal open={open} title="Start a game" onClose={onClose}>
      <div className="space-y-4">
        <Field label="In which session?" hint="Only a live session can host a game.">
          <Select value={sessionId} onChange={(event) => setSessionId(event.target.value)}>
            <option value="">Pick a session</option>
            {active.map((session) => (
              <option key={session.id} value={session.id}>
                {session.title}
              </option>
            ))}
          </Select>
        </Field>
        {active.length === 0 ? (
          <p className="text-sm text-ink-600">
            No session is running. Start one from <Link className="underline" to="/sessions">Sessions</Link>.
          </p>
        ) : null}
        <Field label="Game">
          <Select value={gameKey} onChange={(event) => setGameKey(event.target.value)}>
            <option value="">Pick a game</option>
            {(games.data?.items ?? []).map((game) => (
              <option key={game.key} value={game.key}>
                {game.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Content pack">
          <Select value={packId} onChange={(event) => setPackId(event.target.value)}>
            <option value="">No pack (host runs it)</option>
            {(packs.data?.items ?? [])
              .filter((pack) => !gameKey || pack.game_key === gameKey)
              .map((pack) => (
                <option key={pack.id} value={pack.id}>
                  {pack.title} ({pack.items})
                </option>
              ))}
          </Select>
        </Field>
        <Button
          size="lg"
          disabled={!sessionId || !gameKey || start.isPending}
          onClick={() =>
            void start
              .mutateAsync({ game_key: gameKey, content_pack_id: packId || undefined })
              .then((play) => navigate(`/play/${play.id}`))
          }
        >
          Start
        </Button>
      </div>
    </Modal>
  );
}

export function GamePlayPage() {
  const { playId } = useParams<{ playId: string }>();
  const play = usePlay(playId);
  const actions = useGameActions(playId ?? "");
  const players = useSessionPlayers(play.data?.session_id);
  const [revealed, setRevealed] = useState(false);
  const [overrideFor, setOverrideFor] = useState<string | null>(null);
  const [overridePoints, setOverridePoints] = useState("10");
  const [overrideReason, setOverrideReason] = useState("");

  if (play.isPending) return <LoadingState />;
  if (play.isError) return <ErrorState error={play.error} />;
  if (!play.data) return null;
  const data = play.data;

  if (!data.game.key) return <EmptyState title="No game" />;

  return (
    <div className="min-h-dvh bg-ink-900 px-4 py-6 text-white">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs tracking-widest text-white/50 uppercase">
              {data.pack?.title ?? "Host-run"} · {data.total > 0 ? `${data.index + 1} of ${data.total}` : "no pack"}
            </p>
            <h1 className="text-3xl font-semibold">{data.game.name}</h1>
          </div>
          <Link to={`/sessions/${data.session_id}/run`}>
            <Button variant="ghost" className="text-white hover:bg-white/10">
              Back to Run Mode
            </Button>
          </Link>
        </header>

        <Card className="bg-white/5 text-white">
          <p className="text-4xl leading-snug font-semibold">
            {data.question?.prompt ?? "Use the host console below to score this activity."}
          </p>
          {revealed && data.question?.answer ? (
            <p className="mt-4 text-xl text-nile-400">Answer: {data.question.answer}</p>
          ) : null}
          {data.game.how_to_play ? (
            <p className="mt-4 text-sm text-white/60">{data.game.how_to_play}</p>
          ) : null}

          <div className="mt-6 flex flex-wrap gap-3">
            <Button variant="ghost" className="text-white hover:bg-white/10" onClick={() => void actions.previous.mutateAsync()}>
              Back
            </Button>
            <Button size="lg" onClick={() => setRevealed(true)}>
              Reveal answer
            </Button>
            <Button
              size="lg"
              onClick={() => {
                setRevealed(false);
                void actions.next.mutateAsync();
              }}
            >
              Next
            </Button>
          </div>
        </Card>

        <Card className="bg-white/5 text-white">
          <h2 className="mb-3 text-sm font-semibold text-white/70">Host console</h2>
          <ul className="grid gap-2 sm:grid-cols-2">
            {(players.data?.items ?? []).map((player) => {
              const key = player.user_id ?? player.guest_id ?? "";
              const score = data.scores.find(
                (row) => row.user_id === player.user_id && row.guest_id === player.guest_id,
              );
              return (
                <li
                  key={key}
                  className="flex items-center justify-between gap-2 rounded-xl bg-white/5 p-3"
                >
                  <span>
                    {player.name}
                    <span className="ml-2 text-white/50">{score?.points ?? 0}</span>
                  </span>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() =>
                        void actions.score.mutateAsync({
                          user_id: player.user_id ?? undefined,
                          guest_id: player.guest_id ?? undefined,
                          points: 10,
                        })
                      }
                    >
                      +10
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-white hover:bg-white/10"
                      onClick={() => setOverrideFor(key)}
                    >
                      Fix
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>

          {overrideFor ? (
            <div className="mt-4 space-y-2 border-t border-white/10 pt-4">
              <p className="text-sm text-white/70">Correct a score (recorded with a reason)</p>
              <div className="flex flex-wrap gap-2">
                <input
                  className="h-11 w-24 rounded-lg bg-white px-3 text-ink-900"
                  value={overridePoints}
                  onChange={(event) => setOverridePoints(event.target.value)}
                />
                <input
                  className="h-11 flex-1 rounded-lg bg-white px-3 text-ink-900"
                  placeholder="Why?"
                  value={overrideReason}
                  onChange={(event) => setOverrideReason(event.target.value)}
                />
                <Button
                  disabled={overrideReason.trim().length < 3}
                  onClick={() => {
                    const player = (players.data?.items ?? []).find(
                      (row) => (row.user_id ?? row.guest_id) === overrideFor,
                    );
                    void actions
                      .override
                      .mutateAsync({
                        user_id: player?.user_id ?? undefined,
                        guest_id: player?.guest_id ?? undefined,
                        points: Number(overridePoints),
                        reason: overrideReason,
                      })
                      .then(() => {
                        setOverrideFor(null);
                        setOverrideReason("");
                      });
                  }}
                >
                  Save
                </Button>
              </div>
            </div>
          ) : null}

          <div className="mt-6 flex gap-3">
            <Button size="lg" onClick={() => void actions.finish.mutateAsync()}>
              Finish and record results
            </Button>
            <Link to={`/sessions/${data.session_id}/run`}>
              <Button variant="ghost" className="text-white hover:bg-white/10">
                Done
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
}
