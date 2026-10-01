/**
 * The QR landing page.

 * One screen, three fields, one button. Scanning the code on the projector should
 * get somebody into the meeting faster than walking to the front of the room.
 */

import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/api/client";
import type { SessionDetail } from "@/api/types";
import { Button, Card, Field, Input } from "@/components/ui/kit";
import { ErrorState, LoadingState } from "@/components/states";
import { formatDateTime } from "@/lib/dates";

type Preview = {
  team_name: string;
  role: string;
  email_domains: string[];
  session: { id: string; title: string; status: string; scheduled_at: string | null } | null;
};

type JoinResult = {
  team: { id: string; name: string };
  session: SessionDetail | null;
};

export function JoinPage() {
  const { code = "" } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const preview = useQuery({
    queryKey: ["join", code],
    queryFn: () => apiFetch<Preview>(`/join/${code}`),
    retry: false,
  });

  const join = useMutation({
    mutationFn: () =>
      apiFetch<JoinResult>("/join", {
        method: "POST",
        json: { code, display_name: displayName, email, password },
      }),
    onSuccess: (result) => {
      navigate(result.session ? `/sessions/${result.session.id}` : "/");
    },
  });

  if (preview.isPending) return <LoadingState label="Checking your invite" />;
  if (preview.isError) {
    return (
      <main className="mx-auto max-w-md p-5">
        <ErrorState error={preview.error} />
        <p className="mt-4 text-sm text-ink-600">
          Ask the facilitator to show the QR code again.
        </p>
      </main>
    );
  }

  const data = preview.data;
  const domains = data?.email_domains ?? [];
  const domainHint = domains.map((domain) => `@${domain}`).join(" or ");

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-5 p-5">
      <header className="space-y-2">
        <p className="text-sm font-semibold tracking-wide text-ember-700 uppercase">Mshikaki</p>
        <h1 className="text-3xl font-semibold text-balance">
          Joining {data?.team_name ?? "the team"}
        </h1>
        {data?.session ? (
          <p className="text-ink-600">
            You are joining <strong>{data.session.title}</strong>
            {data.session.scheduled_at ? ` · ${formatDateTime(data.session.scheduled_at)}` : ""}
            {data.session.status === "active" ? " · happening now" : ""}
          </p>
        ) : (
          <p className="text-ink-600">No meeting is scheduled yet. You will still be in the team.</p>
        )}
      </header>

      <Card className="space-y-4">
        <Field label="Your name" hint="This is how you appear in games and in the record.">
          <Input
            autoFocus
            value={displayName}
            placeholder="Herman"
            onChange={(event) => setDisplayName(event.target.value)}
          />
        </Field>
        <Field label="Work email" hint={domainHint ? `Please use ${domainHint}` : undefined}>
          <Input
            type="email"
            inputMode="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </Field>
        <Field label="Password" hint="At least 8 characters, so you can sign in next time.">
          <Input
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>

        <Button
          size="lg"
          className="w-full"
          disabled={!displayName.trim() || !email || password.length < 8 || join.isPending}
          onClick={() => join.mutate()}
        >
          {join.isPending ? "Joining…" : "Join and open the meeting"}
        </Button>

        {join.isError ? (
          <p className="text-sm text-red-700">
            {join.error instanceof Error ? join.error.message : "Could not join."}
          </p>
        ) : null}
      </Card>

      <p className="text-xs text-ink-600">
        You are created as a member of {data?.team_name ?? "the team"}. That account is what lets
        you capture ideas, take tasks and follow what was decided.
      </p>
    </main>
  );
}
