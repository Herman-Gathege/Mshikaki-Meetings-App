/**
 * Every server interaction, in one place.
 *
 * Components never call fetch directly: they use these hooks, so caching,
 * invalidation and optimistic capture behave the same everywhere. Query keys are
 * plain arrays and invalidate by prefix, which is enough for an app this size.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
} from "@tanstack/react-query";

import { apiFetch, apiFetchText } from "@/api/client";
import type {
  Achievements,
  ActivityItem,
  Blocker,
  Comment,
  ContentPack,
  Decision,
  DecisionDetail,
  GameDefinition,
  GamePlay,
  Guest,
  Idea,
  IdeaDetail,
  Leaderboard,
  Me,
  Member,
  Metrics,
  MyPoints,
  Participant,
  Project,
  ProjectDetail,
  SessionDetail,
  SessionListItem,
  Standing,
  SummaryPayload,
  Task,
  TaskDetail,
  TeamInfo,
  Today,
} from "@/api/types";

type Items<T> = { items: T[]; total?: number };

interface MutateOptions {
  onSuccessMessage?: string;
}

function useInvalidate() {
  const queryClient = useQueryClient();
  return (keys: string[]) => {
    for (const key of keys) {
      void queryClient.invalidateQueries({ queryKey: [key] });
    }
  };
}

// --- auth ----------------------------------------------------------------------

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => apiFetch<Me>("/auth/me"),
    retry: false,
    staleTime: 60_000,
  });
}

export function useLogin() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { email: string; password: string }) =>
      apiFetch<Me>("/auth/login", { method: "POST", json: payload }),
    onSuccess: () => invalidate(["me", "today"]),
  });
}

export function useRegister() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: {
      email: string;
      display_name: string;
      password: string;
      team_name?: string;
      invite_code?: string;
    }) => apiFetch<Me>("/auth/register", { method: "POST", json: payload }),
    onSuccess: () => invalidate(["me", "today"]),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch("/auth/logout", { method: "POST" }),
    onSuccess: () => queryClient.clear(),
  });
}

export function useUpdatePreferences() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { leaderboard_opt_out?: boolean; display_name?: string }) =>
      apiFetch("/me/preferences", { method: "PATCH", json: payload }),
    onSuccess: () => invalidate(["me", "leaderboard", "achievements"]),
  });
}

// --- team ----------------------------------------------------------------------

export function useTeam() {
  return useQuery({ queryKey: ["team"], queryFn: () => apiFetch<TeamInfo>("/team") });
}

export function useMembers() {
  return useQuery({
    queryKey: ["team", "members"],
    queryFn: () => apiFetch<Items<Member>>("/team/members"),
  });
}

export function useGuests() {
  return useQuery({
    queryKey: ["team", "guests"],
    queryFn: () => apiFetch<Items<Guest>>("/team/guests"),
  });
}

export function useInvites() {
  return useQuery({
    queryKey: ["team", "invites"],
    queryFn: () => apiFetch<Items<{ id: string; code: string; email: string | null; role: string; expires_at: string | null }>>("/team/invites"),
    retry: false,
  });
}

export function useCreateInvite() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { email?: string; role?: string }) =>
      apiFetch<{ code: string }>("/team/invites", { method: "POST", json: payload }),
    onSuccess: () => invalidate(["team"]),
  });
}

export function useChangeRole() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { membershipId: string; role: string }) =>
      apiFetch(`/team/members/${payload.membershipId}`, {
        method: "PATCH",
        json: { role: payload.role },
      }),
    onSuccess: () => invalidate(["team"]),
  });
}

export function useRemoveMember() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (membershipId: string) =>
      apiFetch(`/team/members/${membershipId}`, { method: "DELETE" }),
    onSuccess: () => invalidate(["team"]),
  });
}

export function useCreateGuest() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { display_name: string; email?: string }) =>
      apiFetch<{ id: string; display_name: string }>("/guest-requests", {
        method: "POST",
        json: payload,
      }),
    onSuccess: () => invalidate(["team", "participants"]),
  });
}

// --- today ---------------------------------------------------------------------

export function useToday() {
  return useQuery({
    queryKey: ["today"],
    queryFn: () => apiFetch<Today>("/today"),
    staleTime: 15_000,
  });
}

// --- sessions ------------------------------------------------------------------

export function useSessions() {
  return useQuery({
    queryKey: ["sessions"],
    queryFn: () => apiFetch<Items<SessionListItem>>("/sessions"),
  });
}

export function useSession(sessionId: string | undefined) {
  return useQuery({
    queryKey: ["sessions", sessionId],
    queryFn: () => apiFetch<SessionDetail>(`/sessions/${sessionId}`),
    enabled: Boolean(sessionId),
  });
}

export function useCreateSession() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: {
      title?: string;
      scheduled_at?: string | null;
      location?: string | null;
      agenda?: string[];
    }) => apiFetch<SessionDetail>("/sessions", { method: "POST", json: payload }),
    onSuccess: () => invalidate(["sessions", "today"]),
  });
}

export function useSessionLifecycle(sessionId: string) {
  const invalidate = useInvalidate();
  const action = (verb: string, body?: unknown) =>
    apiFetch<SessionDetail>(`/sessions/${sessionId}/${verb}`, {
      method: "POST",
      ...(body === undefined ? {} : { json: body }),
    });

  return {
    start: useMutation({
      mutationFn: () => action("start"),
      onSuccess: () => invalidate(["sessions", "today"]),
    }),
    pause: useMutation({
      mutationFn: () => action("pause"),
      onSuccess: () => invalidate(["sessions", "today"]),
    }),
    resume: useMutation({
      mutationFn: () => action("resume"),
      onSuccess: () => invalidate(["sessions", "today"]),
    }),
    close: useMutation({
      mutationFn: () => action("close"),
      onSuccess: () => invalidate(["sessions", "today", "leaderboard", "achievements"]),
    }),
    reopen: useMutation({
      mutationFn: (reason: string) => action("reopen", { reason }),
      onSuccess: () => invalidate(["sessions", "today"]),
    }),
    cancel: useMutation({
      mutationFn: (reason?: string) => action("cancel", { reason: reason || undefined }),
      onSuccess: () => invalidate(["sessions", "today"]),
    }),
  };
}

export function useSessionParticipants(sessionId: string) {
  return useQuery({
    queryKey: ["participants", sessionId],
    queryFn: () => apiFetch<Items<Participant>>(`/sessions/${sessionId}/participants`),
  });
}

export function useAddParticipant(sessionId: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { user_id?: string; guest_id?: string; role?: string }) =>
      apiFetch(`/sessions/${sessionId}/participants`, { method: "POST", json: payload }),
    onSuccess: () => invalidate(["participants", "sessions"]),
  });
}

export function useMarkAttendance(sessionId: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { participantId: string; attended: boolean }) =>
      apiFetch(`/sessions/${sessionId}/participants/${payload.participantId}`, {
        method: "PATCH",
        json: { attended: payload.attended },
      }),
    onSuccess: () => invalidate(["participants", "sessions", "leaderboard"]),
  });
}

export function useAddAgendaItem(sessionId: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (title: string) =>
      apiFetch(`/sessions/${sessionId}/agenda`, { method: "POST", json: { title } }),
    onSuccess: () => invalidate(["sessions"]),
  });
}

export function useCoverAgendaItem(sessionId: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (itemId: string) =>
      apiFetch(`/sessions/${sessionId}/agenda/${itemId}/cover`, { method: "POST" }),
    onSuccess: () => invalidate(["sessions"]),
  });
}

export function useSessionSummary(sessionId: string, enabled = true) {
  return useQuery({
    queryKey: ["summary", sessionId],
    queryFn: () => apiFetch<SummaryPayload>(`/sessions/${sessionId}/summary`),
    enabled: Boolean(sessionId) && enabled,
  });
}

export function useRegenerateSummary(sessionId: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: () =>
      apiFetch<SummaryPayload>(`/sessions/${sessionId}/summary/regenerate`, { method: "POST" }),
    onSuccess: () => invalidate(["summary", "sessions"]),
  });
}

export function useSessionExport(sessionId: string) {
  return useMutation({ mutationFn: () => apiFetchText(`/sessions/${sessionId}/export.txt`) });
}

export function useSessionActivity(sessionId: string | undefined) {
  return useQuery({
    queryKey: ["activity", "session", sessionId],
    queryFn: () => apiFetch<Items<ActivityItem>>(`/sessions/${sessionId}/activity`),
    enabled: Boolean(sessionId),
    refetchInterval: 5000,
  });
}

// --- ideas ---------------------------------------------------------------------

export function useIdeas(params: { status?: string; session_id?: string } = {}) {
  const search = new URLSearchParams();
  if (params.status) search.set("status", params.status);
  if (params.session_id) search.set("session_id", params.session_id);
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return useQuery({
    queryKey: ["ideas", params.status ?? "all", params.session_id ?? "all"],
    queryFn: () => apiFetch<Items<Idea>>(`/ideas${suffix}`),
  });
}

export function useIdea(ideaId: string | undefined) {
  return useQuery({
    queryKey: ["ideas", "detail", ideaId],
    queryFn: () => apiFetch<IdeaDetail>(`/ideas/${ideaId}`),
    enabled: Boolean(ideaId),
  });
}

export function useCreateIdea() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { title: string; description?: string; session_id?: string; tags?: string[] }) =>
      apiFetch<Idea>("/ideas", { method: "POST", json: payload }),
    onSuccess: () => invalidate(["ideas", "sessions", "today", "activity"]),
  });
}

export function useUpdateIdea() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: {
      id: string;
      title?: string;
      description?: string;
      status?: string;
      tags?: string[];
    }) => {
      const { id, ...body } = payload;
      return apiFetch<Idea>(`/ideas/${id}`, { method: "PATCH", json: body });
    },
    onSuccess: () => invalidate(["ideas", "sessions", "today", "leaderboard"]),
  });
}

// --- decisions -----------------------------------------------------------------

export function useDecisions(params: { session_id?: string } = {}) {
  const suffix = params.session_id ? `?session_id=${params.session_id}` : "";
  return useQuery({
    queryKey: ["decisions", params.session_id ?? "all"],
    queryFn: () => apiFetch<Items<Decision>>(`/decisions${suffix}`),
  });
}

export function useDecision(decisionId: string | undefined) {
  return useQuery({
    queryKey: ["decisions", "detail", decisionId],
    queryFn: () => apiFetch<DecisionDetail>(`/decisions/${decisionId}`),
    enabled: Boolean(decisionId),
  });
}

export function useRecordDecision() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: {
      statement: string;
      session_id?: string;
      idea_id?: string;
      rationale?: string;
      standalone_reason?: string;
    }) => apiFetch<Decision>("/decisions", { method: "POST", json: payload }),
    onSuccess: () => invalidate(["decisions", "ideas", "sessions", "today", "leaderboard"]),
  });
}

export function useSupersedeDecision() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { id: string; statement: string; rationale?: string }) =>
      apiFetch<Decision>(`/decisions/${payload.id}/supersede`, {
        method: "POST",
        json: { statement: payload.statement, rationale: payload.rationale },
      }),
    onSuccess: () => invalidate(["decisions"]),
  });
}

// --- tasks ---------------------------------------------------------------------

export type TaskFilters = {
  status?: string;
  owner_id?: string;
  project_id?: string;
  session_id?: string;
  idea_id?: string;
  decision_id?: string;
  include_closed?: boolean;
};

export function useTasks(filters: TaskFilters = {}) {
  const search = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return useQuery({
    queryKey: ["tasks", search.toString()],
    queryFn: () => apiFetch<Items<Task>>(`/tasks${suffix}`),
  });
}

export function useMyTasks() {
  return useQuery({
    queryKey: ["tasks", "mine"],
    queryFn: () => apiFetch<Items<Task>>("/tasks/mine"),
  });
}

export function useTask(taskId: string | undefined) {
  return useQuery({
    queryKey: ["tasks", "detail", taskId],
    queryFn: () => apiFetch<TaskDetail>(`/tasks/${taskId}`),
    enabled: Boolean(taskId),
  });
}

export function useCreateTask() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: {
      title: string;
      description?: string;
      owner_id?: string | null;
      status?: string;
      priority?: string;
      due_date?: string | null;
      project_id?: string | null;
      session_id?: string | null;
      idea_id?: string | null;
      decision_id?: string | null;
      collaborator_ids?: string[];
    }) => apiFetch<Task>("/tasks", { method: "POST", json: payload }),
    onSuccess: () => invalidate(["tasks", "sessions", "today", "metrics", "activity"]),
  });
}

export function useUpdateTask() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: {
      id: string;
      title?: string;
      description?: string;
      priority?: string;
      due_date?: string | null;
      project_id?: string | null;
    }) => {
      const { id, ...body } = payload;
      return apiFetch<Task>(`/tasks/${id}`, { method: "PATCH", json: body });
    },
    onSuccess: () => invalidate(["tasks", "today"]),
  });
}

export function useAssignTask() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { id: string; owner_id: string | null }) =>
      apiFetch<Task>(`/tasks/${payload.id}/assign`, {
        method: "POST",
        json: { owner_id: payload.owner_id },
      }),
    onSuccess: () => invalidate(["tasks", "today", "activity"]),
  });
}

export function useChangeTaskStatus() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { id: string; status: string; reason?: string }) =>
      apiFetch<Task>(`/tasks/${payload.id}/status`, {
        method: "POST",
        json: { status: payload.status, reason: payload.reason },
      }),
    onSuccess: () =>
      invalidate(["tasks", "today", "sessions", "leaderboard", "metrics", "activity"]),
  });
}

export function useRaiseBlocker() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { taskId: string; reason: string }) =>
      apiFetch<Task & { blocker: Blocker }>(`/tasks/${payload.taskId}/blockers`, {
        method: "POST",
        json: { reason: payload.reason },
      }),
    onSuccess: () => invalidate(["tasks", "blockers", "today", "activity"]),
  });
}

export function useResolveBlocker() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { blockerId: string; resolution: string }) =>
      apiFetch<Blocker>(`/blockers/${payload.blockerId}/resolve`, {
        method: "POST",
        json: { resolution: payload.resolution },
      }),
    onSuccess: () =>
      invalidate(["tasks", "blockers", "today", "leaderboard", "achievements", "activity"]),
  });
}

export function useBlockers(openOnly = true) {
  return useQuery({
    queryKey: ["blockers", openOnly],
    queryFn: () => apiFetch<Items<Blocker>>(`/blockers?open_only=${openOnly}`),
  });
}

export function useAddCollaborator() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { taskId: string; userId: string }) =>
      apiFetch<Task>(`/tasks/${payload.taskId}/collaborators`, {
        method: "POST",
        json: { user_id: payload.userId },
      }),
    onSuccess: () => invalidate(["tasks"]),
  });
}

// --- projects ------------------------------------------------------------------

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => apiFetch<Items<Project>>("/projects"),
  });
}

export function useProject(projectId: string | undefined) {
  return useQuery({
    queryKey: ["projects", projectId],
    queryFn: () => apiFetch<ProjectDetail>(`/projects/${projectId}`),
    enabled: Boolean(projectId),
  });
}

export function useCreateProject() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { name: string; description?: string }) =>
      apiFetch<Project>("/projects", { method: "POST", json: payload }),
    onSuccess: () => invalidate(["projects", "activity"]),
  });
}

// --- comments ------------------------------------------------------------------

export function useCreateComment() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { target_type: string; target_id: string; body: string }) =>
      apiFetch<Comment>("/comments", { method: "POST", json: payload }),
    onSuccess: () => invalidate(["ideas", "decisions", "tasks", "activity"]),
  });
}

// --- games ---------------------------------------------------------------------

export function useGames() {
  return useQuery({
    queryKey: ["games"],
    queryFn: () => apiFetch<Items<GameDefinition>>("/games"),
  });
}

export function useContentPacks(family?: string) {
  const suffix = family ? `?family=${family}` : "";
  return useQuery({
    queryKey: ["games", "packs", family ?? "all"],
    queryFn: () => apiFetch<Items<ContentPack>>(`/games/packs${suffix}`),
  });
}

export function useStartPlay(sessionId: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: { game_key: string; content_pack_id?: string }) =>
      apiFetch<GamePlay>(`/sessions/${sessionId}/games`, { method: "POST", json: payload }),
    onSuccess: () => invalidate(["sessions", "games", "activity"]),
  });
}

export function usePlay(playId: string | undefined) {
  return useQuery({
    queryKey: ["play", playId],
    queryFn: () => apiFetch<GamePlay>(`/game-plays/${playId}`),
    enabled: Boolean(playId),
    refetchInterval: 4000,
  });
}

export function useSessionPlayers(sessionId: string | undefined) {
  return useQuery({
    queryKey: ["players", sessionId],
    queryFn: () => apiFetch<Items<{ user_id: string | null; guest_id: string | null; name: string; attended: boolean }>>(`/sessions/${sessionId}/players`),
    enabled: Boolean(sessionId),
  });
}

export function useGameActions(playId: string) {
  const invalidate = useInvalidate();
  const post = (suffix: string, body?: unknown) =>
    apiFetch<GamePlay>(`/game-plays/${playId}/${suffix}`, {
      method: "POST",
      ...(body === undefined ? {} : { json: body }),
    });

  return {
    next: useMutation({ mutationFn: () => post("next"), onSuccess: () => invalidate(["play"]) }),
    previous: useMutation({
      mutationFn: () => post("previous"),
      onSuccess: () => invalidate(["play"]),
    }),
    score: useMutation({
      mutationFn: (payload: { user_id?: string; guest_id?: string; points?: number }) =>
        post("score", payload),
      onSuccess: () => invalidate(["play"]),
    }),
    override: useMutation({
      mutationFn: (payload: {
        user_id?: string;
        guest_id?: string;
        points: number;
        reason: string;
      }) => post("override", payload),
      onSuccess: () => invalidate(["play"]),
    }),
    finish: useMutation({
      mutationFn: () => post("finish"),
      onSuccess: () => invalidate(["play", "sessions", "leaderboard"]),
    }),
  };
}

// --- bragging rights -----------------------------------------------------------

export function useLeaderboard(scope: string, sessionId?: string) {
  const suffix = sessionId ? `&session_id=${sessionId}` : "";
  return useQuery({
    queryKey: ["leaderboard", scope, sessionId ?? "none"],
    queryFn: () => apiFetch<Leaderboard>(`/leaderboard?scope=${scope}${suffix}`),
  });
}

export function useSessionLeaderboard(sessionId: string | undefined) {
  return useQuery({
    queryKey: ["leaderboard", "session", sessionId],
    queryFn: () => apiFetch<Leaderboard>(`/sessions/${sessionId}/leaderboard`),
    enabled: Boolean(sessionId),
  });
}

export function useMyPoints() {
  return useQuery({ queryKey: ["points"], queryFn: () => apiFetch<MyPoints>("/me/points") });
}

export function useAchievements() {
  return useQuery({
    queryKey: ["achievements"],
    queryFn: () => apiFetch<Achievements>("/achievements"),
  });
}

export function useMetrics() {
  return useQuery({ queryKey: ["metrics"], queryFn: () => apiFetch<Metrics>("/metrics") });
}

// --- record --------------------------------------------------------------------

export function useTeamActivity(params: {
  actor_id?: string;
  target_type?: string;
  limit?: number;
} = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return useQuery({
    queryKey: ["activity", "team", search.toString()],
    queryFn: () => apiFetch<Items<ActivityItem>>(`/activity${suffix}`),
  });
}

export function useSearch(term: string) {
  return useQuery({
    queryKey: ["search", term],
    queryFn: () =>
      apiFetch<{ ideas: Idea[]; decisions: Decision[]; tasks: Task[] }>(
        `/search?q=${encodeURIComponent(term)}`,
      ),
    enabled: term.trim().length > 1,
  });
}

export type { UseMutationResult, MutateOptions };
export type { Standing };
