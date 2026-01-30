import type { AnalysisHistoryItem, ComplianceAnswer } from "@/types";

const HISTORY_KEY = "policyready_history";
const MAX_HISTORY_ITEMS = 50;

export function getHistory(): AnalysisHistoryItem[] {
  if (typeof window === "undefined") return [];
  
  try {
    const stored = localStorage.getItem(HISTORY_KEY);
    if (!stored) return [];
    return JSON.parse(stored);
  } catch {
    return [];
  }
}

export function saveToHistory(item: Omit<AnalysisHistoryItem, "id" | "timestamp">): AnalysisHistoryItem {
  const history = getHistory();
  
  const newItem: AnalysisHistoryItem = {
    ...item,
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
  };
  
  // Add to beginning, limit size
  const updated = [newItem, ...history].slice(0, MAX_HISTORY_ITEMS);
  
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
  } catch {
    // Storage full - remove oldest items
    const trimmed = updated.slice(0, 10);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(trimmed));
  }
  
  return newItem;
}

export function deleteFromHistory(id: string): void {
  const history = getHistory();
  const updated = history.filter((item) => item.id !== id);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
}

export function clearHistory(): void {
  localStorage.removeItem(HISTORY_KEY);
}
