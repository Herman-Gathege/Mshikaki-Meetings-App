/**
 * Small confirmation messages.

 * Every important action says what happened, in the fewest words possible. The
 * messages dismiss themselves: nobody should have to close a notification to get
 * on with their meeting.
 */

import { useEffect, useState } from "react";

type Toast = { id: number; message: string };

let listeners: ((item: Toast) => void)[] = [];
let nextId = 1;

export function toast(message: string): void {
  const item = { id: nextId, message };
  nextId += 1;
  listeners.forEach((listener) => listener(item));
}

const DURATION_MS = 2600;

export function Toaster() {
  const [items, setItems] = useState<Toast[]>([]);

  useEffect(() => {
    const listener = (item: Toast) => {
      setItems((current) => [...current, item]);
      setTimeout(
        () => setItems((current) => current.filter((entry) => entry.id !== item.id)),
        DURATION_MS,
      );
    };
    listeners.push(listener);
    return () => {
      listeners = listeners.filter((entry) => entry !== listener);
    };
  }, []);

  if (items.length === 0) return null;

  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed bottom-24 left-1/2 z-[70] flex -translate-x-1/2 flex-col items-center gap-2 lg:bottom-8"
    >
      {items.map((item) => (
        <p
          key={item.id}
          className="rounded-full bg-ink-900 px-5 py-3 text-sm font-medium text-white shadow-lg"
        >
          {item.message}
        </p>
      ))}
    </div>
  );
}
