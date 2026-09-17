"use client";

import { useEffect, useRef } from "react";
import {
  CaretRight,
  Check,
  FlagCheckered,
  GitBranch,
  ShieldWarning,
  WarningOctagon,
  X,
} from "@phosphor-icons/react";
import {
  formatSeconds,
  isTerminal,
  pad,
  summarizeResult,
  toolLabel,
  type Run,
  type Step,
  type TraceEvent,
} from "@/lib/events";
import { cn } from "@/lib/utils";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { gsap, motionAllowed, useGSAP } from "@/components/motion/gsap";
import { StatusDot } from "@/components/workbench/status-dot";
import { ToolIcon } from "@/components/workbench/tool-icon";

interface ExecutionTraceProps {
  run: Run;
  startedAt: number | null;
  className?: string;
}

export function ExecutionTrace({ run, startedAt, className }: ExecutionTraceProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const stick = useRef(true);
  const running = run.status === "running";

  // Follow new output unless the reader has scrolled up.
  useEffect(() => {
    const el = scrollRef.current;
    if (el && stick.current) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [run]);

  const since = (at: number) => (startedAt ? `+${formatSeconds(Math.max(0, (at - startedAt) / 1000))}` : "");

  return (
    <section data-panel className={cn("panel flex min-h-0 flex-col", className)} aria-label="Execution trace">
      <header className="flex h-11 shrink-0 items-center gap-3 border-b border-line px-4">
        <h2 className="label-mono text-muted-foreground">Execution trace</h2>
        <span className="ml-auto flex items-center gap-3 font-mono text-[11px] text-faint">
          <span>
            <span className="tabular text-foreground/80">{pad(run.steps.length)}</span> steps
          </span>
          <span>
            <span className="tabular text-foreground/80">{pad(run.toolCalls)}</span> tool calls
          </span>
        </span>
      </header>

      <div
        ref={scrollRef}
        onScroll={(e) => {
          const el = e.currentTarget;
          stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 96;
        }}
        className="min-h-0 flex-1 overflow-y-auto px-4 pt-5 pb-2"
      >
        <ol className="flex flex-col">
          {run.preamble.map((event) => (
            <PreambleNode key={event.id} event={event} run={run} />
          ))}

          {running && run.steps.length === 0 && (
            <Node marker={<StatusDot tone="live" />}>
              <p className="text-shimmer text-[13px]">Routing task to a local model</p>
            </Node>
          )}

          {run.steps.map((step, i) => (
            <StepNode
              key={step.iteration + ":" + step.at}
              step={step}
              offset={since(step.at)}
              live={running && i === run.steps.length - 1}
            />
          ))}

          <TerminalNode run={run} />
        </ol>
      </div>
    </section>
  );
}

// ── Node chrome ─────────────────────────────────────────────────────────────

function Node({ marker, children }: { marker: React.ReactNode; children: React.ReactNode }) {
  const ref = useRef<HTMLLIElement>(null);

  useGSAP(
    () => {
      if (!motionAllowed() || !ref.current) return;
      const tl = gsap.timeline();
      tl.from(ref.current.querySelector("[data-node-body]"), { autoAlpha: 0, y: 10, duration: 0.6 });
      tl.from(ref.current.querySelector("[data-node-marker]"), { scale: 0, duration: 0.5, ease: "back.out(2)" }, 0);
      tl.from(
        ref.current.querySelector("[data-rail]"),
        { scaleY: 0, transformOrigin: "top center", duration: 0.9, ease: "expo.inOut" },
        0.1,
      );
    },
    { scope: ref },
  );

  return (
    <li ref={ref} className="group/node relative pb-6 pl-8 last:pb-2">
      <span data-rail aria-hidden className="absolute top-5 bottom-0 left-[7px] w-px bg-line group-last/node:hidden" />
      <span data-node-marker aria-hidden className="absolute top-[3px] left-0 grid size-[15px] place-items-center">
        {marker}
      </span>
      <div data-node-body>{children}</div>
    </li>
  );
}

const Diamond = ({ filled }: { filled?: boolean }) => (
  <span className={cn("size-[7px] rotate-45 border border-foreground/50", filled ? "bg-foreground" : "bg-background")} />
);

function NodeTitle({ children, meta }: { children: React.ReactNode; meta?: React.ReactNode }) {
  return (
    <div className="flex items-baseline gap-3">
      <h3 className="text-[13px] font-medium text-foreground">{children}</h3>
      {meta && <span className="ml-auto shrink-0 font-mono text-[11px] text-faint tabular">{meta}</span>}
    </div>
  );
}

// ── Nodes ───────────────────────────────────────────────────────────────────

function PreambleNode({ event, run }: { event: TraceEvent; run: Run }) {
  const d = event.data;
  switch (event.type) {
    case "classified": {
      const c = run.classification;
      if (!c) return null;
      return (
        <Node marker={<GitBranch weight="light" className="size-3.5 text-muted-foreground" />}>
          <NodeTitle meta={`${Math.round(c.confidence * 100)}% match`}>
            Routed to <span className="font-mono text-[12.5px]">{c.model_key}</span>
          </NodeTitle>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            <span className="font-mono text-foreground/70">{c.task_type}</span>
            {c.reasoning && <> · {c.reasoning}</>}
          </p>
        </Node>
      );
    }
    case "agent_start":
      return null;
    case "guardrail_block":
      return (
        <Node marker={<ShieldWarning weight="light" className="size-3.5 text-destructive" />}>
          <GuardrailBody data={d} />
        </Node>
      );
    case "error":
      return (
        <Node marker={<WarningOctagon weight="light" className="size-3.5 text-destructive" />}>
          <ErrorBody data={d} recoverable={false} />
        </Node>
      );
    default:
      return null;
  }
}

function StepNode({ step, offset, live }: { step: Step; offset: string; live: boolean }) {
  const items = groupItems(step.events);
  const hasThought = step.events.some((e) => e.type === "thought");

  return (
    <Node marker={live ? <StatusDot tone="live" /> : <Diamond />}>
      <NodeTitle meta={offset}>
        <span className="font-mono text-[11px] tracking-[0.14em] text-muted-foreground uppercase">
          Step {pad(step.iteration)}
        </span>
      </NodeTitle>

      <div className="mt-2.5 flex flex-col gap-3">
        {items.length === 0 && live && <p className="text-shimmer text-[13px]">Reasoning</p>}
        {items.map((item) => {
          switch (item.kind) {
            case "stream":
              return (
                <StreamItem
                  key={item.event.id}
                  text={String(item.event.data.text ?? "")}
                  live={live && !hasThought}
                />
              );
            case "thought":
              return <ThoughtItem key={item.event.id} data={item.event.data} />;
            case "tool":
              return <ToolItem key={item.call.id} call={item.call} result={item.result} live={live} />;
            case "error":
              return (
                <ErrorBody
                  key={item.event.id}
                  data={item.event.data}
                  recoverable={!isTerminal(item.event, true)}
                />
              );
            case "guard":
              return <GuardrailBody key={item.event.id} data={item.event.data} />;
          }
        })}
      </div>
    </Node>
  );
}

function TerminalNode({ run }: { run: Run }) {
  if (run.status === "done" && run.finish) {
    const t = run.finish.total_elapsed_s;
    return (
      <Node marker={<FlagCheckered weight="light" className="size-3.5 text-foreground" />}>
        <NodeTitle meta={t !== undefined ? formatSeconds(t) : undefined}>Answer composed</NodeTitle>
        <p className="mt-1 text-xs text-muted-foreground">
          {run.artifacts.length > 0
            ? `${run.artifacts.length} ${run.artifacts.length === 1 ? "artifact" : "artifacts"} ready in the output panel.`
            : "See the output panel."}
        </p>
      </Node>
    );
  }
  if (run.status === "timeout" || (run.status === "failed" && !hasFailureNode(run))) {
    return (
      <Node marker={<WarningOctagon weight="light" className="size-3.5 text-destructive" />}>
        <NodeTitle>{run.status === "timeout" ? "Stopped at the step limit" : "Run ended"}</NodeTitle>
        <p className="mt-1 text-xs leading-relaxed text-destructive/85">{run.failure}</p>
      </Node>
    );
  }
  return null;
}

// A terminal error or guardrail is already drawn inline; don't repeat it.
const hasFailureNode = (run: Run) =>
  [...run.preamble, ...run.steps.flatMap((s) => s.events)].some(
    (e) => (e.type === "error" || e.type === "guardrail_block") && isTerminal(e, true),
  );

// ── Step items ──────────────────────────────────────────────────────────────

type Item =
  | { kind: "stream" | "thought" | "error" | "guard"; event: TraceEvent }
  | { kind: "tool"; call: TraceEvent; result?: TraceEvent };

function groupItems(events: TraceEvent[]): Item[] {
  const items: Item[] = [];
  const openCalls = new Map<string, Extract<Item, { kind: "tool" }>>();

  for (const event of events) {
    switch (event.type) {
      case "streaming_thought":
        items.push({ kind: "stream", event });
        break;
      case "thought":
        items.push({ kind: "thought", event });
        break;
      case "tool_call": {
        const item = { kind: "tool" as const, call: event };
        openCalls.set(String(event.data.tool), item);
        items.push(item);
        break;
      }
      case "tool_result": {
        const open = openCalls.get(String(event.data.tool));
        if (open) {
          open.result = event;
          openCalls.delete(String(event.data.tool));
        }
        break;
      }
      case "error":
        items.push({ kind: "error", event });
        break;
      case "guardrail_block":
        items.push({ kind: "guard", event });
        break;
    }
  }
  return items;
}

function StreamItem({ text, live }: { text: string; live: boolean }) {
  if (live) {
    return (
      <pre
        aria-live="off"
        className="max-h-40 overflow-hidden font-mono text-[11.5px] leading-relaxed break-words whitespace-pre-wrap text-muted-foreground [mask-image:linear-gradient(to_bottom,transparent,black_45%)]"
        style={{ display: "flex", flexDirection: "column", justifyContent: "flex-end" }}
      >
        <span className="caret">{text.slice(-900)}</span>
      </pre>
    );
  }
  return (
    <Disclosure label="Model output" meta={`${text.length.toLocaleString("en-US")} chars`}>
      <CodeBlock>{text}</CodeBlock>
    </Disclosure>
  );
}

function ThoughtItem({ data }: { data: Record<string, unknown> }) {
  const action = String(data.action ?? "");
  return (
    <div>
      <p className="text-[13.5px] leading-relaxed text-pretty text-foreground/90">{String(data.thought ?? "")}</p>
      {action && (
        <p className="mt-1.5 flex items-center gap-2 font-mono text-[11px] text-faint">
          <span className="tracking-[0.14em] uppercase">Next</span>
          <span className="h-px w-3 bg-line-strong" />
          <span className="text-muted-foreground">{action === "finish" ? "compose answer" : toolLabel(action)}</span>
        </p>
      )}
    </div>
  );
}

function ToolItem({ call, result, live }: { call: TraceEvent; result?: TraceEvent; live: boolean }) {
  const tool = String(call.data.tool ?? "");
  const input = (call.data.input ?? {}) as Record<string, unknown>;
  const ok = result ? Boolean(result.data.success) : undefined;
  const elapsed = result?.data.elapsed_s;

  return (
    <Collapsible className="group/tool">
      <CollapsibleTrigger
        className={cn(
          "flex w-full items-center gap-2.5 rounded-lg border border-line bg-background/50 px-3 py-2 text-left transition-colors duration-200",
          "hover:border-line-strong data-[state=open]:border-line-strong",
          ok === false && "border-destructive/25",
        )}
      >
        <ToolIcon tool={tool} className="size-4 shrink-0 text-foreground/80" />
        <span className="shrink-0 text-[13px] font-medium">{toolLabel(tool)}</span>
        <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-faint">{previewArgs(input)}</span>
        <span className="flex shrink-0 items-center gap-1.5 font-mono text-[11px]">
          {ok === undefined ? (
            live ? (
              <span className="text-shimmer">running</span>
            ) : (
              <span className="text-faint">no result</span>
            )
          ) : ok ? (
            <>
              {elapsed !== undefined && <span className="tabular text-faint">{formatSeconds(Number(elapsed))}</span>}
              <Check weight="bold" className="size-3 text-foreground/80" />
            </>
          ) : (
            <>
              <span className="text-destructive">failed</span>
              <X weight="bold" className="size-3 text-destructive" />
            </>
          )}
        </span>
        <CaretRight
          weight="light"
          className="size-3 shrink-0 text-faint transition-transform duration-300 ease-expo group-data-[state=open]/tool:rotate-90"
        />
      </CollapsibleTrigger>

      {result && (
        <p className={cn("mt-1.5 pl-3 text-xs leading-relaxed", ok ? "text-muted-foreground" : "text-destructive/85")}>
          {summarizeResult(result.data)}
        </p>
      )}

      <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
        <div className="mt-2 flex flex-col gap-2">
          <CodeBlock label="input">{JSON.stringify(input, null, 2)}</CodeBlock>
          {result && <CodeBlock label="output">{JSON.stringify(result.data.result ?? {}, null, 2)}</CodeBlock>}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

function ErrorBody({ data, recoverable }: { data: Record<string, unknown>; recoverable: boolean }) {
  return (
    <div className="flex items-start gap-2 text-xs leading-relaxed">
      <WarningOctagon weight="light" className="mt-0.5 size-3.5 shrink-0 text-destructive" />
      <p className="text-destructive/90">
        {String(data.message ?? "Unknown error")}
        {recoverable && <span className="text-faint"> · agent is retrying</span>}
      </p>
    </div>
  );
}

function GuardrailBody({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="rounded-lg border border-destructive/25 bg-destructive/[0.04] px-3 py-2">
      <p className="flex items-center gap-2 font-mono text-[11px] tracking-[0.1em] text-destructive uppercase">
        <ShieldWarning weight="light" className="size-3.5" />
        Guardrail · {String(data.category ?? "policy")}
      </p>
      <p className="mt-1 text-xs leading-relaxed text-foreground/80">{String(data.message ?? "")}</p>
      {data.tool !== undefined && (
        <p className="mt-1 font-mono text-[11px] text-faint">blocked call to {toolLabel(data.tool)} · agent will re-plan</p>
      )}
    </div>
  );
}

// ── Primitives ──────────────────────────────────────────────────────────────

function Disclosure({ label, meta, children }: { label: string; meta?: string; children: React.ReactNode }) {
  return (
    <Collapsible className="group/disc">
      <CollapsibleTrigger className="flex items-center gap-1.5 font-mono text-[11px] text-faint transition-colors hover:text-muted-foreground">
        <CaretRight weight="light" className="size-3 transition-transform duration-300 ease-expo group-data-[state=open]/disc:rotate-90" />
        {label}
        {meta && <span className="text-faint/70">· {meta}</span>}
      </CollapsibleTrigger>
      <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
        <div className="mt-2">{children}</div>
      </CollapsibleContent>
    </Collapsible>
  );
}

function CodeBlock({ label, children }: { label?: string; children: string }) {
  return (
    <div className="overflow-hidden rounded-lg border border-line bg-background/70">
      {label && <p className="border-b border-line px-3 py-1.5 label-mono">{label}</p>}
      <pre className="max-h-64 overflow-auto px-3 py-2.5 font-mono text-[11.5px] leading-relaxed break-words whitespace-pre-wrap text-muted-foreground">
        {children}
      </pre>
    </div>
  );
}

function previewArgs(input: Record<string, unknown>) {
  return Object.entries(input)
    .map(([key, value]) => {
      let v = typeof value === "string" ? value : JSON.stringify(value);
      if (typeof value === "string" && value.includes("/")) v = value.split("/").pop() ?? value;
      return `${key}=${v.length > 40 ? v.slice(0, 40) + "…" : v}`;
    })
    .join("  ");
}
