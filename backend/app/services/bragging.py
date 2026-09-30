"""XP, achievements and the leaderboard.

XP is a ledger of events. Nothing here stores a running total, and every award
carries an idempotency key so a retry cannot pay twice. The leaderboard is a query
over that ledger, filtered by the seasons people can actually compete in.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.db.models import (
    Achievement,
    AchievementAward,
    Blocker,
    GamePlay,
    GameScore,
    Guest,
    Idea,
    Season,
    SessionParticipant,
    Task,
    User,
    XpEvent,
)
from app.db.models import Session as MeetingSession
from app.domain import achievements as achievement_rules
from app.domain import xp as xp_rules
from app.domain.enums import IdeaStatus, SeasonStatus, TaskStatus
from app.errors import AppError, NotFoundError
from app.services.activity import record_activity


def ensure_season(db: DbSession, team_id: uuid.UUID) -> Season:
    """The active season, created on first use. One quarter, named."""
    season = (
        db.execute(
            select(Season)
            .where(Season.team_id == team_id, Season.status == SeasonStatus.ACTIVE.value)
            .order_by(Season.starts_at.desc())
        )
        .scalars()
        .first()
    )
    if season is not None:
        return season

    count = int(
        db.execute(
            select(func.count()).select_from(Season).where(Season.team_id == team_id)
        ).scalar_one()
    )
    now = datetime.now(timezone.utc)
    season = Season(
        team_id=team_id,
        name=xp_rules.season_name(count + 1),
        starts_at=now,
        ends_at=now + timedelta(days=90),
        status=SeasonStatus.ACTIVE.value,
    )
    db.add(season)
    db.flush()
    return season


def _window_counts(
    db: DbSession, *, user_id: uuid.UUID | None, guest_id: uuid.UUID | None, reason_key: str
) -> tuple[int, int, int]:
    """Awards already made today, this week, and in the given rule's lifetime."""
    now = datetime.now(timezone.utc)
    day_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    week_start = day_start - timedelta(days=now.weekday())

    subject = XpEvent.user_id == user_id if user_id is not None else XpEvent.guest_id == guest_id
    base = (
        select(func.count()).select_from(XpEvent).where(XpEvent.reason_key == reason_key, subject)
    )

    today = int(db.execute(base.where(XpEvent.occurred_at >= day_start)).scalar_one())
    week = int(db.execute(base.where(XpEvent.occurred_at >= week_start)).scalar_one())
    total = int(db.execute(base).scalar_one())
    return today, week, total


def award_for_event(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    user_id: uuid.UUID | None,
    subject_name: str,
    rule_key: str,
    source_type: str,
    source_id: uuid.UUID | None,
    actor=None,
    actor_name: str | None = None,
    session_id: uuid.UUID | None = None,
    guest_id: uuid.UUID | None = None,
    awards_this_session: int = 0,
) -> XpEvent | None:
    """Award XP once for a domain event. Returns None when capped or already paid."""
    if user_id is None and guest_id is None:
        return None

    subject_id = user_id or guest_id
    key = xp_rules.idempotency_key(rule_key, source_type, source_id or subject_id, subject_id)
    existing = db.execute(
        select(XpEvent).where(XpEvent.idempotency_key == key)
    ).scalar_one_or_none()
    if existing is not None:
        return None

    today, week, total = _window_counts(
        db, user_id=user_id, guest_id=guest_id if user_id is None else None, reason_key=rule_key
    )
    amount = xp_rules.award_amount(
        rule_key,
        awards_this_session=awards_this_session,
        awards_today=today,
        awards_this_week=week,
        # Diminishing returns are per day, not per lifetime: a reliable
        # contributor should not be worth less in month three than in week one.
        occurrence_index=today,
    )
    if amount <= 0:
        return None

    facilitator_pressed_it = (
        actor is not None and actor.user_id is not None and actor.user_id == user_id
    )
    amount = xp_rules.apply_facilitator_weight(
        rule_key, amount, facilitator_created_it=facilitator_pressed_it
    )

    season = ensure_season(db, team_id)
    event = XpEvent(
        team_id=team_id,
        user_id=user_id,
        guest_id=guest_id,
        subject_name=subject_name,
        amount=amount,
        reason_key=rule_key,
        source_type=source_type,
        source_id=source_id,
        session_id=session_id,
        awarded_by=actor.user_id if actor is not None else None,
        season_id=season.id,
        occurred_at=datetime.now(timezone.utc),
        idempotency_key=key,
    )
    db.add(event)
    db.flush()

    record_activity(
        db,
        team_id=team_id,
        session_id=session_id,
        actor=actor,
        actor_name=actor_name or subject_name,
        verb="xp.awarded",
        target_type="xp_event",
        target_id=event.id,
        payload={
            "amount": amount,
            "reason": xp_rules.rule(rule_key).label,
            "name": subject_name,
        },
    )
    return event


def reverse_award(db: DbSession, *, event: XpEvent, reason: str, actor, actor_name: str) -> XpEvent:
    """Corrections are new events. The original stays in the ledger."""
    reversal = XpEvent(
        team_id=event.team_id,
        user_id=event.user_id,
        guest_id=event.guest_id,
        subject_name=event.subject_name,
        amount=-event.amount,
        reason_key=event.reason_key,
        source_type="reversal",
        source_id=event.id,
        session_id=event.session_id,
        awarded_by=actor.user_id if actor else None,
        season_id=event.season_id,
        occurred_at=datetime.now(timezone.utc),
        idempotency_key=xp_rules.idempotency_key(
            "reversal", "xp_event", event.id, event.user_id or event.guest_id or event.id
        ),
    )
    db.add(reversal)
    db.flush()
    record_activity(
        db,
        team_id=event.team_id,
        session_id=event.session_id,
        actor=actor,
        actor_name=actor_name,
        verb="xp.reversed",
        target_type="xp_event",
        target_id=reversal.id,
        payload={"amount": event.amount, "reason": reason, "name": event.subject_name},
    )
    return reversal


def _subject_names(
    db: DbSession,
    totals: dict[uuid.UUID, int],
    kinds: dict[uuid.UUID, str],
    *,
    include_guests: bool,
) -> list[dict]:
    """Turn id -> points into named standings.

    Aggregating in Python rather than SQL keeps this readable and avoids
    Postgres-specific tricks on UUID columns; the ledger is small by design.
    """
    standings: list[dict] = []
    for subject_id, total in totals.items():
        if kinds.get(subject_id) == "user":
            user = db.get(User, subject_id)
            if user is None or user.leaderboard_opt_out:
                continue
            name, kind = user.display_name, "user"
        else:
            guest = db.get(Guest, subject_id)
            if guest is None:
                continue
            # A claimed guest now competes as the user they became.
            if guest.linked_user_id is not None or not include_guests:
                continue
            name, kind = guest.display_name, "guest"
        standings.append(
            {
                "id": str(subject_id),
                "name": name,
                "kind": kind,
                "points": int(total),
            }
        )
    standings.sort(key=lambda row: row["points"], reverse=True)
    for index, row in enumerate(standings, start=1):
        row["rank"] = index
    return standings


def leaderboard(
    db: DbSession,
    *,
    team_id: uuid.UUID,
    scope: str = "season",
    session_id: uuid.UUID | None = None,
) -> list[dict]:
    query = select(XpEvent).where(XpEvent.team_id == team_id)
    if scope == "session":
        if session_id is None:
            raise AppError("A session leaderboard needs a session.", code="leaderboard.no_session")
        query = query.where(XpEvent.session_id == session_id)
    elif scope == "season":
        season = ensure_season(db, team_id)
        query = query.where(XpEvent.season_id == season.id)
    elif scope != "all":
        raise AppError("Unknown leaderboard scope.", code="leaderboard.bad_scope")

    totals: dict[uuid.UUID, int] = {}
    kinds: dict[uuid.UUID, str] = {}
    for event in db.execute(query).scalars():
        subject_id = event.user_id or event.guest_id
        if subject_id is None:
            continue
        totals[subject_id] = totals.get(subject_id, 0) + event.amount
        kinds[subject_id] = "user" if event.user_id is not None else "guest"

    return _subject_names(db, totals, kinds, include_guests=scope == "session")


def my_points(db: DbSession, *, team_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    season = ensure_season(db, team_id)
    season_total = int(
        db.execute(
            select(func.coalesce(func.sum(XpEvent.amount), 0)).where(
                XpEvent.team_id == team_id,
                XpEvent.user_id == user_id,
                XpEvent.season_id == season.id,
            )
        ).scalar_one()
    )
    all_time = int(
        db.execute(
            select(func.coalesce(func.sum(XpEvent.amount), 0)).where(
                XpEvent.team_id == team_id, XpEvent.user_id == user_id
            )
        ).scalar_one()
    )
    recent = list(
        db.execute(
            select(XpEvent)
            .where(XpEvent.team_id == team_id, XpEvent.user_id == user_id)
            .order_by(XpEvent.occurred_at.desc())
            .limit(10)
        ).scalars()
    )
    return {
        "season": {"name": season.name, "points": season_total},
        "all_time": all_time,
        "recent": [
            {
                "reason": xp_rules.rule(event.reason_key).label
                if event.reason_key in xp_rules.DEFAULT_RULES
                else event.reason_key,
                "amount": event.amount,
                "at": event.occurred_at.isoformat(),
            }
            for event in recent
        ],
    }


# --- achievements --------------------------------------------------------------


def stats_for_user(db: DbSession, *, team_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, int]:
    def count(model, *conditions) -> int:
        return int(
            db.execute(select(func.count()).select_from(model).where(*conditions)).scalar_one()
        )

    attended = count(
        SessionParticipant,
        SessionParticipant.user_id == user_id,
        SessionParticipant.attended.is_(True),
    )
    ideas_authored = count(Idea, Idea.team_id == team_id, Idea.created_by == user_id)
    ideas_accepted = count(
        Idea,
        Idea.team_id == team_id,
        Idea.created_by == user_id,
        Idea.status.in_([IdeaStatus.ACCEPTED.value, IdeaStatus.CONVERTED.value]),
    )
    tasks_completed = count(
        Task,
        Task.team_id == team_id,
        Task.owner_id == user_id,
        Task.status == TaskStatus.DONE.value,
    )
    on_time = count(
        Task,
        Task.team_id == team_id,
        Task.owner_id == user_id,
        Task.status == TaskStatus.DONE.value,
        Task.due_date.is_not(None),
        func.date(Task.completed_at) <= Task.due_date,
    )
    blockers_resolved = count(Blocker, Blocker.team_id == team_id, Blocker.resolved_by == user_id)
    game_wins = count(
        GameScore,
        GameScore.user_id == user_id,
        GameScore.position == 1,
    )
    games_hosted = count(GamePlay, GamePlay.host_id == user_id)

    early_bird = count(
        XpEvent,
        XpEvent.team_id == team_id,
        XpEvent.user_id == user_id,
        XpEvent.reason_key == "early_bird",
    )
    comebacks = count(
        XpEvent,
        XpEvent.team_id == team_id,
        XpEvent.user_id == user_id,
        XpEvent.reason_key == "comeback",
    )

    return {
        "sessions_attended": attended,
        "session_streak": 0,
        "ideas_authored": ideas_authored,
        "ideas_accepted": ideas_accepted,
        "tasks_completed": tasks_completed,
        "tasks_completed_on_time": on_time,
        "blockers_resolved": blockers_resolved,
        "game_wins": game_wins,
        "games_hosted": games_hosted,
        "early_bird_count": early_bird,
        "comebacks": comebacks,
        "seasons_top_three": 0,
    }


def sync_achievements(db: DbSession, *, team_id: uuid.UUID, user_id: uuid.UUID) -> list[str]:
    """Award anything newly earned. Never revokes automatically."""
    stats = stats_for_user(db, team_id=team_id, user_id=user_id)
    newly: list[str] = []
    season = ensure_season(db, team_id)

    for key in achievement_rules.earned(stats):
        definition = db.execute(
            select(Achievement).where(Achievement.key == key)
        ).scalar_one_or_none()
        if definition is None:
            continue
        existing = db.execute(
            select(AchievementAward).where(
                AchievementAward.achievement_id == definition.id,
                AchievementAward.team_id == team_id,
                AchievementAward.user_id == user_id,
                AchievementAward.revoked_at.is_(None),
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue

        user = db.get(User, user_id)
        db.add(
            AchievementAward(
                achievement_id=definition.id,
                team_id=team_id,
                user_id=user_id,
                season_id=season.id,
                awarded_at=datetime.now(timezone.utc),
                source_type="system",
            )
        )
        db.flush()
        record_activity(
            db,
            team_id=team_id,
            actor=None,
            actor_name=user.display_name if user else "Someone",
            verb="achievement.awarded",
            target_type="achievement",
            target_id=definition.id,
            payload={
                "achievement": definition.name,
                "emoji": definition.emoji,
                "name": user.display_name if user else "Someone",
            },
        )
        newly.append(key)
    return newly


def achievements_overview(db: DbSession, *, team_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    stats = stats_for_user(db, team_id=team_id, user_id=user_id)
    awards = list(
        db.execute(
            select(AchievementAward).where(
                AchievementAward.team_id == team_id,
                AchievementAward.user_id == user_id,
                AchievementAward.revoked_at.is_(None),
            )
        ).scalars()
    )
    definitions = {row.id: row for row in db.execute(select(Achievement)).scalars()}
    return {
        "progress": achievement_rules.progress(stats),
        "awards": [
            {
                "key": definitions[award.achievement_id].key
                if award.achievement_id in definitions
                else "unknown",
                "name": definitions[award.achievement_id].name
                if award.achievement_id in definitions
                else "Unknown",
                "emoji": definitions[award.achievement_id].emoji
                if award.achievement_id in definitions
                else "🏆",
                "awarded_at": award.awarded_at.isoformat(),
            }
            for award in awards
        ],
    }


def revoke_achievement(
    db: DbSession, *, team_id: uuid.UUID, award_id: uuid.UUID, reason: str, actor, actor_name: str
) -> None:
    award = db.get(AchievementAward, award_id)
    if award is None or award.team_id != team_id:
        raise NotFoundError("That award does not exist.")
    award.revoked_at = datetime.now(timezone.utc)
    award.revoke_reason = reason
    db.flush()
    definition = db.get(Achievement, award.achievement_id)
    record_activity(
        db,
        team_id=team_id,
        actor=actor,
        actor_name=actor_name,
        verb="achievement.revoked",
        target_type="achievement",
        target_id=award.achievement_id,
        payload={
            "achievement": definition.name if definition else "an achievement",
            "reason": reason,
        },
    )


def team_metrics(db: DbSession, *, team_id: uuid.UUID) -> dict:
    """Serious numbers, deliberately unscored and unranked."""

    def count(model, *conditions) -> int:
        return int(
            db.execute(select(func.count()).select_from(model).where(*conditions)).scalar_one()
        )

    open_tasks = count(
        Task,
        Task.team_id == team_id,
        Task.status.in_(
            [TaskStatus.BACKLOG.value, TaskStatus.IN_PROGRESS.value, TaskStatus.BLOCKED.value]
        ),
        Task.deleted_at.is_(None),
    )
    blocked = count(
        Task,
        Task.team_id == team_id,
        Task.status == TaskStatus.BLOCKED.value,
        Task.deleted_at.is_(None),
    )
    done = count(
        Task,
        Task.team_id == team_id,
        Task.status == TaskStatus.DONE.value,
        Task.deleted_at.is_(None),
    )
    overdue = count(
        Task,
        Task.team_id == team_id,
        Task.deleted_at.is_(None),
        Task.due_date.is_not(None),
        Task.due_date < func.current_date(),
        Task.status.notin_([TaskStatus.DONE.value, TaskStatus.CANCELLED.value]),
    )
    open_blockers = count(Blocker, Blocker.team_id == team_id, Blocker.resolved_at.is_(None))

    by_owner: list[dict] = []
    rows = db.execute(
        select(Task.owner_id, func.count())
        .where(
            Task.team_id == team_id,
            Task.deleted_at.is_(None),
            Task.status.notin_([TaskStatus.DONE.value, TaskStatus.CANCELLED.value]),
        )
        .group_by(Task.owner_id)
    ).all()
    for owner_id, total in rows:
        user = db.get(User, owner_id) if owner_id else None
        by_owner.append(
            {"name": user.display_name if user else "Unassigned", "open_tasks": int(total)}
        )
    by_owner.sort(key=lambda row: row["open_tasks"], reverse=True)

    return {
        "open_tasks": open_tasks,
        "blocked": blocked,
        "completed": done,
        "overdue": overdue,
        "open_blockers": open_blockers,
        "by_owner": by_owner,
        "note": "Plain numbers, not a ranking. The leaderboard is elsewhere and is for fun.",
    }


def sessions_attended(db: DbSession, *, team_id: uuid.UUID, user_id: uuid.UUID) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(SessionParticipant)
            .join(MeetingSession, MeetingSession.id == SessionParticipant.session_id)
            .where(
                MeetingSession.team_id == team_id,
                SessionParticipant.user_id == user_id,
                SessionParticipant.attended.is_(True),
            )
        ).scalar_one()
    )
