/**
 * API shapes, consumed by every page.
 *
 * Hand-written for now and checked by the compiler. When the API settles these
 * become the output of scripts/gen-types.sh (FastAPI's OpenAPI schema), and this
 * file is replaced rather than edited.
 */

export type Role = "owner" | "admin" | "facilitator" | "member";
export type SessionStatus = "planned" | "active" | "paused" | "completed" | "cancelled";
export type IdeaStatus =
  | "new"
  | "discussing"
  | "accepted"
  | "parked"
  | "rejected"
  | "converted";
export type TaskStatus = "backlog" | "in_progress" | "blocked" | "done" | "cancelled";
export type TaskPriority = "low" | "normal" | "high" | "urgent";
export type GameFamily = "prompt_deck" | "host_quiz" | "host_scored";
export type RunModeStage = "play" | "agenda" | "capture" | "decide" | "assign" | "close";

/** How an agenda item ended, in one word. */
export type AgendaOutcome = "accomplished" | "pending" | "assigned" | "none";

export interface Me {
  user: {
    id: string;
    email: string;
    display_name: string;
    timezone: string;
    leaderboard_opt_out: boolean;
  };
  team: { id: string; name: string; timezone: string };
  role: Role;
}

export interface ActivityItem {
  id: string;
  verb: string;
  description: string;
  sentence: string;
  actor_type: string;
  actor_name: string;
  occurred_at: string;
  target_type: string;
  target_id: string | null;
  session_id: string | null;
  payload: Record<string, unknown>;
}

export interface Comment {
  id: string;
  body: string;
  author: string;
  author_id: string | null;
  created_at: string;
  edited_at: string | null;
}

export interface Member {
  membership_id: string;
  user_id: string;
  name: string;
  email: string;
  role: Role;
  status: string;
  joined_at: string;
  leaderboard_opt_out: boolean;
}

export interface Guest {
  id: string;
  display_name: string;
  email: string | null;
  linked_user_id: string | null;
}

export interface SessionCounts {
  ideas: number;
  decisions: number;
  tasks: number;
  games: number;
}

export interface AgendaItem {
  id: string;
  position: number;
  title: string;
  covered: boolean;
  timebox_minutes: number | null;
  outcome: AgendaOutcome | null;
  is_current: boolean;
}

export interface AgendaPosition {
  position: number;
  total: number;
  remaining: number;
  is_last: boolean;
}

export interface Note {
  id: string;
  body: string;
  author: string;
  agenda_item_id: string | null;
  agenda_title?: string | null;
  created_at: string | null;
}

export interface SessionListItem {
  id: string;
  title: string;
  sequence_no: number;
  status: SessionStatus;
  scheduled_at: string | null;
  started_at: string | null;
  location: string | null;
  facilitator: string | null;
  counts: SessionCounts;
}

export interface SessionDetail extends Omit<SessionListItem, "facilitator"> {
  ended_at: string | null;
  facilitator: { id: string; name: string } | null;
  tasks_open: number;
  has_summary: boolean;
  summary_generated_at: string | null;
  /** Which Run Mode stage the room is on, set by the facilitator. */
  run_mode_stage: RunModeStage | null;
  run_mode_active: boolean;
  run_mode_updated_at: string | null;
  agenda: AgendaItem[];
  /** Where the room is in the agenda, counted the way a person says it. */
  agenda_position: AgendaPosition;
  current_agenda_item_id: string | null;
  notes: Note[];
  ideas: { id: string; title: string; status: IdeaStatus; author: string }[];
  decisions: { id: string; statement: string; recorded_by: string }[];
  games: { id: string; key: string; status: string }[];
}

export interface Participant {
  id: string;
  user_id: string | null;
  guest_id: string | null;
  name: string;
  role: string;
  attended: boolean;
}

export interface Idea {
  id: string;
  title: string;
  description: string | null;
  status: IdeaStatus;
  author: { id: string | null; name: string };
  session_id: string | null;
  /** The agenda item this idea was raised under, when there was one. */
  agenda_item_id: string | null;
  tags: string[];
  converted_to: { type: string; id: string } | null;
  created_at: string;
}

export interface IdeaDetail extends Idea {
  comments: Comment[];
  activity: ActivityItem[];
}

export interface Decision {
  id: string;
  statement: string;
  rationale: string | null;
  recorded_by: string;
  session_id: string | null;
  agenda_item_id?: string | null;
  idea_id: string | null;
  decided_at: string | null;
  superseded_by_id: string | null;
  is_superseded: boolean;
}

export interface DecisionDetail extends Decision {
  comments: Comment[];
  activity: ActivityItem[];
}

export interface Blocker {
  id: string;
  task_id: string | null;
  task_title: string | null;
  reason: string;
  raised_by: string;
  raised_at: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
  resolution: string | null;
  is_open: boolean;
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  owner: { id: string; name: string } | null;
  due_date: string | null;
  completed_at: string | null;
  project_id: string | null;
  origin: {
    session_id: string | null;
    idea_id: string | null;
    decision_id: string | null;
  };
  agenda_item_id: string | null;
  collaborators: { id: string; name: string }[];
  open_blockers: { id: string; reason: string; raised_by: string; raised_at: string | null }[];
  created_at: string;
  updated_at: string;
}

export interface TaskDetail extends Task {
  comments: Comment[];
  activity: ActivityItem[];
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  status: string;
  owner: { id: string; name: string } | null;
}

export interface ProjectDetail extends Project {
  tasks: Task[];
  decisions: Decision[];
  activity: ActivityItem[];
}

export interface GameDefinition {
  key: string;
  name: string;
  family: GameFamily;
  description: string | null;
  how_to_play: string | null;
  min_players: number;
  max_players: number | null;
  typical_minutes: number;
  energy: string;
  tags: string[];
}

export interface ContentPack {
  id: string;
  key: string;
  title: string;
  description: string | null;
  game_key: string;
  items: number;
  license: string;
  attribution: string;
}

export interface GamePlay {
  id: string;
  session_id: string;
  host_id: string | null;
  /** Who the room is following while this game runs. */
  host_name: string | null;
  game: { key: string; name: string; family: GameFamily; how_to_play: string | null };
  pack: { id: string; title: string } | null;
  status: string;
  index: number;
  total: number;
  /** How many people have answered the live question, out of the room. */
  answered: { count: number; of: number };
  question: {
    id: string;
    prompt: string;
    /** Hidden from the room until the answer is revealed. */
    answer: string | null;
    choices: string[] | null;
    category: string | null;
    media_url: string | null;
    explanation: string | null;
    seconds: number;
    /** The server's clock, so every phone counts the same seconds. */
    seconds_left: number;
    started_at: string | null;
    revealed: boolean;
    open: boolean;
  } | null;
  /** The viewer's own answer to the live question. */
  you: { answer: string | null; correct: boolean | null; answered: boolean };
  scores: {
    id: string;
    user_id: string | null;
    guest_id: string | null;
    player_name: string;
    points: number;
    correct_count: number;
    position: number | null;
  }[];
}

export interface Standing {
  id: string;
  name: string;
  kind: string;
  points: number;
  rank?: number;
}

export interface Leaderboard {
  scope: string;
  items: Standing[];
  disclaimer: string;
}

export interface MyPoints {
  season: { name: string; points: number };
  all_time: number;
  recent: { reason: string; amount: number; at: string }[];
}

export interface Achievements {
  progress: {
    key: string;
    name: string;
    description: string;
    emoji: string;
    rarity: string;
    earned: boolean;
    have: number;
    threshold: number;
  }[];
  awards: { key: string; name: string; emoji: string; awarded_at: string }[];
}

export interface Metrics {
  open_tasks: number;
  blocked: number;
  completed: number;
  overdue: number;
  open_blockers: number;
  by_owner: { name: string; open_tasks: number }[];
  note: string;
}

export interface SummaryPayload {
  summary: Record<string, unknown> | null;
  text: string | null;
  generated_at: string | null;
}

export interface Today {
  session: {
    id: string;
    title: string;
    status: SessionStatus;
    scheduled_at: string | null;
    sequence_no: number;
  } | null;
  my_tasks: Task[];
  my_open_count: number;
  blockers: Blocker[];
  activity: ActivityItem[];
  leaderboard: Standing[];
  my_points: MyPoints;
}

export interface TeamInfo {
  id: string;
  name: string;
  description: string | null;
  timezone: string;
  role: Role;
  members: number | null;
}
