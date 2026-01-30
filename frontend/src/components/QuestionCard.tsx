"use client";

import type { ComplianceAnswer, ComplianceStatus } from "@/types";

interface QuestionCardProps {
  index: number;
  question: string;
  answer: ComplianceAnswer | null;
}

const statusConfig: Record<ComplianceStatus, { bg: string; text: string; border: string; dot: string; label: string }> = {
  MET: {
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200",
    dot: "bg-emerald-500",
    label: "Met",
  },
  PARTIAL: {
    bg: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-200",
    dot: "bg-amber-500",
    label: "Partial",
  },
  NOT_MET: {
    bg: "bg-red-50",
    text: "text-red-700",
    border: "border-red-200",
    dot: "bg-red-500",
    label: "Not Met",
  },
};

export default function QuestionCard({ index, question, answer }: QuestionCardProps) {
  const config = answer ? statusConfig[answer.status] : null;

  return (
    <div
      className={`
        rounded-xl border transition-all duration-200 overflow-hidden
        ${answer ? `${config?.bg} ${config?.border}` : "bg-white border-slate-200"}
        ${answer ? "animate-fade-in" : ""}
      `}
    >
      {/* Question header */}
      <div className="px-4 py-3 flex items-start gap-3">
        {/* Number / Status indicator */}
        <div
          className={`
            flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium
            ${answer ? `${config?.bg} ${config?.text} border ${config?.border}` : "bg-slate-100 text-slate-500"}
          `}
        >
          {answer ? (
            <div className={`w-2.5 h-2.5 rounded-full ${config?.dot}`}></div>
          ) : (
            index + 1
          )}
        </div>

        {/* Question text */}
        <div className="flex-1 min-w-0">
          <p className={`text-sm ${answer ? config?.text : "text-slate-700"}`}>
            {question}
          </p>

          {/* Loading state */}
          {!answer && (
            <div className="mt-2 flex items-center gap-2 text-slate-400 text-xs">
              <div className="w-3 h-3 rounded-full border-2 border-slate-300 border-t-transparent animate-spin"></div>
              <span>Analyzing...</span>
            </div>
          )}
        </div>

        {/* Status badge */}
        {answer && (
          <span
            className={`
              flex-shrink-0 px-2 py-0.5 rounded text-xs font-medium
              ${config?.bg} ${config?.text}
            `}
          >
            {config?.label}
          </span>
        )}
      </div>

      {/* Evidence section */}
      {answer && (answer.evidence || answer.source) && (
        <div className={`px-4 py-3 border-t ${config?.border} bg-white/60`}>
          {answer.evidence && (
            <div className="mb-2">
              <blockquote className={`text-xs ${config?.text} italic border-l-2 ${config?.border} pl-2`}>
                &ldquo;{answer.evidence}&rdquo;
              </blockquote>
            </div>
          )}

          {answer.source && (
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="font-mono">
                {answer.source}
                {answer.page && ` p.${answer.page}`}
              </span>
            </div>
          )}
        </div>
      )}

      {/* No evidence found */}
      {answer && !answer.evidence && answer.status === "NOT_MET" && (
        <div className={`px-4 py-2 border-t ${config?.border} bg-white/60`}>
          <p className="text-xs text-red-600">No matching policy found</p>
        </div>
      )}
    </div>
  );
}
