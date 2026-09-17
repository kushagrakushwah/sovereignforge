"use client";

import { useEffect, useState } from "react";
import { formatSeconds, pad, type Run } from "@/lib/events";
import { cn } from "@/lib/utils";
import { StatusDot } from "@/components/workbench/status-dot";

/** Seconds since `since`, ticking while `active`. */
export function useElapsed(since: number | null, active: boolean) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => setNow(Date.now()), 100);
    return () => clearInterval(id);
  }, [active]);
  return since ? Math.max(0, (now - since) / 1000) : 0;
}

export function RunStatus({
  run,
  startedAt,
  className,
}: {
  run: Run;
  startedAt: number | null;
  className?: string;
}) {
  const running = run.status === "running";
  const elapsed = useElapsed(startedAt, running);
  const step = run.steps.at(-1)?.iteration;

  let tone: "live" | "idle" | "alert" = "idle";
  let label: string;
  let detail: string | undefined;

  switch (run.status) {
    case "running":
      tone = "live";
      label = step ? `Executing · step ${pad(step)}` : "Routing";
      detail = formatSeconds(elapsed);
      break;
    case "done":
      label = "Complete";
      detail = run.finish?.total_elapsed_s !== undefined ? formatSeconds(run.finish.total_elapsed_s) : undefined;
      break;
    case "timeout":
      tone = "alert";
      label = "Halted · step limit";
      break;
    case "blocked":
      tone = "alert";
      label = "Blocked by guardrail";
      break;
    case "failed":
      tone = "alert";
      label = "Failed";
      break;
    default:
      label = "Ready";
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn("flex items-center gap-2 font-mono text-[11px] tracking-[0.06em] uppercase", className)}
    >
      <StatusDot tone={tone} />
      <span className={cn(tone === "alert" ? "text-destructive" : "text-foreground/85")}>{label}</span>
      {detail && <span className="tabular text-faint">{detail}</span>}
    </div>
  );
}
