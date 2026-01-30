"use client";

import type { AnalysisProgress } from "@/types";

interface ProgressBarProps {
  progress: AnalysisProgress | null;
  status: string;
}

export default function ProgressBar({ progress, status }: ProgressBarProps) {
  if (!progress) {
    return (
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-sky-100">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 rounded-full border-2 border-sky-500 border-t-transparent animate-spin"></div>
          <span className="text-sky-700">{status || "Initializing..."}</span>
        </div>
      </div>
    );
  }

  const percentage = Math.round((progress.answered / progress.total) * 100);

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-sky-100 overflow-hidden">
      {/* Header with counts */}
      <div className="px-5 py-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-sky-900">Processing</h3>
          <span className="text-xl font-bold text-sky-700 font-mono">{percentage}%</span>
        </div>

        {/* Progress bar */}
        <div className="h-2 bg-sky-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-sky-500 transition-all duration-300 ease-out rounded-full"
            style={{ width: `${percentage}%` }}
          />
        </div>

        <p className="text-sm text-sky-600 mt-2">
          {progress.answered} of {progress.total} questions
        </p>
      </div>

      {/* Status breakdown */}
      <div className="px-5 py-3 bg-sky-50 border-t border-sky-100 flex items-center gap-6 text-sm">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
          <span className="text-sky-700">{progress.met} met</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-amber-500"></div>
          <span className="text-sky-700">{progress.partial} partial</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-red-500"></div>
          <span className="text-sky-700">{progress.not_met} not met</span>
        </div>
      </div>
    </div>
  );
}
