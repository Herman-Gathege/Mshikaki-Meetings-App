import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind classes, letting later classes win.
 * The one utility every component shares.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
