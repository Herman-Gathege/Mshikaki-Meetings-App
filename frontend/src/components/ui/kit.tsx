/**
 * The primitives the app actually uses, in one place.
 *
 * These follow the shadcn/ui idea - you own the source, you edit it here - but
 * they are grouped in a single file rather than one file per component, because
 * this app needs eight primitives, not eighty. Add to this file instead of
 * layering a second abstraction on top.
 */

import { type VariantProps, cva } from "class-variance-authority";
import { Link } from "react-router-dom";
import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember-500",
  {
    variants: {
      variant: {
        primary: "bg-ember-600 text-white hover:bg-ember-500",
        secondary: "bg-ink-900 text-white hover:bg-ink-800",
        outline: "border border-ink-200 bg-white hover:bg-ink-100",
        ghost: "hover:bg-ink-100",
        danger: "border border-red-200 bg-white text-red-700 hover:bg-red-50",
      },
      size: {
        // 44px minimum: the touch-target rule. Run Mode uses "xl" for the room.
        sm: "h-11 px-3",
        md: "h-11 px-4",
        lg: "h-14 px-6 text-base",
        xl: "h-16 px-8 text-lg",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>;

export function Button({ className, variant, size, type, ...props }: ButtonProps) {
  return (
    <button
      type={type ?? "button"}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
}

/**
 * A link that looks like a button.

 * Navigation must stay a link: a <button> inside an <a> is invalid HTML and a
 * screen reader announces both, which is noise. Use this whenever a button-like
 * thing is really a destination or a download.
 */
export function ButtonLink({
  to,
  href,
  download,
  target,
  rel,
  variant,
  size,
  className,
  children,
  onClick,
}: {
  to?: string;
  href?: string;
  download?: boolean | string;
  target?: string;
  rel?: string;
  className?: string;
  children: ReactNode;
  onClick?: () => void;
} & VariantProps<typeof buttonVariants>) {
  const classes = cn(buttonVariants({ variant, size }), className);

  if (to) {
    return (
      <Link to={to} className={classes} onClick={onClick}>
        {children}
      </Link>
    );
  }
  return (
    <a href={href} className={classes} download={download} target={target} rel={rel} onClick={onClick}>
      {children}
    </a>
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        // Text colour is stated, never inherited: these fields sit on dark
        // screens too, where inherited colour would be white on white.
        "h-11 w-full rounded-lg border border-ink-200 bg-white px-3 text-base text-ink-900 outline-none placeholder:text-ink-600 focus-visible:border-ember-500",
        className,
      )}
      {...props}
    />
  );
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "w-full rounded-lg border border-ink-200 bg-white p-3 text-base text-ink-900 outline-none placeholder:text-ink-600 focus-visible:border-ember-500",
        className,
      )}
      {...props}
    />
  );
}

export function Select({ className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-11 w-full rounded-lg border border-ink-200 bg-white px-3 text-base text-ink-900 outline-none focus-visible:border-ember-500",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="block text-sm font-medium text-ink-800">{label}</span>
      {children}
      {hint ? <span className="block text-xs text-ink-600">{hint}</span> : null}
    </label>
  );
}

export function Card({
  className,
  children,
  as: Tag = "section",
}: {
  className?: string;
  children: ReactNode;
  as?: "section" | "article" | "li" | "div";
}) {
  return (
    <Tag className={cn("rounded-card border border-ink-200 bg-white p-4", className)}>
      {children}
    </Tag>
  );
}

const badgeTones: Record<string, string> = {
  neutral: "bg-ink-100 text-ink-800",
  ember: "bg-ember-500/15 text-ember-700",
  nile: "bg-nile-500/15 text-nile-700",
  danger: "bg-red-100 text-red-700",
  success: "bg-emerald-100 text-emerald-700",
};

export function Badge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: keyof typeof badgeTones;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
        badgeTones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Modal({
  open,
  title,
  onClose,
  children,
  wide = false,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink-900/40 p-0 sm:items-center sm:p-6">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn(
          "max-h-[92dvh] w-full overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl",
          wide ? "sm:max-w-2xl" : "sm:max-w-lg",
        )}
      >
        <div className="mb-4 flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold">{title}</h2>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close">
            Close
          </Button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-ink-600">
      <span className="size-4 animate-spin rounded-full border-2 border-ink-200 border-t-ember-500" />
      {label}
    </span>
  );
}
