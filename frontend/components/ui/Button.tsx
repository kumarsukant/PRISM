import Link from "next/link";
import type { ComponentProps } from "react";

type Variant = "primary" | "secondary" | "tertiary";
type Size = "sm" | "md" | "lg";

const base =
  "inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-600";

const variants: Record<Variant, string> = {
  // Brand guidelines: Amber-500 fill, Amber-400 hover, Amber-600 active.
  primary: "bg-amber-500 text-on-brand shadow-card hover:bg-amber-400 active:bg-amber-600",
  secondary: "border border-amber-500 text-link hover:bg-tint",
  tertiary:
    "bg-gray-100 text-gray-800 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-700",
};

const sizes: Record<Size, string> = {
  sm: "h-9 px-4 text-sm",
  md: "h-11 px-5 text-base",
  lg: "h-12 px-6 text-base",
};

type ButtonLinkProps = ComponentProps<typeof Link> & { variant?: Variant; size?: Size };

export function ButtonLink({ variant = "primary", size = "md", className = "", ...props }: ButtonLinkProps) {
  return <Link className={`${base} ${variants[variant]} ${sizes[size]} ${className}`} {...props} />;
}
