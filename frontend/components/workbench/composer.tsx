"use client";

import { useState } from "react";
import { ArrowUp, CircleNotch, Paperclip, X } from "@phosphor-icons/react";
import type { UploadResult } from "@/lib/api";
import { fileKind } from "@/lib/events";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Kbd, KbdGroup } from "@/components/ui/kbd";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useModKey } from "@/hooks/use-mod-key";

interface ComposerProps {
  variant: "hero" | "panel";
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onAttach: () => void;
  onDropFile: (file: File) => void;
  onClearAttachment: () => void;
  attachment: UploadResult | null;
  uploading: boolean;
  running: boolean;
  className?: string;
  ref?: React.Ref<HTMLTextAreaElement>;
}

export function Composer({
  variant,
  value,
  onChange,
  onSubmit,
  onAttach,
  onDropFile,
  onClearAttachment,
  attachment,
  uploading,
  running,
  className,
  ref,
}: ComposerProps) {
  const [dragging, setDragging] = useState(false);
  const mod = useModKey();
  const hero = variant === "hero";
  const canSubmit = value.trim().length > 0 && !running && !uploading;

  return (
    <form
      id="composer"
      data-flip-id="composer"
      onSubmit={(e) => {
        e.preventDefault();
        if (canSubmit) onSubmit();
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const file = e.dataTransfer.files[0];
        if (file && !running) onDropFile(file);
      }}
      className={cn(
        "panel group/composer flex flex-col transition-[border-color,box-shadow] duration-300 ease-expo",
        "focus-within:border-line-strong focus-within:shadow-[inset_0_1px_0_0_oklch(1_0_0/6%),0_0_0_4px_oklch(1_0_0/3%)]",
        dragging && "border-foreground/30",
        className,
      )}
    >
      <label htmlFor="task-input" className="sr-only">
        Task for the agent
      </label>
      <textarea
        id="task-input"
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            if (canSubmit) onSubmit();
          }
        }}
        disabled={running}
        rows={hero ? 4 : 6}
        placeholder={
          hero
            ? "Describe the task. Attach a report, drawing or source file if the agent needs one."
            : "Describe the next task…"
        }
        className={cn(
          "w-full resize-none bg-transparent px-4 pt-4 text-foreground outline-none placeholder:text-faint disabled:opacity-50",
          "focus-visible:outline-none",
          hero ? "min-h-28 text-[15px] leading-relaxed" : "min-h-32 text-sm leading-relaxed",
        )}
      />

      <div className="flex items-center gap-2 px-2.5 pt-2 pb-2.5">
        {attachment ? (
          <span className="flex min-w-0 items-center gap-2 rounded-md border border-line bg-secondary/60 py-1 pr-1 pl-1.5 animate-in fade-in-0 slide-in-from-bottom-1 duration-300">
            <span className="rounded-[4px] border border-line-strong px-1 font-mono text-[9.5px] leading-4 text-muted-foreground">
              {fileKind(attachment.filename)}
            </span>
            <span className="truncate text-xs text-foreground/90" title={attachment.filename}>
              {attachment.filename}
            </span>
            <Button
              type="button"
              variant="ghost"
              size="icon-xs"
              onClick={onClearAttachment}
              disabled={running}
              aria-label={`Remove ${attachment.filename}`}
              className="text-faint hover:text-foreground"
            >
              <X />
            </Button>
          </span>
        ) : (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onAttach}
                disabled={uploading || running}
                className="text-muted-foreground"
              >
                {uploading ? (
                  <CircleNotch className="animate-spin" data-icon="inline-start" />
                ) : (
                  <Paperclip weight="light" data-icon="inline-start" />
                )}
                {uploading ? "Uploading" : "Attach"}
              </Button>
            </TooltipTrigger>
            <TooltipContent>PDF, image, Word or source file. You can also drop it here.</TooltipContent>
          </Tooltip>
        )}

        <div className="ml-auto flex items-center gap-2.5">
          <KbdGroup className="hidden text-faint sm:inline-flex">
            <Kbd className="bg-transparent font-mono text-faint">{mod}</Kbd>
            <Kbd className="bg-transparent font-mono text-faint">↵</Kbd>
          </KbdGroup>
          <Button
            type="submit"
            size={hero ? "default" : "sm"}
            disabled={!canSubmit}
            className="gap-1.5 transition-transform duration-200 ease-expo active:scale-[0.97]"
          >
            {running ? (
              <>
                <CircleNotch className="animate-spin" data-icon="inline-start" />
                Running
              </>
            ) : (
              <>
                Run
                <ArrowUp weight="bold" data-icon="inline-end" />
              </>
            )}
          </Button>
        </div>
      </div>
    </form>
  );
}
