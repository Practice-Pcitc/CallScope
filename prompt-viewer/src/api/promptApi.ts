import axios from "axios";

import type {
  ApiEnvelope,
  CodexSessionListData,
  PromptFilters,
  PromptListData,
  PromptProject,
  PromptRecord,
  PromptStats,
  ToolEventListData
} from "../types/prompt";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api",
  timeout: 15_000
});

export async function getPromptHistory(
  filters: PromptFilters,
  page: number,
  pageSize: number
): Promise<PromptListData> {
  const response = await client.get<ApiEnvelope<PromptListData>>("/prompt-history", {
    params: { ...filters, page, pageSize }
  });
  return response.data.data;
}

export async function getPromptRecord(id: string): Promise<PromptRecord> {
  const response = await client.get<ApiEnvelope<PromptRecord>>(`/prompt-history/${id}`);
  return response.data.data;
}

export async function getPromptStats(): Promise<PromptStats> {
  const response = await client.get<ApiEnvelope<PromptStats>>("/prompt-history/stats");
  return response.data.data;
}

export async function getPromptProjects(): Promise<PromptProject[]> {
  const response = await client.get<ApiEnvelope<PromptProject[]>>(
    "/prompt-history/projects"
  );
  return response.data.data;
}

export async function getCodexSessions(
  filters: PromptFilters,
  page: number,
  pageSize: number
): Promise<CodexSessionListData> {
  const response = await client.get<ApiEnvelope<CodexSessionListData>>(
    "/prompt-history/sessions",
    {
      params: {
        projectId: filters.projectId,
        projectName: filters.projectName,
        sessionId: filters.sessionId,
        startTime: filters.startTime,
        endTime: filters.endTime,
        page,
        pageSize
      }
    }
  );
  return response.data.data;
}

export async function getToolEvents(
  filters: PromptFilters,
  page: number,
  pageSize: number
): Promise<ToolEventListData> {
  const response = await client.get<ApiEnvelope<ToolEventListData>>(
    "/prompt-history/tool-events",
    {
      params: {
        projectId: filters.projectId,
        projectName: filters.projectName,
        sessionId: filters.sessionId,
        startTime: filters.startTime,
        endTime: filters.endTime,
        page,
        pageSize
      }
    }
  );
  return response.data.data;
}
