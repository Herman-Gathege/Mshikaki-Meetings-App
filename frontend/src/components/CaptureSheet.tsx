/**
 * The five-second capture.

 * Reachable from anywhere (the floating button, or the capture step in Run Mode).
 * Title only, no required fields, no navigation away from what you were doing -
 * the whole point is that nobody loses their train of thought.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useCreateIdea } from "@/api/hooks";
import { useSessions } from "@/api/hooks";
import { Button, Field, Input, Modal, Select, Textarea } from "@/components/ui/kit";

export function CaptureSheet({
  open,
  onClose,
  defaultSessionId,
}: {
  open: boolean;
  onClose: () => void;
  defaultSessionId?: string;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [sessionId, setSessionId] = useState(defaultSessionId ?? "");
  const createIdea = useCreateIdea();
  const sessions = useSessions();
  const navigate = useNavigate();

  const submit = async () => {
    if (!title.trim()) return;
    const idea = await createIdea.mutateAsync({
      title: title.trim(),
      description: description.trim() || undefined,
      session_id: sessionId || undefined,
    });
    setTitle("");
    setDescription("");
    onClose();
    navigate(`/ideas/${idea.id}`);
  };

  return (
    <Modal open={open} title="Capture an idea" onClose={onClose}>
      <div className="space-y-4">
        <Field label="What is the idea?">
          <Input
            autoFocus
            value={title}
            placeholder="Automate radio schedule notifications"
            onChange={(event) => setTitle(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void submit();
            }}
          />
        </Field>
        <Field label="Anything else?" hint="Optional. You can add detail later.">
          <Textarea
            rows={3}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </Field>
        <Field label="From this meeting?" hint="Optional.">
          <Select value={sessionId} onChange={(event) => setSessionId(event.target.value)}>
            <option value="">Not from a meeting</option>
            {(sessions.data?.items ?? []).map((session) => (
              <option key={session.id} value={session.id}>
                {session.title}
              </option>
            ))}
          </Select>
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            size="lg"
            disabled={!title.trim() || createIdea.isPending}
            onClick={() => void submit()}
          >
            {createIdea.isPending ? "Saving..." : "Save idea"}
          </Button>
        </div>
        {createIdea.isError ? (
          <p className="text-sm text-red-700">
            {createIdea.error instanceof Error ? createIdea.error.message : "Could not save."}
          </p>
        ) : null}
      </div>
    </Modal>
  );
}
