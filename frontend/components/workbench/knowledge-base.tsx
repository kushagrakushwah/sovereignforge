"use client";

import { useState } from "react";
import { CaretDown, CircleNotch, Database, Plus, Trash } from "@phosphor-icons/react";
import type { KnowledgeBaseState } from "@/hooks/use-knowledge-base";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { AnimatedNumber } from "@/components/motion/animated-number";

interface KnowledgeBaseProps {
  kb: KnowledgeBaseState;
  onIngest: () => void;
  defaultOpen?: boolean;
  className?: string;
}

export function KnowledgeBase({ kb, onIngest, defaultOpen = false, className }: KnowledgeBaseProps) {
  const [open, setOpen] = useState(defaultOpen);
  const { stats, reachable, busy } = kb;
  const sources = Object.entries(stats?.sources ?? {}).sort((a, b) => b[1] - a[1]);
  const chunks = stats?.total_chunks ?? 0;

  return (
    <Collapsible open={open} onOpenChange={setOpen} className={cn("panel", className)}>
      <CollapsibleTrigger className="group/kb flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left transition-colors hover:bg-foreground/[0.02]">
        <Database weight="light" className="size-4 text-muted-foreground" />
        <span className="text-[13px] font-medium">Knowledge base</span>
        <span className="ml-auto flex items-center gap-2 font-mono text-[11px] text-faint">
          {!reachable ? (
            "unreachable"
          ) : stats === null ? (
            "…"
          ) : chunks > 0 ? (
            <>
              <AnimatedNumber value={chunks} className="text-foreground/85" />
              chunks
            </>
          ) : (
            "empty"
          )}
        </span>
        <CaretDown
          weight="light"
          className="size-3.5 text-faint transition-transform duration-300 ease-expo group-data-[state=open]/kb:rotate-180"
        />
      </CollapsibleTrigger>

      <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
        <div className="flex flex-col gap-3 border-t border-line px-4 pt-3 pb-4">
          {sources.length > 0 ? (
            <ul className="flex max-h-44 flex-col overflow-y-auto">
              {sources.map(([source, count]) => (
                <li key={source} className="flex items-baseline gap-3 py-1 text-xs">
                  <span className="min-w-0 flex-1 truncate text-foreground/80" title={source}>
                    {source}
                  </span>
                  <span className="tabular font-mono text-[11px] text-faint">{count}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs leading-relaxed text-muted-foreground">
              Index SOPs, manuals and past reports so the agent can cite them in its answers.
            </p>
          )}

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onIngest}
              disabled={busy !== null || !reachable}
              className="border-line"
            >
              {busy === "ingest" ? (
                <CircleNotch className="animate-spin" data-icon="inline-start" />
              ) : (
                <Plus weight="light" data-icon="inline-start" />
              )}
              {busy === "ingest" ? "Indexing" : "Add document"}
            </Button>

            {chunks > 0 && (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="ghost" size="sm" disabled={busy !== null} className="ml-auto text-faint hover:text-destructive">
                    <Trash weight="light" data-icon="inline-start" />
                    Clear
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Clear the knowledge base?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This removes {chunks.toLocaleString("en-US")} chunks from {sources.length}{" "}
                      {sources.length === 1 ? "source" : "sources"}. The agent will no longer be able to cite them.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Keep</AlertDialogCancel>
                    <AlertDialogAction variant="destructive" onClick={kb.clear}>
                      Clear all
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}
          </div>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
