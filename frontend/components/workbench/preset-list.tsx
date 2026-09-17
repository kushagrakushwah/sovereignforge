"use client";

import { ArrowRight } from "@phosphor-icons/react";
import { PRESETS, type Preset } from "@/lib/presets";
import { pad } from "@/lib/events";
import { cn } from "@/lib/utils";

interface PresetListProps {
  onPick: (preset: Preset) => void;
  disabled?: boolean;
  limit?: number;
  className?: string;
}

export function PresetList({ onPick, disabled, limit, className }: PresetListProps) {
  const presets = limit ? PRESETS.slice(0, limit) : PRESETS;

  return (
    <ul className={cn("flex flex-col", className)}>
      {presets.map((preset, i) => (
        <li key={preset.title} data-reveal>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onPick(preset)}
            title={preset.prompt}
            className={cn(
              "group/preset flex w-full items-baseline gap-3 border-t border-line py-2.5 text-left transition-colors duration-200",
              "hover:border-line-strong disabled:pointer-events-none disabled:opacity-40",
            )}
          >
            <span className="tabular font-mono text-[10.5px] text-faint">{pad(i + 1)}</span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[13px] text-foreground/85 transition-colors group-hover/preset:text-foreground">
                {preset.title}
              </span>
              <span className="block truncate font-mono text-[10.5px] text-faint">{preset.pipeline}</span>
            </span>
            <ArrowRight
              weight="light"
              className="size-3.5 shrink-0 -translate-x-1 self-center text-faint opacity-0 transition-all duration-300 ease-expo group-hover/preset:translate-x-0 group-hover/preset:opacity-100"
            />
          </button>
        </li>
      ))}
    </ul>
  );
}
