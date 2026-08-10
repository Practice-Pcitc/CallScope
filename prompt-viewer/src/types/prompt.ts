export interface PromptRecord {
  id: string;
  sessionId: string | null;
  turnId: string | null;
  projectId: string | null;
  projectName: string;
  workingDirectory: string;
  repositoryPath: string | null;
  prompt: string;
  promptLength: number;
  source: string;
  model: string | null;
  permissionMode: string | null;
  gitBranch: string | null;
  gitCommit: string | null;
  endpointIds: string[];
  nodeIds: string[];
  createdAt: string;
}

export interface PromptStats {
  totalPromptCount: number;
  todayPromptCount: number;
  projectCount: number;
  recentPromptCount: number;
  recentDays: number;
}

export interface PromptProject {
  projectId: string | null;
  projectName: string;
  promptCount: number;
  lastPromptAt: string;
}

export interface PromptFilters {
  projectId?: string;
  projectName?: string;
  keyword?: string;
  sessionId?: string;
  startTime?: string;
  endTime?: string;
}

export interface Pagination {
  page: number;
  pageSize: number;
  total: number;
}

export interface ApiEnvelope<T> {
  data: T;
}

export interface PromptListData {
  items: PromptRecord[];
  pagination: Pagination;
}

export interface CodexSession {
  sessionId: string;
  projectId: string | null;
  projectName: string;
  workingDirectory: string;
  repositoryPath: string | null;
  model: string | null;
  permissionMode: string | null;
  gitBranch: string | null;
  gitCommit: string | null;
  startedAt: string;
  endedAt: string | null;
  endReason: string | null;
  status: "active" | "ended";
  promptCount: number;
  toolCallCount: number;
  updatedAt: string;
}

export interface ToolEvent {
  id: string;
  sessionId: string | null;
  turnId: string | null;
  projectId: string | null;
  projectName: string;
  workingDirectory: string;
  toolName: string;
  toolUseId: string | null;
  status: "success" | "failed";
  durationMs: number | null;
  errorType: string | null;
  createdAt: string;
}

export interface CodexSessionListData {
  items: CodexSession[];
  pagination: Pagination;
}

export interface ToolEventListData {
  items: ToolEvent[];
  pagination: Pagination;
}
