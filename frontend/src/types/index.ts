export type ComplianceStatus = "MET" | "NOT_MET" | "PARTIAL";

export interface PolicyFolder {
  name: string;
  file_count: number;
}

export interface PolicyFile {
  name: string;
  folder: string;
  path: string;
}

export interface PoliciesResponse {
  folders: PolicyFolder[];
  total_files: number;
}

export interface FolderContentsResponse {
  folder: string;
  files: PolicyFile[];
}

export interface IndexStats {
  total_chunks: number;
  total_keywords: number;
  metadata: {
    created_at: string;
    total_chunks: string;
    total_keywords: string;
    source_dir: string;
  };
}

export interface ComplianceAnswer {
  question: string;
  status: ComplianceStatus;
  evidence: string | null;
  source: string | null;
  page: number | null;
  confidence: number;
  reasoning: string;
}

export interface AnalysisProgress {
  answered: number;
  total: number;
  met: number;
  not_met: number;
  partial: number;
}

// SSE Event Types
export interface SSEStatusEvent {
  type: "status";
  message: string;
}

export interface SSEQuestionsEvent {
  type: "questions";
  questions: string[];
  total: number;
}

export interface SSEAnswerEvent {
  type: "answer";
  index: number;
  answer: ComplianceAnswer;
  progress: AnalysisProgress;
}

export interface SSECompleteEvent {
  type: "complete";
  total: number;
  met: number;
  not_met: number;
  partial: number;
}

export interface SSEErrorEvent {
  type: "error";
  message: string;
}

export type SSEEvent =
  | SSEStatusEvent
  | SSEQuestionsEvent
  | SSEAnswerEvent
  | SSECompleteEvent
  | SSEErrorEvent;

// History types
export interface AnalysisHistoryItem {
  id: string;
  filename: string;
  timestamp: string;
  totalQuestions: number;
  met: number;
  notMet: number;
  partial: number;
  questions: string[];
  answers: Record<number, ComplianceAnswer>;
}

// PDF Preview types
export interface PDFChunk {
  page: number;
  text: string;
}
