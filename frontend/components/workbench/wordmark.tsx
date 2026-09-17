"use client";

import { useRef } from "react";
import { cn } from "@/lib/utils";
import { SplitText, gsap, motionAllowed, useGSAP } from "@/components/motion/gsap";

export function Mark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden className={cn("size-5", className)}>
      <rect x="1.5" y="1.5" width="17" height="17" rx="4.5" stroke="currentColor" strokeOpacity=".28" />
      <path d="M6 13.5h8M6 10h5.5M6 6.5h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function Wordmark() {
  const ref = useRef<HTMLSpanElement>(null);

  useGSAP(
    () => {
      if (!ref.current || !motionAllowed()) return;
      const split = SplitText.create(ref.current, { type: "chars", mask: "chars" });
      gsap.from(split.chars, {
        yPercent: 110,
        duration: 0.8,
        stagger: 0.022,
        delay: 0.1,
        onComplete: () => split.revert(),
      });
    },
    { scope: ref },
  );

  return (
    <div className="flex items-center gap-2.5">
      <Mark className="text-foreground" />
      <span ref={ref} className="text-[14px] font-semibold tracking-[-0.01em]">
        SovereignForge
      </span>
    </div>
  );
}
