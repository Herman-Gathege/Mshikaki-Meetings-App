/**
 * The join link as a QR code.

 * Rendered locally by the `qrcode` package - no image service, because this app
 * runs on an internal network where an outbound call would simply hang.

 * `QrOverlay` is the projector view: one huge code, a close button, Esc, or a
 * click anywhere. It is a plain overlay over whatever is on screen, so opening
 * and closing it cannot change any state.
 */

import QRCode from "qrcode";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/kit";

export function joinUrlFor(code: string): string {
  // Short by design: fewer characters means a coarser code, which is easier to
  // scan from the back of a room.
  return `${window.location.origin}/join/${code}`;
}

/** Returns the SVG source for a string, or null while it is being generated. */
function useQrSvg(text: string): string | null {
  const [svg, setSvg] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setSvg(null);
    QRCode.toString(text, {
      type: "svg",
      margin: 1,
      errorCorrectionLevel: "M",
      color: { dark: "#12100f", light: "#ffffff" },
    })
      .then((value) => {
        if (alive) setSvg(value);
      })
      .catch(() => {
        if (alive) setSvg(null);
      });
    return () => {
      alive = false;
    };
  }, [text]);

  return svg;
}

export function JoinQr({ url, className }: { url: string; className?: string }) {
  const svg = useQrSvg(url);

  if (!svg) {
    return (
      <div className={`flex items-center justify-center text-xs text-ink-400 ${className ?? ""}`}>
        Generating…
      </div>
    );
  }

  return (
    <div
      className={className}
      // The SVG comes from the encoder, not from user input.
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

export function QrOverlay({
  url,
  code,
  open,
  onClose,
}: {
  url: string;
  code: string;
  open: boolean;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Scan to join"
      onClick={onClose}
      className="fixed inset-0 z-[60] flex flex-col items-center justify-center gap-4 bg-ink-900/95 p-6 text-white"
    >
      <Button
        variant="ghost"
        className="absolute top-4 right-4 text-white hover:bg-white/10"
        onClick={onClose}
      >
        Close ✕
      </Button>

      <p className="text-2xl font-semibold sm:text-4xl">Scan to join</p>

      {/* Large enough to read from the back row, square on any screen. */}
      <div
        className="rounded-3xl bg-white p-4 sm:p-8"
        onClick={(event) => event.stopPropagation()}
      >
        <JoinQr
          url={url}
          className="h-[min(62vh,72vw)] w-[min(62vh,72vw)] [&>svg]:h-full [&>svg]:w-full"
        />
      </div>

      <p className="font-mono text-lg break-all sm:text-2xl">{url}</p>
      <p className="text-sm text-white/60">
        or enter the code <span className="font-mono font-semibold text-white">{code}</span>
      </p>
      <p className="text-xs text-white/40">Press Esc or click anywhere to close</p>
    </div>
  );
}
