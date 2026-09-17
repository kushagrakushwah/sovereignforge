import { cn } from "@/lib/utils";

type Tone = "live" | "idle" | "off" | "alert";

/** A small status light. `live` breathes; `alert` is the only colored state. */
export function StatusDot({ tone, className }: { tone: Tone; className?: string }) {
  return (
    <span aria-hidden className={cn("relative inline-flex size-1.5 shrink-0", className)}>
      {tone === "live" && <span className="absolute inset-0 rounded-full bg-foreground/60 animate-breathe" />}
      <span
        className={cn(
          "relative size-1.5 rounded-full",
          tone === "live" && "bg-foreground",
          tone === "idle" && "bg-foreground/45",
          tone === "off" && "border border-foreground/30 bg-transparent",
          tone === "alert" && "bg-destructive shadow-[0_0_0_3px_color-mix(in_oklch,var(--destructive),transparent_80%)]",
        )}
      />
    </span>
  );
}
