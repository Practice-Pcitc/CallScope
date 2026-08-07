export type ScanTaskStatus =
  | "PENDING"
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED"
  | "CANCELLED";

export type ScanStage =
  | "DISCOVERY"
  | "VALIDATE"
  | "PARSE"
  | "RESOLVE"
  | "PERSIST"
  | "COMPLETED";

export interface ScanError {
  path: string;
  code: string;
  message: string;
}

export interface ScanTask {
  id: string;
  projectId: string;
  revisionId: string;
  status: ScanTaskStatus;
  stage: ScanStage;
  progress: number;
  currentFile: string | null;
  discoveredFiles: number;
  processedFiles: number;
  skippedFiles: number;
  failedFiles: number;
  errorMessage: string | null;
  errors: ScanError[];
  startedAt: string | null;
  finishedAt: string | null;
  createdAt: string;
}
