import type {
  PoliciesResponse,
  FolderContentsResponse,
  IndexStats,
  SSEEvent,
  PDFChunk,
} from "@/types";

// Render backend URL for production, localhost for development
const RENDER_API_URL = "https://policyready.onrender.com";

function getApiUrl(): string {
  if (typeof window !== "undefined") {
    const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    if (isLocalhost) {
      return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    }
    // Production - use Render backend directly
    return RENDER_API_URL;
  }
  // Server-side rendering - use Render backend
  return RENDER_API_URL;
}

export async function fetchPolicies(): Promise<PoliciesResponse> {
  const res = await fetch(`${getApiUrl()}/policies`);
  if (!res.ok) throw new Error("Failed to fetch policies");
  return res.json();
}

export async function fetchFolderContents(
  folderName: string
): Promise<FolderContentsResponse> {
  const res = await fetch(`${getApiUrl()}/policies/${encodeURIComponent(folderName)}`);
  if (!res.ok) throw new Error(`Failed to fetch folder: ${folderName}`);
  return res.json();
}

export async function fetchIndexStats(): Promise<IndexStats> {
  const res = await fetch(`${getApiUrl()}/index/stats`);
  if (!res.ok) throw new Error("Index not found. Run 'npm run index' first.");
  return res.json();
}

export async function fetchPDFText(
  folderName: string,
  fileName: string
): Promise<PDFChunk[]> {
  const res = await fetch(
    `${getApiUrl()}/policies/${encodeURIComponent(folderName)}/${encodeURIComponent(fileName)}/text`
  );
  if (!res.ok) throw new Error("Failed to fetch PDF text");
  return res.json();
}

export async function* analyzeStream(
  file: File
): AsyncGenerator<SSEEvent, void, unknown> {
  const formData = new FormData();
  formData.append("file", file);

  let res: Response;
  try {
    res = await fetch(`${getApiUrl()}/analyze/stream`, {
      method: "POST",
      body: formData,
    });
  } catch (networkError) {
    const msg = networkError instanceof Error ? networkError.message : "Network error";
    throw new Error(`Connection failed: ${msg}. Please check your internet connection.`);
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: `Server error: ${res.status} ${res.statusText}` }));
    throw new Error(error.detail || `Analysis failed: ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body from server");

  const decoder = new TextDecoder();
  let buffer = "";

  try {
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
  } catch (streamError) {
    const msg = streamError instanceof Error ? streamError.message : "Stream interrupted";
    throw new Error(`Connection lost during analysis: ${msg}`);
  }
}
