import { clsx } from "clsx"
import { twMerge } from "tailwind-merge"

// Utility function pour combiner les classes CSS (principe DRY)
export function cn(...inputs) {
  return twMerge(clsx(inputs))
}