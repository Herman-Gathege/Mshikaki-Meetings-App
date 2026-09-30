/**
 * The mobile-first shell.

 * Bottom navigation holds the five things a person does weekly. Everything else
 * (leaderboard, activity, search, team, sign out) lives behind the menu in the
 * top bar, so the primary navigation never grows past five items.
 */

import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useLogout, useMe, useSearch } from "@/api/hooks";
import { CaptureSheet } from "@/components/CaptureSheet";
import { Button, Input } from "@/components/ui/kit";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Today", end: true },
  { to: "/sessions", label: "Sessions" },
  { to: "/work", label: "Work" },
  { to: "/ideas", label: "Ideas" },
  { to: "/play", label: "Play" },
];

export function AppLayout() {
  const me = useMe();
  const logout = useLogout();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [captureOpen, setCaptureOpen] = useState(false);
  const [term, setTerm] = useState("");
  const search = useSearch(term);

  return (
    <div className="min-h-dvh bg-ink-50 pb-20 lg:pb-0 lg:pl-64">
      <header className="sticky top-0 z-30 border-b border-ink-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3">
          <NavLink to="/" className="text-base font-semibold tracking-tight text-ember-600">
            MSHIKAKI
          </NavLink>
          <span className="hidden truncate text-sm text-ink-600 sm:inline">
            {me.data?.team.name}
          </span>
          <div className="ml-auto flex items-center gap-2">
            <div className="relative hidden sm:block">
              <Input
                className="h-9 w-48"
                placeholder="Search"
                value={term}
                onChange={(event) => setTerm(event.target.value)}
              />
              {term.trim().length > 1 && search.data ? (
                <div className="absolute right-0 z-40 mt-1 w-72 rounded-card border border-ink-200 bg-white p-3 shadow-lg">
                  {search.data.ideas.length + search.data.decisions.length + search.data.tasks.length ===
                  0 ? (
                    <p className="text-sm text-ink-600">Nothing found.</p>
                  ) : (
                    <ul className="space-y-2 text-sm">
                      {search.data.ideas.slice(0, 4).map((idea) => (
                        <li key={idea.id}>
                          <NavLink
                            className="hover:underline"
                            to={`/ideas/${idea.id}`}
                            onClick={() => setTerm("")}
                          >
                            💡 {idea.title}
                          </NavLink>
                        </li>
                      ))}
                      {search.data.decisions.slice(0, 3).map((decision) => (
                        <li key={decision.id}>
                          <NavLink
                            className="hover:underline"
                            to={`/decisions/${decision.id}`}
                            onClick={() => setTerm("")}
                          >
                            📌 {decision.statement.slice(0, 60)}
                          </NavLink>
                        </li>
                      ))}
                      {search.data.tasks.slice(0, 4).map((task) => (
                        <li key={task.id}>
                          <NavLink
                            className="hover:underline"
                            to={`/tasks/${task.id}`}
                            onClick={() => setTerm("")}
                          >
                            ✅ {task.title}
                          </NavLink>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ) : null}
            </div>
            <Button variant="ghost" size="sm" onClick={() => setMenuOpen((open) => !open)}>
              Menu
            </Button>
          </div>
        </div>

        {menuOpen ? (
          <div className="border-t border-ink-200 bg-white">
            <nav className="mx-auto flex max-w-5xl flex-wrap gap-2 px-4 py-3 text-sm">
              {[
                { to: "/leaderboard", label: "Leaderboard" },
                { to: "/activity", label: "Activity" },
                { to: "/projects", label: "Projects" },
                { to: "/team", label: "Team" },
                { to: "/search", label: "Search" },
              ].map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setMenuOpen(false)}
                  className="rounded-lg border border-ink-200 px-3 py-2 hover:bg-ink-100"
                >
                  {item.label}
                </NavLink>
              ))}
              <button
                type="button"
                className="rounded-lg border border-ink-200 px-3 py-2 hover:bg-ink-100"
                onClick={() => {
                  void logout.mutateAsync().then(() => navigate("/login"));
                }}
              >
                Sign out
              </button>
            </nav>
          </div>
        ) : null}
      </header>

      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-ink-200 bg-white p-4 lg:block">
        <p className="px-2 py-3 text-lg font-semibold tracking-tight text-ember-600">MSHIKAKI</p>
        <nav className="space-y-1">
          {[
            ...NAV,
            { to: "/leaderboard", label: "Leaderboard" },
            { to: "/activity", label: "Activity" },
            { to: "/projects", label: "Projects" },
            { to: "/team", label: "Team" },
          ].map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={"end" in item ? item.end : false}
              className={({ isActive }) =>
                cn(
                  "block rounded-lg px-3 py-2 text-sm",
                  isActive ? "bg-ink-100 font-medium" : "hover:bg-ink-100",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <p className="mt-6 px-3 text-xs text-ink-400">
          For fun. Not a performance measure.
        </p>
      </aside>

      <main className="mx-auto max-w-5xl px-4 py-5">
        <Outlet />
      </main>

      <button
        type="button"
        onClick={() => setCaptureOpen(true)}
        className="fixed bottom-20 right-4 z-30 rounded-full bg-ember-600 px-5 py-4 text-sm font-semibold text-white shadow-lg hover:bg-ember-500 lg:bottom-8"
      >
        + Idea
      </button>

      <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-ink-200 bg-white lg:hidden">
        <ul className="flex">
          {NAV.map((item) => (
            <li key={item.to} className="flex-1">
              <NavLink
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "flex h-16 items-center justify-center text-xs font-medium",
                    isActive ? "text-ember-600" : "text-ink-600",
                  )
                }
              >
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <CaptureSheet open={captureOpen} onClose={() => setCaptureOpen(false)} />
    </div>
  );
}
