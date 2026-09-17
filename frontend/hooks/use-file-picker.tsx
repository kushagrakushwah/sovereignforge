"use client";

import { useRef } from "react";

/** A hidden file input plus a function that opens it. Render `input` once. */
export function useFilePicker(accept: string, onFile: (file: File) => void) {
  const ref = useRef<HTMLInputElement>(null);

  const input = (
    <input
      ref={ref}
      type="file"
      accept={accept}
      hidden
      tabIndex={-1}
      onChange={(e) => {
        const file = e.target.files?.[0];
        e.target.value = "";
        if (file) onFile(file);
      }}
    />
  );

  return { open: () => ref.current?.click(), input };
}
