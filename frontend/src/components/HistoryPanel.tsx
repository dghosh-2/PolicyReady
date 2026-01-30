"use client";

import { useState, useEffect } from "react";
import { getHistory, deleteFromHistory, clearHistory } from "@/lib/history";
import type { AnalysisHistoryItem } from "@/types";

interface HistoryPanelProps {
  onSelectHistory: (item: AnalysisHistoryItem) => void;
  onClose: () => void;
}

export default function HistoryPanel({ onSelectHistory, onClose }: HistoryPanelProps) {
  const [history, setHistory] = useState<AnalysisHistoryItem[]>([]);

  useEffect(() => {
    setHistory(getHistory());
  }, []);

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    deleteFromHistory(id);
    setHistory(getHistory());
  };

  const handleClearAll = () => {
    if (confirm("Clear all history? This cannot be undone.")) {
      clearHistory();
      setHistory([]);
    }
  };

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
    });
  };

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-sky-200 overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="px-5 py-4 border-b border-sky-100 bg-sky-50 flex items-center justify-between">
        <h2 className="font-semibold text-sky-900">Analysis History</h2>
        <div className="flex items-center gap-2">
          {history.length > 0 && (
            <button
              onClick={handleClearAll}
              className="text-xs text-sky-500 hover:text-red-600 transition-colors"
            >
              Clear all
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-sky-100 rounded-lg transition-colors"
          >
            <svg className="w-4 h-4 text-sky-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* List */}
      <div className="max-h-[400px] overflow-y-auto">
        {history.length === 0 ? (
          <div className="px-5 py-12 text-center text-sky-500">
            <svg className="w-12 h-12 mx-auto mb-3 text-sky-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sky-700">No analysis history yet</p>
            <p className="text-sm mt-1 text-sky-500">Your past analyses will appear here</p>
          </div>
        ) : (
          <div className="divide-y divide-sky-50">
            {history.map((item) => (
              <button
                key={item.id}
                onClick={() => onSelectHistory(item)}
                className="w-full px-5 py-4 text-left hover:bg-sky-50 transition-colors group"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-sky-900 truncate">{item.filename}</p>
                    <p className="text-sm text-sky-500 mt-0.5">
                      {item.totalQuestions} questions
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-sky-400">{formatDate(item.timestamp)}</span>
                    <button
                      onClick={(e) => handleDelete(item.id, e)}
                      className="p-1 opacity-0 group-hover:opacity-100 hover:bg-sky-100 rounded transition-all"
                    >
                      <svg className="w-3.5 h-3.5 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>

                {/* Stats bar */}
                <div className="flex items-center gap-4 mt-2 text-xs">
                  <span className="text-emerald-600">{item.met} met</span>
                  <span className="text-amber-600">{item.partial} partial</span>
                  <span className="text-red-600">{item.notMet} not met</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
