"use client";

import { useRef, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Check, Copy, DownloadSimple, WarningOctagon } from "@phosphor-icons/react";
import { downloadUrl } from "@/lib/api";
import { fileKind, formatSeconds, pad, type Run } from "@/lib/events";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { AnimatedNumber } from "@/components/motion/animated-number";
import { SplitText, gsap, motionAllowed, useGSAP } from "@/components/motion/gsap";
import { useElapsed } from "@/components/workbench/run-status";

interface OutputPanelProps {
  run: Run;
  startedAt: number | null;
  className?: string;
}

export function OutputPanel({ run, startedAt, className }: OutputPanelProps) {
  const running = run.status === "running";

  return (
    <section data-panel className={cn("panel flex min-h-0 flex-col", className)} aria-label="Output">
      <header className="flex h-11 shrink-0 items-center gap-3 border-b border-line px-4">
        <h2 className="label-mono text-muted-foreground">Output</h2>
        {run.finish && <CopyButton text={run.finish.answer} />}
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto px-4 py-5">
        {running && !run.finish && <Composing />}
        {run.finish && <Answer key={run.finish.answer} markdown={run.finish.answer} />}
        {!run.finish && run.failure && run.status !== "running" && <Failure run={run} />}
        {run.artifacts.length > 0 && <Artifacts files={run.artifacts} />}
        {run.classification && <RunDetails run={run} startedAt={startedAt} />}
      </div>
    </section>
  );
}

function Composing() {
  return (
    <div aria-busy className="flex flex-col gap-3">
      <p className="text-shimmer text-[13px]">Working on the answer</p>
      <div className="flex flex-col gap-2">
        {[92, 78, 85, 40].map((w, i) => (
          <span
            key={i}
            className="h-2.5 rounded-sm bg-[linear-gradient(90deg,var(--muted)_0%,var(--accent)_50%,var(--muted)_100%)] bg-[length:200%_100%] animate-shimmer"
            style={{ width: `${w}%`, animationDelay: `${i * 120}ms` }}
          />
        ))}
      </div>
    </div>
  );
}

// Map markdown elements to styled tags; drops react-markdown's `node` prop.
function styled<T extends keyof React.JSX.IntrinsicElements>(Tag: T, base: string, as?: keyof React.JSX.IntrinsicElements) {
  const El = (as ?? Tag) as React.ElementType;
  function Styled({ node, className, ...props }: React.ComponentProps<T> & { node?: unknown; className?: string }) {
    void node;
    return <El className={cn(base, className)} {...props} />;
  }
  return Styled;
}

const markdown: Components = {
  h1: styled("h1", "mt-5 mb-2 text-base font-semibold tracking-tight first:mt-0", "h3"),
  h2: styled("h2", "mt-5 mb-2 text-[15px] font-semibold tracking-tight first:mt-0", "h3"),
  h3: styled("h3", "mt-4 mb-1.5 text-sm font-semibold first:mt-0", "h4"),
  h4: styled("h4", "mt-4 mb-1.5 text-sm font-medium first:mt-0"),
  p: styled("p", "my-2.5 text-pretty first:mt-0 last:mb-0"),
  ul: styled("ul", "my-2.5 flex list-none flex-col gap-1.5 pl-0"),
  ol: styled("ol", "my-2.5 flex list-decimal flex-col gap-1.5 pl-5 marker:font-mono marker:text-faint"),
  li: styled(
    "li",
    "relative pl-4 before:absolute before:top-[0.8em] before:left-0 before:h-px before:w-2 before:bg-faint in-[ol]:pl-1 in-[ol]:before:hidden",
  ),
  strong: styled("strong", "font-semibold text-foreground"),
  a: styled("a", "underline decoration-line-strong underline-offset-4 hover:decoration-foreground"),
  code: styled("code", "rounded bg-secondary px-1 py-0.5 font-mono text-[12px]"),
  pre: styled(
    "pre",
    "my-3 overflow-x-auto rounded-lg border border-line bg-background/70 p-3 font-mono text-[12px] [&_code]:bg-transparent [&_code]:p-0",
  ),
  table: styled("table", "my-3 block w-full overflow-x-auto rounded-lg border border-line text-left text-xs"),
  th: styled("th", "border-b border-line px-3 py-2 font-mono text-[10.5px] font-medium tracking-wider text-faint uppercase"),
  td: styled("td", "tabular border-b border-line px-3 py-2 align-top"),
  hr: styled("hr", "my-4 border-line"),
  blockquote: styled("blockquote", "my-3 border-l border-line-strong pl-3 text-muted-foreground"),
};

function Answer({ markdown: source }: { markdown: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      if (!ref.current || !motionAllowed()) return;
      const blocks = ref.current.querySelectorAll("p, li, h3, h4");
      if (blocks.length === 0) return;
      const split = SplitText.create(blocks, { type: "lines", mask: "lines" });
      gsap.from(split.lines, {
        yPercent: 105,
        autoAlpha: 0,
        duration: 0.9,
        stagger: 0.035,
        onComplete: () => split.revert(),
      });
    },
    { scope: ref },
  );

  return (
    <article>
      <p className="label-mono mb-3">Answer</p>
      <div ref={ref} className="text-[14px] leading-[1.7] text-foreground/90">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdown}>
          {source}
        </ReactMarkdown>
      </div>
    </article>
  );
}

function Failure({ run }: { run: Run }) {
  const title =
    run.status === "blocked" ? "Request blocked" : run.status === "timeout" ? "Stopped at the step limit" : "No answer produced";
  return (
    <div role="alert" className="rounded-lg border border-destructive/25 bg-destructive/[0.04] p-4">
      <p className="flex items-center gap-2 text-[13px] font-medium text-destructive">
        <WarningOctagon weight="light" className="size-4" />
        {title}
      </p>
      <p className="mt-1.5 text-xs leading-relaxed text-foreground/75">{run.failure}</p>
    </div>
  );
}

function Artifacts({ files }: { files: string[] }) {
  const ref = useRef<HTMLUListElement>(null);

  // Animate only rows that weren't there before.
  useGSAP(
    () => {
      if (!ref.current || !motionAllowed()) return;
      const fresh = ref.current.querySelectorAll("li:not([data-seen])");
      if (fresh.length === 0) return;
      fresh.forEach((el) => el.setAttribute("data-seen", ""));
      gsap.from(fresh, { autoAlpha: 0, x: -8, duration: 0.6, stagger: 0.07 });
    },
    { scope: ref, dependencies: [files.length] },
  );

  return (
    <div>
      <p className="label-mono mb-2">Artifacts</p>
      <ul ref={ref} className="flex flex-col gap-1.5">
        {files.map((file) => (
          <li key={file}>
            <a
              href={downloadUrl(file)}
              download={file}
              className="group/artifact flex items-center gap-3 rounded-lg border border-line bg-background/50 px-3 py-2.5 transition-[border-color,background-color,transform] duration-300 ease-expo hover:border-line-strong hover:bg-foreground/[0.03] active:scale-[0.99]"
            >
              <span className="grid h-7 w-10 shrink-0 place-items-center rounded-[5px] border border-line-strong font-mono text-[9.5px] tracking-wider text-foreground/85">
                {fileKind(file)}
              </span>
              <span className="min-w-0 flex-1 truncate text-[13px]" title={file}>
                {file}
              </span>
              <DownloadSimple
                weight="light"
                className="size-4 shrink-0 text-faint transition-all duration-300 ease-expo group-hover/artifact:translate-y-0.5 group-hover/artifact:text-foreground"
              />
              <span className="sr-only">Download</span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RunDetails({ run, startedAt }: { run: Run; startedAt: number | null }) {
  const c = run.classification!;
  const live = useElapsed(startedAt, run.status === "running");
  const duration = run.finish?.total_elapsed_s ?? (run.status === "running" ? live : undefined);

  const rows: [string, React.ReactNode][] = [
    ["Task", c.task_type],
    ["Model", c.model_key],
    ["Route confidence", <AnimatedNumber key="c" value={c.confidence * 100} format={(n) => `${Math.round(n)}%`} />],
    ["Steps", pad(run.steps.length)],
    ["Tool calls", pad(run.toolCalls)],
    ["Duration", duration !== undefined ? formatSeconds(duration) : "—"],
  ];

  return (
    <div className="mt-auto">
      <p className="label-mono mb-2">Run</p>
      <dl className="grid grid-cols-2 border-t border-line">
        {rows.map(([k, v]) => (
          <div key={k} className="flex flex-col gap-0.5 border-b border-line py-2 odd:pr-3 even:border-l even:pl-3">
            <dt className="text-[11px] text-faint">{k}</dt>
            <dd className="tabular font-mono text-[12.5px] text-foreground/90">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      variant="ghost"
      size="xs"
      className="ml-auto text-faint hover:text-foreground"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1600);
      }}
    >
      {copied ? <Check data-icon="inline-start" /> : <Copy weight="light" data-icon="inline-start" />}
      {copied ? "Copied" : "Copy"}
    </Button>
  );
}
