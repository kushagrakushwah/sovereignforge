"use client";

import { useRef } from "react";
import { SplitText, gsap, motionAllowed, useGSAP } from "@/components/motion/gsap";

interface IdleHeroProps {
  /** Play the entrance sequence. Off when returning from the workbench. */
  intro: boolean;
  connected: boolean;
  composer: React.ReactNode;
  presets: React.ReactNode;
  knowledgeBase: React.ReactNode;
}

export function IdleHero({ intro, connected, composer, presets, knowledgeBase }: IdleHeroProps) {
  const ref = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      if (!intro || !motionAllowed()) return;
      const split = SplitText.create("[data-headline]", { type: "words", mask: "words" });
      const tl = gsap.timeline({ delay: 0.15 });
      tl.from(split.words, { yPercent: 110, duration: 1.1, stagger: 0.06, onComplete: () => split.revert() })
        .from("[data-hero-sub]", { autoAlpha: 0, y: 8, duration: 0.8 }, 0.35)
        .from("[data-flip-id=composer]", { autoAlpha: 0, y: 16, duration: 1 }, 0.45)
        .from("[data-reveal]", { autoAlpha: 0, y: 8, duration: 0.7, stagger: 0.045 }, 0.65);
    },
    { scope: ref },
  );

  return (
    <section ref={ref} className="h-full overflow-y-auto">
      <div className="mx-auto flex min-h-full w-full max-w-[720px] flex-col justify-center gap-8 py-10">
        <div className="flex flex-col gap-4">
          <p data-hero-sub className="label-mono flex items-center gap-2">
            <span className={connected ? "text-foreground/70" : "text-destructive"}>
              {connected ? "Local agent ready" : "Waiting for the local agent"}
            </span>
            <span className="h-px w-8 bg-line-strong" />
            <span>No external calls</span>
          </p>
          <h1
            data-headline
            className="text-[clamp(2rem,4.6vw,3.25rem)] leading-[1.05] font-medium tracking-[-0.035em] text-balance"
          >
            What should the agent work on?
          </h1>
          <p data-hero-sub className="max-w-[54ch] text-[15px] leading-relaxed text-pretty text-muted-foreground">
            Reports, drawings and code are read, reasoned over and drafted by models running on this machine. Every
            step is traced as it happens.
          </p>
        </div>

        {composer}

        <div className="grid gap-8 md:grid-cols-[minmax(0,1fr)_260px]">
          <div>
            <p data-reveal className="label-mono mb-2">
              Presets
            </p>
            {presets}
          </div>
          <div data-reveal className="md:pt-6">
            {knowledgeBase}
          </div>
        </div>
      </div>
    </section>
  );
}
