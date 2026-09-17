"use client";

import { useRef } from "react";
import { Prohibit } from "@phosphor-icons/react";
import { useNetworkMonitor, type NetworkEntry } from "@/lib/websocket";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { AnimatedNumber } from "@/components/motion/animated-number";
import { gsap, motionAllowed, useGSAP } from "@/components/motion/gsap";
import { StatusDot } from "@/components/workbench/status-dot";

const entryKey = (e: NetworkEntry) => `${e.timestamp}|${e.method}|${e.url}`;

export function NetworkRail() {
  const status = useNetworkMonitor();
  const breach = status.external_blocked > 0;
  const recent = status.entries.slice(-10).reverse();
  const tickerRef = useRef<HTMLOListElement>(null);
  const newest = recent[0] ? entryKey(recent[0]) : "";

  // Slide the newest request in from the left.
  useGSAP(
    () => {
      const first = tickerRef.current?.firstElementChild;
      if (!first || !motionAllowed()) return;
      gsap.from(first, { autoAlpha: 0, x: -12, duration: 0.5 });
    },
    { dependencies: [newest] },
  );

  return (
    <footer
      className={cn(
        "flex h-11 shrink-0 items-center gap-4 border-t px-4 font-mono text-[11px] md:px-5",
        breach ? "border-destructive/30 bg-destructive/[0.03]" : "border-line",
      )}
      aria-label="Network sovereignty monitor"
    >
      <Tooltip>
        <TooltipTrigger asChild>
          <span role="status" className="flex shrink-0 items-center gap-2 tracking-[0.12em] uppercase">
            <StatusDot tone={!status.connected ? "off" : breach ? "alert" : "live"} />
            <span className={breach ? "text-destructive" : "text-foreground/85"}>
              {!status.connected ? "Monitor offline" : breach ? "External call detected" : "Sovereign"}
            </span>
          </span>
        </TooltipTrigger>
        <TooltipContent side="top">
          {breach
            ? "mitmproxy blocked outbound traffic to a non-local host."
            : "Every request observed by mitmproxy stayed on this machine."}
        </TooltipContent>
      </Tooltip>

      <span className="h-3.5 w-px shrink-0 bg-line-strong" />

      <span className="flex shrink-0 items-center gap-4 text-faint">
        <span>
          <AnimatedNumber value={status.total} className="text-foreground/85" /> requests
        </span>
        <span className={cn(breach && "text-destructive")}>
          <AnimatedNumber value={status.external_blocked} className={breach ? "" : "text-foreground/85"} /> external
        </span>
      </span>

      <span className="hidden h-3.5 w-px shrink-0 bg-line-strong md:block" />

      <div className="relative hidden min-w-0 flex-1 overflow-hidden md:block [mask-image:linear-gradient(to_right,black_85%,transparent)]">
        {recent.length === 0 ? (
          <span className="text-faint">Awaiting traffic. Start mitmproxy to capture requests.</span>
        ) : (
          <ol ref={tickerRef} className="flex items-center gap-5 whitespace-nowrap">
            {recent.map((entry) => (
              <li
                key={entryKey(entry)}
                title={entry.url}
                className={cn("flex items-center gap-1.5", entry.blocked ? "text-destructive" : "text-faint")}
              >
                {entry.blocked && <Prohibit weight="bold" className="size-3" />}
                <span className={entry.blocked ? "" : "text-muted-foreground"}>{entry.method}</span>
                {entry.host}:{entry.port}
              </li>
            ))}
          </ol>
        )}
      </div>

      <span className="ml-auto hidden shrink-0 tracking-[0.12em] text-faint uppercase lg:inline">mitmproxy</span>
    </footer>
  );
}
