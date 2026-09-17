"use client";

import { ArrowCounterClockwise } from "@phosphor-icons/react";
import type { Run } from "@/lib/events";
import { Button } from "@/components/ui/button";
import { Kbd, KbdGroup } from "@/components/ui/kbd";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { RunStatus } from "@/components/workbench/run-status";
import { StatusDot } from "@/components/workbench/status-dot";
import { Wordmark } from "@/components/workbench/wordmark";
import { useModKey } from "@/hooks/use-mod-key";

interface TopBarProps {
  run: Run;
  startedAt: number | null;
  connected: boolean;
  onReset: () => void;
  onOpenCommands: () => void;
}

export function TopBar({ run, startedAt, connected, onReset, onOpenCommands }: TopBarProps) {
  const mod = useModKey();
  const canReset = run.status !== "idle" && run.status !== "running";

  return (
    <header className="flex h-14 shrink-0 items-center gap-4 px-4 md:px-5">
      <Wordmark />
      <span aria-hidden className="hidden h-4 w-px bg-line-strong md:block" />
      <span className="label-mono hidden md:inline">Workbench</span>

      <div className="ml-auto flex items-center gap-3 md:gap-5">
        {run.status !== "idle" && <RunStatus run={run} startedAt={startedAt} className="hidden sm:flex" />}

        {run.classification && (
          <span className="hidden items-center gap-1.5 rounded-md border border-line px-2 py-1 font-mono text-[11px] text-muted-foreground lg:inline-flex">
            <span className="text-foreground/85">{run.classification.model_key}</span>
            <span className="text-faint">/</span>
            {run.classification.task_type}
          </span>
        )}

        <Tooltip>
          <TooltipTrigger asChild>
            <span className="flex items-center gap-2 font-mono text-[11px] tracking-[0.06em] text-muted-foreground uppercase">
              <StatusDot tone={connected ? "idle" : "alert"} />
              <span className="hidden md:inline">{connected ? "Agent linked" : "Agent offline"}</span>
            </span>
          </TooltipTrigger>
          <TooltipContent>
            {connected ? "WebSocket to the local agent is open" : "Reconnecting to the backend every 3 seconds"}
          </TooltipContent>
        </Tooltip>

        {canReset && (
          <Button variant="ghost" size="sm" onClick={onReset} className="text-muted-foreground">
            <ArrowCounterClockwise weight="light" data-icon="inline-start" />
            New task
          </Button>
        )}

        <Button
          variant="outline"
          size="sm"
          onClick={onOpenCommands}
          className="gap-2 border-line bg-transparent pr-1.5 text-muted-foreground dark:bg-transparent"
          aria-label="Open command menu"
        >
          <span className="hidden sm:inline">Commands</span>
          <KbdGroup>
            <Kbd className="bg-secondary font-mono">{mod}</Kbd>
            <Kbd className="bg-secondary font-mono">K</Kbd>
          </KbdGroup>
        </Button>
      </div>
    </header>
  );
}
