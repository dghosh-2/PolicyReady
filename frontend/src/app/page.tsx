"use client";

import { useState, useCallback, useEffect } from "react";
import PolicyBrowser from "@/components/PolicyBrowser";
import FileUpload from "@/components/FileUpload";
import ProgressBar from "@/components/ProgressBar";
import QuestionCard from "@/components/QuestionCard";
import HistoryPanel from "@/components/HistoryPanel";
import { analyzeStream } from "@/lib/api";
import { saveToHistory, getHistory } from "@/lib/history";
import type { ComplianceAnswer, AnalysisProgress, IndexStats, AnalysisHistoryItem } from "@/types";

type AnalysisState = "idle" | "analyzing" | "complete" | "error";
type AnalysisPhase = "uploading" | "extracting" | "keywords" | "searching" | "analyzing" | "complete";
type Tab = "analyze" | "history";

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("analyze");
  const [analysisState, setAnalysisState] = useState<AnalysisState>("idle");
  const [phase, setPhase] = useState<AnalysisPhase>("uploading");
  const [status, setStatus] = useState("");
  const [questions, setQuestions] = useState<string[]>([]);
  const [answers, setAnswers] = useState<Record<number, ComplianceAnswer>>({});
  const [progress, setProgress] = useState<AnalysisProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [indexStats, setIndexStats] = useState<IndexStats | null>(null);
  const [currentFilename, setCurrentFilename] = useState<string>("");
  const [historyCount, setHistoryCount] = useState(0);
  const [processingIndices, setProcessingIndices] = useState<Set<number>>(new Set());

  // Load history count on mount
  useEffect(() => {
    setHistoryCount(getHistory().length);
  }, []);

  const handleFileSelect = useCallback(async (file: File) => {
    setAnalysisState("analyzing");
    setPhase("uploading");
    setStatus("Uploading file...");
    setQuestions([]);
    setAnswers({});
    setProgress(null);
    setError(null);
    setCurrentFilename(file.name);
    setActiveTab("analyze");
    setProcessingIndices(new Set());

    try {
      let finalQuestions: string[] = [];
      const finalAnswers: Record<number, ComplianceAnswer> = {};
      let finalProgress: AnalysisProgress | null = null;

      for await (const event of analyzeStream(file)) {
        switch (event.type) {
          case "status":
            setStatus(event.message);
            // Parse status to determine phase
            if (event.message.includes("Extracting questions")) {
              setPhase("extracting");
            } else if (event.message.includes("Extracting keywords") || event.message.includes("keywords")) {
              setPhase("keywords");
            } else if (event.message.includes("Searching") || event.message.includes("search")) {
              setPhase("searching");
            } else if (event.message.includes("Analyzing compliance") || event.message.includes("compliance")) {
              setPhase("analyzing");
            }
            break;

          case "questions":
            finalQuestions = event.questions;
            setQuestions(event.questions);
            setPhase("keywords");
            setProgress({
              answered: 0,
              total: event.total,
              met: 0,
              not_met: 0,
              partial: 0,
            });
            // Mark all questions as pending initially
            setProcessingIndices(new Set());
            break;

          case "answer":
            finalAnswers[event.index] = event.answer;
            setAnswers((prev) => ({
              ...prev,
              [event.index]: event.answer,
            }));
            setProgress(event.progress);
            finalProgress = event.progress;
            // Remove from processing set when answered
            setProcessingIndices((prev) => {
              const next = new Set(prev);
              next.delete(event.index);
              return next;
            });
            break;

          case "complete":
            setAnalysisState("complete");
            setPhase("complete");
            finalProgress = {
              answered: event.total,
              total: event.total,
              met: event.met,
              not_met: event.not_met,
              partial: event.partial,
            };
            setProgress(finalProgress);
            setProcessingIndices(new Set());
            
            // Save to history
            saveToHistory({
              filename: file.name,
              totalQuestions: event.total,
              met: event.met,
              notMet: event.not_met,
              partial: event.partial,
              questions: finalQuestions,
              answers: finalAnswers,
            });
            setHistoryCount(getHistory().length);
            break;

          case "error":
            setAnalysisState("error");
            setError(event.message);
            break;
        }
      }
    } catch (err) {
      setAnalysisState("error");
      setError(err instanceof Error ? err.message : "Analysis failed");
    }
  }, []);

  const handleReset = () => {
    setAnalysisState("idle");
    setPhase("uploading");
    setStatus("");
    setQuestions([]);
    setAnswers({});
    setProgress(null);
    setError(null);
    setCurrentFilename("");
    setProcessingIndices(new Set());
  };

  const handleSelectHistory = (item: AnalysisHistoryItem) => {
    setQuestions(item.questions);
    setAnswers(item.answers);
    setProgress({
      answered: item.totalQuestions,
      total: item.totalQuestions,
      met: item.met,
      not_met: item.notMet,
      partial: item.partial,
    });
    setCurrentFilename(item.filename);
    setAnalysisState("complete");
    setPhase("complete");
    setActiveTab("analyze");
  };

  // Determine which questions are "processing" (in the analyzing phase but not yet answered)
  const isQuestionProcessing = (index: number): boolean => {
    if (phase !== "analyzing") return false;
    return !answers[index];
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-sky-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-sky-100 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-6">
              <h1 className="text-lg font-semibold text-sky-900 tracking-tight">PolicyReady</h1>
              
              {/* Tabs */}
              <nav className="flex items-center gap-1">
                <button
                  onClick={() => setActiveTab("analyze")}
                  className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                    activeTab === "analyze"
                      ? "bg-sky-100 text-sky-900"
                      : "text-sky-600 hover:text-sky-800 hover:bg-sky-50"
                  }`}
                >
                  Analyze
                </button>
                <button
                  onClick={() => setActiveTab("history")}
                  className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
                    activeTab === "history"
                      ? "bg-sky-100 text-sky-900"
                      : "text-sky-600 hover:text-sky-800 hover:bg-sky-50"
                  }`}
                >
                  History
                  {historyCount > 0 && (
                    <span className="text-xs bg-sky-200 text-sky-700 px-1.5 py-0.5 rounded">
                      {historyCount}
                    </span>
                  )}
                </button>
              </nav>
            </div>

            {analysisState !== "idle" && activeTab === "analyze" && (
              <button
                onClick={handleReset}
                className="text-sm text-sky-600 hover:text-sky-800 transition-colors"
              >
                New analysis
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {activeTab === "history" ? (
          <div className="max-w-2xl mx-auto">
            <HistoryPanel
              onSelectHistory={handleSelectHistory}
              onClose={() => setActiveTab("analyze")}
            />
          </div>
        ) : analysisState === "idle" ? (
          /* Initial state - show upload and policy browser */
          <div className="grid lg:grid-cols-2 gap-8">
            <div className="space-y-6">
              <div className="animate-fade-in">
                <h2 className="text-2xl font-semibold text-sky-900 mb-1">
                  Compliance Audit
                </h2>
                <p className="text-sky-600">
                  Upload an audit questionnaire to check policy compliance
                </p>
              </div>

              <div className="animate-fade-in stagger-2">
                <FileUpload
                  onFileSelect={handleFileSelect}
                  disabled={false}
                  isAnalyzing={false}
                />
              </div>

              {/* How it works */}
              <div className="animate-fade-in stagger-3 bg-white rounded-2xl p-5 border border-sky-100">
                <h3 className="font-medium text-sky-900 mb-3 text-sm">How it works</h3>
                <div className="space-y-2.5">
                  {[
                    "Upload your audit questionnaire PDF",
                    "AI extracts and analyzes each question",
                    "Searches policy database for evidence",
                    "Returns compliance status with citations",
                  ].map((step, i) => (
                    <div key={i} className="flex items-center gap-3 text-sm">
                      <span className="w-5 h-5 rounded-full bg-sky-100 text-sky-600 flex items-center justify-center text-xs font-medium">
                        {i + 1}
                      </span>
                      <span className="text-sky-700">{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="animate-fade-in stagger-4">
              <PolicyBrowser onStatsLoaded={setIndexStats} />
              
              {indexStats && (
                <div className="mt-3 px-4 py-2 bg-sky-50 rounded-lg text-xs text-sky-600 border border-sky-100">
                  Index: {indexStats.total_chunks.toLocaleString()} chunks, {indexStats.total_keywords.toLocaleString()} keywords
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Analysis in progress or complete */
          <div className="space-y-6">
            {/* Progress bar - always visible during analysis */}
            {(analysisState === "analyzing" || analysisState === "complete") && (
              <div className="animate-fade-in sticky top-16 z-30">
                <ProgressBar 
                  progress={progress} 
                  status={status} 
                  phase={phase}
                  filename={currentFilename}
                />
              </div>
            )}

            {/* Error state */}
            {analysisState === "error" && (
              <div className="animate-fade-in bg-red-50 border border-red-200 rounded-2xl p-5">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-medium text-red-800">Analysis Failed</h3>
                    <p className="text-red-600 text-sm mt-1">{error}</p>
                    <button
                      onClick={handleReset}
                      className="mt-3 px-3 py-1.5 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                    >
                      Try Again
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Questions list - show as soon as questions are extracted */}
            {questions.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-sky-500 uppercase tracking-wide">
                    Questions ({questions.length})
                  </h3>
                  {progress && progress.answered > 0 && (
                    <span className="text-sm text-sky-600">
                      {progress.answered} / {progress.total} analyzed
                    </span>
                  )}
                </div>

                <div className="space-y-2">
                  {questions.map((question, index) => (
                    <QuestionCard
                      key={index}
                      index={index}
                      question={question}
                      answer={answers[index] || null}
                      isProcessing={isQuestionProcessing(index)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Show loading skeleton while extracting questions */}
            {analysisState === "analyzing" && questions.length === 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-sky-500 uppercase tracking-wide">
                  Questions
                </h3>
                <div className="space-y-2">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div 
                      key={i} 
                      className="bg-white rounded-xl border border-slate-200 p-4 animate-pulse"
                    >
                      <div className="flex items-start gap-3">
                        <div className="w-7 h-7 rounded-full bg-slate-200"></div>
                        <div className="flex-1 space-y-2">
                          <div className="h-4 bg-slate-200 rounded w-full"></div>
                          <div className="h-4 bg-slate-200 rounded w-3/4"></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
