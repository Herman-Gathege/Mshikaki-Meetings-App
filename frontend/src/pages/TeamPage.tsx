import { useState } from "react";

import {
  useAchievements,
  useChangeRole,
  useCreateGuest,
  useCreateInvite,
  useGuests,
  useMe,
  useMembers,
  useMyPoints,
  useTeam,
  useUpdatePreferences,
} from "@/api/hooks";
import { LoadingState, PageHeader, ErrorState } from "@/components/states";
import { JoinQr, QrOverlay, joinUrlFor } from "@/components/JoinQr";
import { toast } from "@/components/toast";
import { Button, Card, Field, Input, Select } from "@/components/ui/kit";

export function TeamPage() {
  const team = useTeam();
  const members = useMembers();
  const guests = useGuests();
  const invites = useCreateInvite();
  const createGuest = useCreateGuest();
  const changeRole = useChangeRole();
  const preferences = useUpdatePreferences();
  const points = useMyPoints();
  const achievements = useAchievements();
  const me = useMe();
  const [guestName, setGuestName] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [code, setCode] = useState("");
  const [qrOpen, setQrOpen] = useState(false);
  const leaderboardHidden = me.data?.user.leaderboard_opt_out ?? false;

  function toggleLeaderboard() {
    const next = !leaderboardHidden;
    preferences
      .mutateAsync({ leaderboard_opt_out: next })
      .then(() => toast(next ? "🙈 Hidden from the standings" : "😎 Back on the standings"))
      .catch(() => toast("Could not update your preference. Try again."));
  }

  if (team.isPending) return <LoadingState />;
  if (team.isError) return <ErrorState error={team.error} />;

  return (
    <>
      <PageHeader
        title={team.data?.name ?? "Team"}
        subtitle={`${members.data?.items.length ?? 0} members · ${team.data?.timezone ?? ""}`}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 text-sm font-semibold text-ink-800">Members</h2>
          <ul className="space-y-3">
            {(members.data?.items ?? []).map((member) => (
              <li key={member.membership_id} className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">{member.name}</p>
                  <p className="text-xs text-ink-600">{member.email}</p>
                </div>
                <Select
                  className="w-32"
                  value={member.role}
                  onChange={(event) =>
                    void changeRole.mutateAsync({
                      membershipId: member.membership_id,
                      role: event.target.value,
                    })
                  }
                >
                  {["owner", "admin", "facilitator", "member"].map((role) => (
                    <option key={role} value={role}>
                      {role}
                    </option>
                  ))}
                </Select>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <h2 className="mb-3 text-sm font-semibold text-ink-800">Invite someone</h2>
          <div className="flex gap-2">
            <Select className="w-32" value={inviteRole} onChange={(event) => setInviteRole(event.target.value)}>
              {["member", "facilitator", "admin"].map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </Select>
            <Button
              onClick={() =>
                void invites.mutateAsync({ role: inviteRole }).then((invite) => setCode(invite.code))
              }
            >
              Create code
            </Button>
          </div>
          {code ? (
            <div className="mt-4 flex flex-wrap items-start gap-4">
              <JoinQr
                url={joinUrlFor(code)}
                className="size-32 shrink-0 rounded-lg border border-ink-200 p-1 [&>svg]:h-full [&>svg]:w-full"
              />
              <div className="min-w-0 text-sm">
                <p className="font-mono text-base font-semibold">{code}</p>
                <p className="mt-1 text-xs break-all text-ink-600">{joinUrlFor(code)}</p>
                <Button size="sm" className="mt-2" onClick={() => setQrOpen(true)}>
                  Show big for the room
                </Button>
              </div>
            </div>
          ) : null}

          <h2 className="mt-6 mb-3 text-sm font-semibold text-ink-800">Guests</h2>
          <div className="flex gap-2">
            <Input
              value={guestName}
              placeholder="Name"
              onChange={(event) => setGuestName(event.target.value)}
            />
            <Button
              variant="outline"
              disabled={!guestName.trim()}
              onClick={() =>
                void createGuest.mutateAsync({ display_name: guestName }).then(() => setGuestName(""))
              }
            >
              Add
            </Button>
          </div>
          <ul className="mt-3 space-y-1 text-sm">
            {(guests.data?.items ?? []).map((guest) => (
              <li key={guest.id}>
                {guest.display_name}
                {guest.linked_user_id ? " (linked)" : ""}
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <h2 className="mb-3 text-sm font-semibold text-ink-800">Your bragging rights</h2>
          {points.data ? (
            <p className="text-sm">
              {points.data.season.name}: <strong>{points.data.season.points} XP</strong> · all time{" "}
              {points.data.all_time} XP
            </p>
          ) : null}
          <ul className="mt-3 space-y-1 text-sm">
            {(achievements.data?.progress ?? [])
              .filter((item) => item.earned)
              .map((item) => (
                <li key={item.key}>
                  {item.emoji} {item.name}
                </li>
              ))}
            {(achievements.data?.awards ?? []).length === 0 ? (
              <li className="text-ink-600">Nothing yet. Play a game.</li>
            ) : null}
          </ul>
          <Field label="Leaderboard">
            <Button
              variant="outline"
              className="mt-2"
              disabled={preferences.isPending || !me.data}
              onClick={toggleLeaderboard}
            >
              {leaderboardHidden ? "Show me in standings" : "Hide me from standings"}
            </Button>
          </Field>
          <p className="mt-2 text-xs text-ink-600">
            {leaderboardHidden
              ? "You are hidden from the table. You still earn XP, and you can show yourself again whenever you like."
              : "Opting out is private: you still earn XP, you just do not appear in the table."}
          </p>
        </Card>
      </div>

      {code ? (
        <QrOverlay url={joinUrlFor(code)} code={code} open={qrOpen} onClose={() => setQrOpen(false)} />
      ) : null}
    </>
  );
}
