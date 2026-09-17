"use client";

import gsap from "gsap";
import { Flip } from "gsap/Flip";
import { SplitText } from "gsap/SplitText";
import { useGSAP } from "@gsap/react";

if (typeof window !== "undefined") {
  gsap.registerPlugin(useGSAP, Flip, SplitText);
  gsap.defaults({ ease: "expo.out", duration: 0.6 });
}

/** False when the user asked the OS for reduced motion. */
export function motionAllowed() {
  return typeof window !== "undefined" && !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export { gsap, Flip, SplitText, useGSAP };
