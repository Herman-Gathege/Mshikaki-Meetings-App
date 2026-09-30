import { type VariantProps, cva } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * shadcn/ui convention: the component source lives in the repository and you own
 * it. Only the variants this app actually uses are defined; add more by extending
 * the cva map rather than wrapping this component in another abstraction.
 */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember-500",
  {
    variants: {
      variant: {
        primary: "bg-ember-600 text-white hover:bg-ember-500",
        secondary: "bg-ink-900 text-white hover:bg-ink-800",
        outline: "border border-ink-200 bg-white hover:bg-ink-100",
        ghost: "hover:bg-ink-100",
      },
      size: {
        // 44px minimum height: the touch target rule from the design notes.
        md: "h-11 px-4",
        lg: "h-14 px-6 text-base",
        sm: "h-11 px-3",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>;

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
