import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useLogin, useRegister } from "@/api/hooks";
import { Button, Card, Field, Input } from "@/components/ui/kit";

export function LoginPage() {
  const [params] = useSearchParams();
  const inviteCode = params.get("invite") ?? "";
  const [mode, setMode] = useState<"signin" | "create">(inviteCode ? "create" : "signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [teamName, setTeamName] = useState("");
  const navigate = useNavigate();
  const login = useLogin();
  const register = useRegister();
  const busy = login.isPending || register.isPending;
  const error = login.error ?? register.error;

  const submit = async () => {
    if (mode === "signin") {
      await login.mutateAsync({ email, password });
    } else {
      await register.mutateAsync({
        email,
        password,
        display_name: displayName,
        team_name: teamName || undefined,
        invite_code: inviteCode || undefined,
      });
    }
    navigate("/");
  };

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-6 p-5">
      <header className="space-y-2">
        <p className="flex items-center gap-2 text-sm font-semibold tracking-wide text-ember-700 uppercase">
          <img src="/mshikaki-mark.png" alt="" aria-hidden className="size-[60px]" />
          Mshikaki
        </p>
        <h1 className="text-3xl font-semibold text-balance">
          We came to the meeting to play. Somehow we left with assigned tasks.
        </h1>
      </header>

      <Card className="space-y-4">
        <div className="flex gap-2 text-sm">
          <button
            type="button"
            className={mode === "signin" ? "font-semibold" : "text-ink-600"}
            onClick={() => setMode("signin")}
          >
            Sign in
          </button>
          <span className="text-ink-200">|</span>
          <button
            type="button"
            className={mode === "create" ? "font-semibold" : "text-ink-600"}
            onClick={() => setMode("create")}
          >
            {inviteCode ? "Join this team" : "Create a team"}
          </button>
        </div>

        {mode === "create" ? (
          <Field label="Your name">
            <Input
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="Herman"
            />
          </Field>
        ) : null}

        <Field label="Email">
          <Input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </Field>
        <Field label="Password" hint={mode === "create" ? "At least 8 characters." : undefined}>
          <Input
            type="password"
            autoComplete={mode === "signin" ? "current-password" : "new-password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>

        {mode === "create" && !inviteCode ? (
          <Field label="Team name" hint="You can change this later.">
            <Input
              value={teamName}
              onChange={(event) => setTeamName(event.target.value)}
              placeholder="Innovations"
            />
          </Field>
        ) : null}

        {inviteCode ? (
          <p className="text-sm text-ink-600">
            You were invited with code <span className="font-mono">{inviteCode}</span>.
          </p>
        ) : null}

        <Button
          size="lg"
          className="w-full"
          disabled={busy || !email || !password || (mode === "create" && !displayName)}
          onClick={() => void submit()}
        >
          {busy ? "Working..." : mode === "signin" ? "Sign in" : "Create account"}
        </Button>

        {error ? (
          <p className="text-sm text-red-700">
            {error instanceof Error ? error.message : "That did not work."}
          </p>
        ) : null}
      </Card>

      <p className="text-xs text-ink-600">
        Internal tool. Email and password only, and nothing here is used to evaluate anybody.
      </p>
    </main>
  );
}
