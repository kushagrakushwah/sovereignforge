// Typed view over the agent event stream emitted by backend/agent/loop.py
// and backend/main.py, plus helpers that fold the flat stream into a run.

export type AgentEventType =
  | "classified"
  | "agent_start"
  | "thinking"
  | "streaming_thought"
  | "thought"
  | "tool_call"
  | "tool_result"
  | "guardrail_block"
  | "finish"
  | "error"
  | "max_iterations";

export interface AgentEvent {
  type: AgentEventType | (string & {});
  data: Record<string, unknown>;
}

/** An event as stored on the client: stable id and receive time. */
export interface TraceEvent extends AgentEvent {
  id: number;
  at: number;
}

export interface Classification {
  task_type: string;
  model_key: string;
  confidence: number;
  reasoning: string;
}

export interface FinishData {
  answer: string;
  artifacts: string[];
  total_elapsed_s?: number;
}

export type RunStatus = "idle" | "running" | "done" | "failed" | "blocked" | "timeout";

export interface Step {
  iteration: number;
  /** Client receive time of the step's `thinking` event. */
  at: number;
  events: TraceEvent[];
}

export interface Run {
  status: RunStatus;
  classification?: Classification;
  /** Events that arrive before the first reasoning step. */
  preamble: TraceEvent[];
  steps: Step[];
  finish?: FinishData;
  /** Terminal failure message, if the run ended without an answer. */
  failure?: string;
  artifacts: string[];
  toolCalls: number;
}

const str = (v: unknown, fallback = "") => (v === undefined || v === null ? fallback : String(v));

/**
 * Whether an event ends the run. The backend keeps looping after a JSON parse
 * failure or an unknown tool (it asks the model to retry), and after a tool
 * argument guardrail; everything else of these kinds is final.
 */
export function isTerminal(event: AgentEvent, started: boolean): boolean {
  switch (event.type) {
    case "finish":
    case "max_iterations":
      return true;
    case "guardrail_block":
      return event.data.tool === undefined;
    case "error": {
      if (!started) return true;
      const recoverable = "raw" in event.data || str(event.data.message).startsWith("Unknown tool");
      return !recoverable;
    }
    default:
      return false;
  }
}

export function buildRun(events: TraceEvent[], running: boolean): Run {
  const run: Run = { status: "idle", preamble: [], steps: [], artifacts: [], toolCalls: 0 };
  const artifacts = new Set<string>();
  let started = false;
  let current: Step | undefined;

  for (const event of events) {
    const d = event.data;
    switch (event.type) {
      case "classified":
        run.classification = {
          task_type: str(d.task_type),
          model_key: str(d.model_key),
          confidence: Number(d.confidence ?? 0),
          reasoning: str(d.reasoning),
        };
        break;
      case "agent_start":
        started = true;
        break;
      case "thinking":
        current = { iteration: Number(d.iteration ?? run.steps.length + 1), at: event.at, events: [] };
        run.steps.push(current);
        continue;
      case "tool_call":
        run.toolCalls += 1;
        break;
      case "tool_result": {
        const filename = (d.result as Record<string, unknown> | undefined)?.filename;
        if (typeof filename === "string") artifacts.add(filename);
        break;
      }
      case "finish":
        run.finish = {
          answer: str(d.answer, "Task complete."),
          artifacts: Array.isArray(d.artifacts) ? d.artifacts.map(String) : [],
          total_elapsed_s: d.total_elapsed_s === undefined ? undefined : Number(d.total_elapsed_s),
        };
        run.finish.artifacts.forEach((a) => artifacts.add(a));
        run.status = "done";
        continue;
    }

    if (isTerminal(event, started)) {
      run.status =
        event.type === "max_iterations" ? "timeout" : event.type === "guardrail_block" ? "blocked" : "failed";
      run.failure = str(d.message, "The run ended unexpectedly.");
    }

    if (event.type === "classified" || event.type === "agent_start") {
      run.preamble.push(event);
    } else if (current) {
      current.events.push(event);
    } else {
      run.preamble.push(event);
    }
  }

  if (run.status === "idle" && running) run.status = "running";
  else if (run.status === "idle" && events.length > 0) run.status = "failed";
  if (run.status === "failed" && !run.failure) run.failure = "Connection to the agent was lost.";
  run.artifacts = [...artifacts];
  return run;
}

// ── Presentation helpers ────────────────────────────────────────────────────

export const TOOL_LABELS: Record<string, string> = {
  ocr: "OCR",
  extract: "Extract",
  draft_word: "Draft Word",
  draft_ppt: "Draft slides",
  draft_excel: "Draft workbook",
  code_sandbox: "Code sandbox",
  image_understand: "Vision",
  search_kb: "Knowledge search",
  ingest_file: "Ingest file",
};

export const toolLabel = (tool: unknown) => TOOL_LABELS[str(tool)] ?? str(tool, "tool");

export function summarizeResult(data: Record<string, unknown>): string {
  const result = (data.result ?? {}) as Record<string, unknown>;
  if (!data.success) return str(result.error, "Tool failed");
  if (result.cache_hit) return "Served from cache";
  if (result.filename) return `Wrote ${result.filename}`;
  if (result.stdout !== undefined) return firstLine(str(result.stdout)) || "Exited cleanly";
  if (result.text !== undefined) return `${str(result.text).length.toLocaleString()} characters extracted`;
  if (result.analysis !== undefined) return firstLine(str(result.analysis));
  if (Array.isArray(result.results)) return `${result.results.length} passages matched`;
  if (result.chunks_added !== undefined) return `${result.chunks_added} chunks indexed`;
  return "Completed";
}

function firstLine(text: string, max = 140) {
  const line = text.trim().split("\n")[0] ?? "";
  return line.length > max ? `${line.slice(0, max)}…` : line;
}

export function fileKind(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  return ext ? ext.toUpperCase().slice(0, 4) : "FILE";
}

export const pad = (n: number, width = 2) => String(n).padStart(width, "0");

export function formatSeconds(seconds: number) {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  return `${m}m ${pad(Math.round(seconds - m * 60))}s`;
}
