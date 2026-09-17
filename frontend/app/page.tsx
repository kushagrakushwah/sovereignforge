"use client";

import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { buildRun } from "@/lib/events";
import type { Preset } from "@/lib/presets";
import { cn } from "@/lib/utils";
import { useAgentWebSocket } from "@/lib/websocket";
import { ATTACHMENT_ACCEPT, useAttachment } from "@/hooks/use-attachment";
import { useFilePicker } from "@/hooks/use-file-picker";
import { KB_ACCEPT, useKnowledgeBase } from "@/hooks/use-knowledge-base";
import { Flip, gsap, motionAllowed, useGSAP } from "@/components/motion/gsap";
import { CommandMenu } from "@/components/workbench/command-menu";
import { Composer } from "@/components/workbench/composer";
import { ExecutionTrace } from "@/components/workbench/execution-trace";
import { IdleHero } from "@/components/workbench/idle-hero";
import { KnowledgeBase } from "@/components/workbench/knowledge-base";
import { NetworkRail } from "@/components/workbench/network-rail";
import { OutputPanel } from "@/components/workbench/output-panel";
import { PresetList } from "@/components/workbench/preset-list";
import { TopBar } from "@/components/workbench/top-bar";

type Tab = "compose" | "trace" | "output";

const TABS: { id: Tab; label: string }[] = [
  { id: "compose", label: "Task" },
  { id: "trace", label: "Trace" },
  { id: "output", label: "Output" },
];

export default function Workbench() {
  const agent = useAgentWebSocket();
  const run = useMemo(() => buildRun(agent.events, agent.isRunning), [agent.events, agent.isRunning]);
  const kb = useKnowledgeBase();
  const attachment = useAttachment();

  const [prompt, setPrompt] = useState("");
  const [commandsOpen, setCommandsOpen] = useState(false);
  const [intro, setIntro] = useState(true);
  const [tab, setTab] = useState<Tab>("trace");
  const [seenStatus, setSeenStatus] = useState(run.status);

  const rootRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const flipState = useRef<Flip.FlipState | null>(null);

  const active = run.status !== "idle";
  const running = run.status === "running";
  const canReset = active && !running;

  // On small screens, surface the answer as soon as it lands.
  if (run.status !== seenStatus) {
    setSeenStatus(run.status);
    if (run.status === "done") setTab("output");
  }

  const attachPicker = useFilePicker(ATTACHMENT_ACCEPT, attachment.upload);
  const kbPicker = useFilePicker(KB_ACCEPT, kb.ingest);

  const captureLayout = () => {
    if (motionAllowed()) flipState.current = Flip.getState("[data-flip-id]");
  };

  const submit = () => {
    const text = prompt.trim();
    if (!text || running) return;
    if (!active) captureLayout();
    if (!agent.sendTask(text, attachment.attachment?.file_path)) {
      flipState.current = null;
      toast.error("Agent is offline", {
        description: "Start the backend on port 8000. The workbench reconnects on its own.",
      });
      return;
    }
    setTab("trace");
  };

  const reset = () => {
    if (!canReset) return;
    captureLayout();
    setIntro(false);
    agent.reset();
  };

  const focusComposer = () => {
    setTab("compose");
    requestAnimationFrame(() => composerRef.current?.focus());
  };

  const pickPreset = (preset: Preset) => {
    setPrompt(preset.prompt);
    focusComposer();
  };

  // Morph the composer between the hero and the workbench column.
  useGSAP(
    () => {
      const state = flipState.current;
      flipState.current = null;
      if (!state) return;
      Flip.from(state, { targets: "[data-flip-id]", duration: 0.95, ease: "expo.inOut", absolute: true });
      if (active) {
        gsap.from("[data-panel]", { autoAlpha: 0, y: 28, duration: 1, stagger: 0.08, delay: 0.25 });
      } else {
        gsap.from("[data-headline], [data-hero-sub], [data-reveal]", {
          autoAlpha: 0,
          y: 10,
          duration: 0.8,
          stagger: 0.03,
          delay: 0.3,
        });
      }
    },
    { scope: rootRef, dependencies: [active] },
  );

  const composer = (
    <Composer
      ref={composerRef}
      variant={active ? "panel" : "hero"}
      value={prompt}
      onChange={setPrompt}
      onSubmit={submit}
      onAttach={attachPicker.open}
      onDropFile={attachment.upload}
      onClearAttachment={attachment.clear}
      attachment={attachment.attachment}
      uploading={attachment.uploading}
      running={running}
    />
  );

  return (
    <div ref={rootRef} className="flex h-dvh flex-col">
      <TopBar
        run={run}
        startedAt={agent.startedAt}
        connected={agent.connected}
        onReset={reset}
        onOpenCommands={() => setCommandsOpen(true)}
      />

      <main className="relative min-h-0 flex-1 px-3 md:px-4">
        {!active ? (
          <IdleHero
            intro={intro}
            connected={agent.connected}
            composer={composer}
            presets={<PresetList onPick={pickPreset} limit={5} />}
            knowledgeBase={<KnowledgeBase kb={kb} onIngest={kbPicker.open} />}
          />
        ) : (
          <div className="flex h-full flex-col gap-3 pb-3">
            <div role="tablist" aria-label="Workbench panels" className="panel flex shrink-0 p-1 lg:hidden">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  role="tab"
                  aria-selected={tab === t.id}
                  onClick={() => setTab(t.id)}
                  className={cn(
                    "flex-1 rounded-lg py-1.5 font-mono text-[11px] tracking-[0.12em] text-faint uppercase transition-colors duration-200",
                    tab === t.id && "bg-secondary text-foreground",
                  )}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)] gap-3 lg:grid-cols-[minmax(300px,340px)_minmax(0,1fr)_minmax(320px,420px)]">
              <aside
                className={cn("flex min-h-0 flex-col gap-3 overflow-y-auto", tab !== "compose" && "max-lg:hidden")}
                aria-label="Task"
              >
                {composer}
                <div data-panel className="panel px-4 pt-3 pb-1">
                  <p className="label-mono mb-2">Presets</p>
                  <PresetList onPick={pickPreset} disabled={running} />
                </div>
                <div data-panel>
                  <KnowledgeBase kb={kb} onIngest={kbPicker.open} />
                </div>
              </aside>

              <ExecutionTrace
                run={run}
                startedAt={agent.startedAt}
                className={cn(tab !== "trace" && "max-lg:hidden")}
              />
              <OutputPanel
                run={run}
                startedAt={agent.startedAt}
                className={cn(tab !== "output" && "max-lg:hidden")}
              />
            </div>
          </div>
        )}
      </main>

      <NetworkRail />

      <CommandMenu
        open={commandsOpen}
        onOpenChange={setCommandsOpen}
        running={running}
        canReset={canReset}
        onPreset={pickPreset}
        onFocusComposer={focusComposer}
        onAttach={attachPicker.open}
        onIngest={kbPicker.open}
        onReset={reset}
      />
      {attachPicker.input}
      {kbPicker.input}
    </div>
  );
}
