import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";

import { useMe } from "@/api/hooks";
import { LoadingState } from "@/components/states";
import { Toaster } from "@/components/toast";
import { AppLayout } from "@/layouts/AppLayout";
import { LoginPage } from "@/pages/LoginPage";
import { JoinPage } from "@/pages/JoinPage";
import { RunModePage } from "@/pages/RunModePage";
import { SessionPage } from "@/pages/SessionPage";
import { SessionsPage } from "@/pages/SessionsPage";
import { TeamPage } from "@/pages/TeamPage";
import { TodayPage } from "@/pages/TodayPage";
import { DecisionPage, IdeaPage, IdeasPage } from "@/pages/ideas";
import { GamePlayPage, PlayPage } from "@/pages/play";
import { ActivityPage, LeaderboardPage, SearchPage } from "@/pages/record";
import { ProjectPage, TaskPage, WorkPage } from "@/pages/work";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // The app is used in meetings on a LAN; refetching on focus is noise.
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 10_000,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Toaster />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/join/:code" element={<JoinPage />} />

          <Route element={<RequireAuth />}>
            {/* Screen-first: no app chrome while a room is watching. */}
            <Route path="/sessions/:sessionId/run" element={<RunModePage />} />
            <Route path="/play/:playId" element={<GamePlayPage />} />

            <Route element={<AppLayout />}>
              <Route path="/" element={<TodayPage />} />
              <Route path="/sessions" element={<SessionsPage />} />
              <Route path="/sessions/:sessionId" element={<SessionPage />} />
              <Route path="/ideas" element={<IdeasPage />} />
              <Route path="/ideas/:ideaId" element={<IdeaPage />} />
              <Route path="/decisions/:decisionId" element={<DecisionPage />} />
              <Route path="/work" element={<WorkPage />} />
              <Route path="/work/mine" element={<WorkPage />} />
              <Route path="/tasks/:taskId" element={<TaskPage />} />
              <Route path="/projects/:projectId" element={<ProjectPage />} />
              <Route path="/play" element={<PlayPage />} />
              <Route path="/leaderboard" element={<LeaderboardPage />} />
              <Route path="/activity" element={<ActivityPage />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/team" element={<TeamPage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

/** Sends anyone without a session to the sign-in page. */
function RequireAuth() {
  const me = useMe();

  if (me.isPending) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <LoadingState label="Checking your session" />
      </div>
    );
  }
  if (me.isError) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}
