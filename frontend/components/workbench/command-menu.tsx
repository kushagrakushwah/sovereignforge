"use client";

import { useEffect } from "react";
import { ArrowCounterClockwise, Database, Paperclip, PencilSimpleLine } from "@phosphor-icons/react";
import { PRESETS, type Preset } from "@/lib/presets";
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command";

interface CommandMenuProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  running: boolean;
  canReset: boolean;
  onPreset: (preset: Preset) => void;
  onFocusComposer: () => void;
  onAttach: () => void;
  onIngest: () => void;
  onReset: () => void;
}

export function CommandMenu({
  open,
  onOpenChange,
  running,
  canReset,
  onPreset,
  onFocusComposer,
  onAttach,
  onIngest,
  onReset,
}: CommandMenuProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  const run = (fn: () => void) => () => {
    onOpenChange(false);
    // Let the dialog release focus before the action moves it.
    requestAnimationFrame(fn);
  };

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Commands"
      description="Run an action or load a preset task"
      className="border-line-strong bg-popover sm:max-w-lg"
    >
        <Command>
        <CommandInput placeholder="Search commands and presets" />
        <CommandList className="max-h-[min(420px,60vh)]">
          <CommandEmpty>No matches.</CommandEmpty>
          <CommandGroup heading="Actions">
            <CommandItem onSelect={run(onFocusComposer)} disabled={running}>
              <PencilSimpleLine weight="light" />
              Write a task
            </CommandItem>
            <CommandItem onSelect={run(onAttach)} disabled={running}>
              <Paperclip weight="light" />
              Attach a file
            </CommandItem>
            <CommandItem onSelect={run(onIngest)}>
              <Database weight="light" />
              Add a document to the knowledge base
            </CommandItem>
            {canReset && (
              <CommandItem onSelect={run(onReset)}>
                <ArrowCounterClockwise weight="light" />
                New task
              </CommandItem>
            )}
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading="Presets">
            {PRESETS.map((preset) => (
              <CommandItem
                key={preset.title}
                value={`${preset.title} ${preset.pipeline}`}
                onSelect={run(() => onPreset(preset))}
                disabled={running}
              >
                {preset.title}
                <CommandShortcut className="font-mono tracking-normal">{preset.pipeline}</CommandShortcut>
              </CommandItem>
            ))}
        </CommandGroup>
      </CommandList>
      </Command>
    </CommandDialog>
  );
}
