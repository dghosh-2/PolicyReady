"use client";

import type { AnalysisProgress, AnalysisPhase } from "@/types";

interface ProgressBarProps {
  progress: AnalysisProgress | null;
  status: string;
  phase: AnalysisPhase;
  filename?: string;
}

const phases: { key: AnalysisPhase; label: string; progressStart: number }[] = [
  { key: "uploading", label: "Upload", progressStart: 0 },
  { key: "extracting", label: "Extract Questions", progressStart: 10 },
  { key: "keywords", label: "Generate Keywords", progressStart: 25 },
  { key: "searching", label: "Search Policies", progressStart: 40 },
  { key: "analyzing", label: "Analyze Compliance", progressStart: 50 },
];

function getPhaseIndex(phase: AnalysisPhase): number {
  const idx = phases.findIndex((p) => p.key === phase);
  return idx >= 0 ? idx : 0;
}

export default function ProgressBar({ progress, status, phase, filename }: ProgressBarProps) {
  const currentPhaseIndex = getPhaseIndex(phase);
  const isComplete = phase === "complete";

  // Calculate overall progress based on phase and question completion
  let overallProgress = 0;
  if (isComplete) {
    overallProgress = 100;
  } else if (progress && phase === "analyzing") {
    // During analyzing phase (50-100%), progress is based on answered questions
    const analyzeProgress = (progress.answered / progress.total) * 50; // 50% of total bar
    overallProgress = Math.min(99, 50 + analyzeProgress);
  } else if (currentPhaseIndex >= 0 && currentPhaseIndex < phases.length) {
    // For other phases, use the defined progress start + a small offset to show activity
    overallProgress = phases[currentPhaseIndex].progressStart + 5;
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-sky-100 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4">
        <div className="flex items-center justify-between mb-1">
          <div>
            <h3 className="font-semibold text-sky-900">
              {isComplete ? "Analysis Complete" : "Analyzing..."}
            </h3>
            {filename && (
              <p className="text-sm text-sky-600 mt-0.5 truncate max-w-xs">{filename}</p>
            )}
          </div>
          <span className="text-2xl font-bold text-sky-700 font-mono tabular-nums">
            {Math.round(overallProgress)}%
          </span>
        </div>

        {/* Main progress bar */}
        <div className="h-2 bg-sky-100 rounded-full overflow-hidden mt-3">
          <div
            className={`h-full transition-all duration-500 ease-out rounded-full ${
              isComplete ? "bg-emerald-500" : "bg-sky-500"
            }`}
            style={{ width: `${overallProgress}%` }}
          />
        </div>

        {/* Phase indicators */}
        <div className="flex items-center justify-between mt-4 gap-1">
          {phases.map((p, idx) => {
            const isActive = idx === currentPhaseIndex && !isComplete;
            const isDone = idx < currentPhaseIndex || isComplete;
            
            return (
              <div key={p.key} className="flex-1 flex flex-col items-center">
                <div
                  className={`
                    w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium
                    transition-all duration-300
                    ${isDone 
                      ? "bg-emerald-500 text-white" 
                      : isActive 
                        ? "bg-sky-500 text-white animate-pulse" 
                        : "bg-slate-200 text-slate-500"
                    }
                  `}
                >
                  {isDone ? (
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    idx + 1
                  )}
                </div>
                <span
                  className={`
                    text-xs mt-1 text-center whitespace-nowrap
                    ${isDone ? "text-emerald-600 font-medium" : isActive ? "text-sky-600 font-medium" : "text-slate-400"}
                  `}
                >
                  {p.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Current status message */}
        {!isComplete && status && (
          <div className="mt-4 flex items-center gap-2 text-sm text-sky-600">
            <div className="w-4 h-4 rounded-full border-2 border-sky-500 border-t-transparent animate-spin"></div>
            <span>{status}</span>
          </div>
        )}
      </div>

      {/* Stats footer - only show when we have progress */}
      {progress && (
        <div className="px-5 py-3 bg-sky-50 border-t border-sky-100">
          <div className="flex items-center justify-between">
            <span className="text-sm text-sky-700">
              {progress.answered} of {progress.total} questions processed
            </span>
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                <span className="text-sky-700 tabular-nums">{progress.met}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-amber-500"></div>
                <span className="text-sky-700 tabular-nums">{progress.partial}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-red-500"></div>
                <span className="text-sky-700 tabular-nums">{progress.not_met}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
