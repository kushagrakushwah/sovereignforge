"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { clearKb, getKbStats, ingestKbFile, type KbStats } from "@/lib/api";

const POLL_MS = 5000;

export const KB_ACCEPT = ".txt,.pdf,.docx,.md";

export function useKnowledgeBase() {
  const [stats, setStats] = useState<KbStats | null>(null);
  const [reachable, setReachable] = useState(true);
  const [busy, setBusy] = useState<"ingest" | "clear" | null>(null);

  const refresh = useCallback(async () => {
    try {
      setStats(await getKbStats());
      setReachable(true);
    } catch {
      setReachable(false);
    }
  }, []);

  useEffect(() => {
    // Initial fetch and polling both update state from an async callback.
    const first = setTimeout(refresh, 0);
    const interval = setInterval(refresh, POLL_MS);
    return () => {
      clearTimeout(first);
      clearInterval(interval);
    };
  }, [refresh]);

  const ingest = useCallback(
    async (file: File) => {
      setBusy("ingest");
      try {
        const result = await ingestKbFile(file);
        if (!result.success) throw new Error(result.error ?? "Ingestion failed");
        toast.success(`Indexed ${file.name}`, {
          description: `${result.chunks_added ?? 0} chunks added to the knowledge base.`,
        });
        await refresh();
      } catch (err) {
        toast.error(`Could not index ${file.name}`, {
          description: err instanceof Error ? err.message : undefined,
        });
      } finally {
        setBusy(null);
      }
    },
    [refresh],
  );

  const clear = useCallback(async () => {
    setBusy("clear");
    try {
      const result = await clearKb();
      if (!result.success) throw new Error(result.message);
      toast("Knowledge base cleared");
      await refresh();
    } catch (err) {
      toast.error("Could not clear the knowledge base", {
        description: err instanceof Error ? err.message : undefined,
      });
    } finally {
      setBusy(null);
    }
  }, [refresh]);

  return { stats, reachable, busy, ingest, clear };
}

export type KnowledgeBaseState = ReturnType<typeof useKnowledgeBase>;
