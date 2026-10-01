/**
 * Start the meeting, then go straight into it.

 * Pressing "Start session" used to change a badge and leave the person on the
 * same page, which reads as nothing having happened. Starting a meeting and
 * entering it are one action from the user's point of view, so they are one
 * action here.
 */

import { useNavigate } from "react-router-dom";

import { useSessionLifecycle } from "@/api/hooks";
import { toast } from "@/components/toast";
import { Button } from "@/components/ui/kit";

export function StartSessionButton({
  sessionId,
  label = "Start session →",
  size = "lg",
  variant = "primary",
}: {
  sessionId: string;
  label?: string;
  size?: "sm" | "md" | "lg" | "xl";
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
}) {
  const lifecycle = useSessionLifecycle(sessionId);
  const navigate = useNavigate();

  return (
    <Button
      size={size}
      variant={variant}
      disabled={lifecycle.start.isPending}
      onClick={() =>
        void lifecycle.start.mutateAsync().then(() => {
          toast("🎲 Let's play!");
          navigate(`/sessions/${sessionId}/run`);
        })
      }
    >
      {lifecycle.start.isPending ? "Starting…" : label}
    </Button>
  );
}
