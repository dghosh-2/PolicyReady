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
type Tab = "analyze" | "history";

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("analyze");
  const [analysisState, setAnalysisState] = useState<AnalysisState>("idle");
  const [status, setStatus] = useState("");
  const [questions, setQuestions] = useState<string[]>([]);
  const [answers, setAnswers] = useState<Record<number, ComplianceAnswer>>({});
  const [progress, setProgress] = useState<AnalysisProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [indexStats, setIndexStats] = useState<IndexStats | null>(null);
  const [currentFilename, setCurrentFilename] = useState<string>("");
  const [historyCount, setHistoryCount] = useState(0);

  // Load history count on mount
  useEffect(() => {
    setHistoryCount(getHistory().length);
  }, []);

  const handleFileSelect = useCallback(async (file: File) => {
    setAnalysisState("analyzing");
    setStatus("Starting analysis...");
    setQuestions([]);
    setAnswers({});
    setProgress(null);
    setError(null);
    setCurrentFilename(file.name);
    setActiveTab("analyze");

    try {
      let finalQuestions: string[] = [];
      const finalAnswers: Record<number, ComplianceAnswer> = {};
      let finalProgress: AnalysisProgress | null = null;

      for await (const event of analyzeStream(file)) {
        switch (event.type) {
          case "status":
            setStatus(event.message);
            break;

          case "questions":
            finalQuestions = event.questions;
            setQuestions(event.questions);
            setProgress({
              answered: 0,
              total: event.total,
              met: 0,
              not_met: 0,
              partial: 0,
            });
            break;

          case "answer":
            finalAnswers[event.index] = event.answer;
            setAnswers((prev) => ({
              ...prev,
              [event.index]: event.answer,
            }));
            setProgress(event.progress);
            finalProgress = event.progress;
            break;

          case "complete":
            setAnalysisState("complete");
            finalProgress = {
              answered: event.total,
              total: event.total,
              met: event.met,
              not_met: event.not_met,
              partial: event.partial,
            };
            setProgress(finalProgress);
            
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
    setStatus("");
    setQuestions([]);
    setAnswers({});
    setProgress(null);
    setError(null);
    setCurrentFilename("");
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
    setActiveTab("analyze");
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
                  disabled={analysisState !== "idle"}
                  isAnalyzing={analysisState === "analyzing"}
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
            {/* Progress bar - visible during analysis */}
            {analysisState === "analyzing" && (
              <div className="animate-fade-in">
                <ProgressBar progress={progress} status={status} />
              </div>
            )}

            {/* Complete header */}
            {analysisState === "complete" && progress && (
              <div className="animate-fade-in bg-white rounded-2xl p-5 border border-sky-100">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-sky-900">{currentFilename}</h3>
                    <p className="text-sm text-sky-600 mt-0.5">
                      {progress.total} questions analyzed
                    </p>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
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

            {/* Questions list */}
            {questions.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-sky-500 uppercase tracking-wide">
                  Questions ({questions.length})
                </h3>

                <div className="space-y-2">
                  {questions.map((question, index) => (
                    <QuestionCard
                      key={index}
                      index={index}
                      question={question}
                      answer={answers[index] || null}
                    />
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
