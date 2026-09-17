"use client";

import { useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { gsap, motionAllowed, useGSAP } from "@/components/motion/gsap";

interface AnimatedNumberProps {
  value: number;
  format?: (n: number) => string;
  className?: string;
}

const defaultFormat = (n: number) => Math.round(n).toLocaleString("en-US");

/** A number that counts toward its new value instead of jumping. */
export function AnimatedNumber({ value, format = defaultFormat, className }: AnimatedNumberProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const shown = useRef({ n: value });
  // React renders the first value once; GSAP owns the text node afterwards.
  const [initial] = useState(value);

  useGSAP(
    () => {
      const el = ref.current;
      if (!el) return;
      if (!motionAllowed()) {
        shown.current.n = value;
        el.textContent = format(value);
        return;
      }
      gsap.to(shown.current, {
        n: value,
        duration: 0.9,
        ease: "power3.out",
        overwrite: true,
        onUpdate: () => {
          el.textContent = format(shown.current.n);
        },
      });
    },
    { dependencies: [value] },
  );

  return (
    <span ref={ref} className={cn("tabular", className)}>
      {format(initial)}
    </span>
  );
}
