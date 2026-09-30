import { Button } from "@/components/ui/button";
import { useHealth, useReadiness } from "@/api/health";

/**
 * Phase 0 placeholder.
 *
 * Its job is to prove the whole path works: browser -> Vite (or FastAPI in the
 * container) -> API -> Postgres. Today, My Work and the next session replace it
 * in Phase 1 and 2.
 */
export function HomePage() {
  const health = useHealth();
  const readiness = useReadiness();

  return (
    <main className="mx-auto flex min-h-dvh max-w-2xl flex-col justify-center gap-6 p-6">
      <header className="space-y-2">
        <p className="text-sm font-medium tracking-wide text-ember-600 uppercase">
          Mshikaki
        </p>
        <h1 className="text-3xl font-semibold text-balance">
          We came to the meeting to play. Somehow we left with assigned tasks.
        </h1>
        <p className="text-ink-600">
          Phase 0 is running. The API answers below, which means the container,
          the database and the browser are all talking to each other.
        </p>
      </header>

      <dl className="grid gap-3 rounded-card border border-ink-200 bg-white p-5 sm:grid-cols-2">
        <div>
          <dt className="text-sm text-ink-600">API</dt>
          <dd className="text-lg font-medium">
            {health.isPending ? "checking..." : (health.data?.status ?? "unreachable")}
          </dd>
          <dd className="text-sm text-ink-400">
            {health.data ? `version ${health.data.version}` : (health.error?.message ?? "")}
          </dd>
        </div>

        <div>
          <dt className="text-sm text-ink-600">Database</dt>
          <dd className="text-lg font-medium">
            {readiness.isPending
              ? "checking..."
              : (readiness.data?.database ?? "unreachable")}
          </dd>
          <dd className="text-sm text-ink-400">
            {readiness.data?.status ?? readiness.error?.message ?? ""}
          </dd>
        </div>
      </dl>

      <div className="flex flex-wrap gap-3">
        <Button
          onClick={() => {
            void health.refetch();
            void readiness.refetch();
          }}
        >
          Check again
        </Button>
        <Button variant="outline" onClick={() => window.open("/api/docs", "_blank")}>
          API docs
        </Button>
      </div>
    </main>
  );
}
