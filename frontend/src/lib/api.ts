import type {
  PoliciesResponse,
  FolderContentsResponse,
  IndexStats,
  SSEEvent,
  PDFChunk,
} from "@/types";

// Helper to get the API base URL at runtime
function getApiUrl(): string {
  // In browser, check if we're on localhost
  if (typeof window !== "undefined") {
    const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    if (isLocalhost) {
      // Local development - use the env var or default to localhost:8000
      return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    }
    // Production - use relative URLs
    return "";
  }
  // Server-side rendering - use relative URLs (will be resolved by the browser)
  return "";
}

// Helper to get the API prefix
function getApiPrefix(): string {
  const apiUrl = getApiUrl();
  // If using absolute URL (local dev), no prefix needed since FastAPI handles routes directly
  // If using relative URL (production), add /api prefix for Vercel routing
  return apiUrl ? "" : "/api";
}

export async function fetchPolicies(): Promise<PoliciesResponse> {
  const res = await fetch(`${getApiUrl()}${getApiPrefix()}/policies`);
  if (!res.ok) throw new Error("Failed to fetch policies");
  return res.json();
}

export async function fetchFolderContents(
  folderName: string
): Promise<FolderContentsResponse> {
  const res = await fetch(`${getApiUrl()}${getApiPrefix()}/policies/${encodeURIComponent(folderName)}`);
  if (!res.ok) throw new Error(`Failed to fetch folder: ${folderName}`);
  return res.json();
}

export async function fetchIndexStats(): Promise<IndexStats> {
  const res = await fetch(`${getApiUrl()}${getApiPrefix()}/index/stats`);
  if (!res.ok) throw new Error("Index not found. Run 'npm run index' first.");
  return res.json();
}

export async function fetchPDFText(
  folderName: string,
  fileName: string
): Promise<PDFChunk[]> {
  const res = await fetch(
    `${getApiUrl()}${getApiPrefix()}/policies/${encodeURIComponent(folderName)}/${encodeURIComponent(fileName)}/text`
  );
  if (!res.ok) throw new Error("Failed to fetch PDF text");
  return res.json();
}

export async function* analyzeStream(
  file: File
): AsyncGenerator<SSEEvent, void, unknown> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${getApiUrl()}${getApiPrefix()}/analyze/stream`, {
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
