import { API_URL } from "@/lib/config";

export interface UploadResult {
  file_id: string;
  file_path: string;
  filename: string;
}

export interface KbStats {
  total_chunks: number;
  sources: Record<string, number>;
  ready: boolean;
}

export interface KbIngestResult {
  success: boolean;
  chunks_added?: number;
  error?: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`.trim());
  return res.json() as Promise<T>;
}

function formData(file: File) {
  const body = new FormData();
  body.append("file", file);
  return body;
}

export const uploadFile = (file: File) =>
  request<UploadResult>("/upload", { method: "POST", body: formData(file) });

export const getKbStats = () => request<KbStats>("/api/kb/stats");

export const ingestKbFile = (file: File) =>
  request<KbIngestResult>("/api/kb/ingest-file?doc_type=document", {
    method: "POST",
    body: formData(file),
  });

export const clearKb = () =>
  request<{ success: boolean; message: string }>("/api/kb/clear", { method: "DELETE" });

export const downloadUrl = (filename: string) =>
  `${API_URL}/download/${encodeURIComponent(filename)}`;
