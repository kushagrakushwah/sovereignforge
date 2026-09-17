"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";
import { uploadFile, type UploadResult } from "@/lib/api";

export const ATTACHMENT_ACCEPT =
  ".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.webp,.bmp,.tiff,.py,.js,.ts,.cpp,.java,.c,.go";

/** The single file attached to the next task, uploaded eagerly to the backend. */
export function useAttachment() {
  const [attachment, setAttachment] = useState<UploadResult | null>(null);
  const [uploading, setUploading] = useState(false);

  const upload = useCallback(async (file: File) => {
    setUploading(true);
    try {
      setAttachment(await uploadFile(file));
    } catch (err) {
      toast.error("Upload failed", {
        description: err instanceof Error ? err.message : "The backend did not accept the file.",
      });
    } finally {
      setUploading(false);
    }
  }, []);

  const clear = useCallback(() => setAttachment(null), []);

  return { attachment, uploading, upload, clear };
}
