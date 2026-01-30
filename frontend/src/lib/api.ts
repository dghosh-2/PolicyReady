import type {
  PoliciesResponse,
  FolderContentsResponse,
  IndexStats,
  SSEEvent,
  PDFChunk,
} from "@/types";

// Use relative URLs for Vercel deployment, absolute for local dev
// In local dev, set NEXT_PUBLIC_API_URL=http://localhost:8000 in .env.local
// In production (Vercel), always use relative URLs regardless of env var
const isProduction = typeof window !== "undefined" && !window.location.hostname.includes("localhost");
const envApiUrl = process.env.NEXT_PUBLIC_API_URL || "";
const API_BASE = isProduction ? "" : envApiUrl;

// For local development, don't add /api prefix since FastAPI handles routes directly
const API_PREFIX = API_BASE ? "" : "/api";

export async function fetchPolicies(): Promise<PoliciesResponse> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/policies`);
  if (!res.ok) throw new Error("Failed to fetch policies");
  return res.json();
}

export async function fetchFolderContents(
  folderName: string
): Promise<FolderContentsResponse> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/policies/${encodeURIComponent(folderName)}`);
  if (!res.ok) throw new Error(`Failed to fetch folder: ${folderName}`);
  return res.json();
}

export async function fetchIndexStats(): Promise<IndexStats> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/index/stats`);
  if (!res.ok) throw new Error("Index not found. Run 'npm run index' first.");
  return res.json();
}

export async function fetchPDFText(
  folderName: string,
  fileName: string
): Promise<PDFChunk[]> {
  const res = await fetch(
    `${API_BASE}${API_PREFIX}/policies/${encodeURIComponent(folderName)}/${encodeURIComponent(fileName)}/text`
  );
  if (!res.ok) throw new Error("Failed to fetch PDF text");
  return res.json();
}

export async function* analyzeStream(
  file: File
): AsyncGenerator<SSEEvent, void, unknown> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}${API_PREFIX}/analyze/stream`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Analysis failed" }));
    throw new Error(error.detail || "Analysis failed");
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6)) as SSEEvent;
          yield data;
        } catch {
          // Skip malformed JSON
        }
      }
    }
  }
}
