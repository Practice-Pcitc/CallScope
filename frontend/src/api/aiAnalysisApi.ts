import type { AIAnalysisData, AnalysisRequest } from "../types/aiAnalysis";
import { apiClient } from "./client";

interface AIAnalysisResponse {
  data: AIAnalysisData;
}

const defaults: AnalysisRequest = {
  depth: 5,
  includeSource: true,
  includeMediumConfidence: false,
  forceRegenerate: false,
};

export const aiAnalysisApi = {
  async endpoints(
    projectId: string,
    endpointIds: string[],
    request: AnalysisRequest = {},
    signal?: AbortSignal,
  ): Promise<AIAnalysisData> {
    const payload = { ...defaults, ...request };
    const response =
      endpointIds.length === 1
        ? await apiClient.post<AIAnalysisResponse>(
            `/projects/${projectId}/endpoints/${endpointIds[0]}/ai-analyses`,
            payload,
            { timeout: 120_000, signal },
          )
        : await apiClient.post<AIAnalysisResponse>(
            `/projects/${projectId}/endpoints/combined-ai-analyses`,
            { ...payload, endpointIds },
            { timeout: 120_000, signal },
          );
    return waitForAnalysis(response.data.data, signal);
  },

  async nodeImpact(
    projectId: string,
    nodeId: string,
    request: AnalysisRequest = {},
    signal?: AbortSignal,
  ): Promise<AIAnalysisData> {
    const response = await apiClient.post<AIAnalysisResponse>(
      `/projects/${projectId}/nodes/${nodeId}/impact-ai-analyses`,
      { ...defaults, ...request },
      { timeout: 120_000, signal },
    );
    return waitForAnalysis(response.data.data, signal);
  },

  async regenerate(
    analysisId: string,
    signal?: AbortSignal,
  ): Promise<AIAnalysisData> {
    const response = await apiClient.post<AIAnalysisResponse>(
      `/ai-analyses/${analysisId}/regenerate`,
      undefined,
      { timeout: 120_000, signal },
    );
    return waitForAnalysis(response.data.data, signal);
  },
};

export async function waitForAnalysis(
  analysis: AIAnalysisData,
  signal?: AbortSignal,
): Promise<AIAnalysisData> {
  const deadline = Date.now() + 35 * 60_000;
  while (analysis.status === "ANALYZING") {
    signal?.throwIfAborted();
    if (Date.now() >= deadline) {
      throw new Error("分析仍在执行，请稍后重试查询");
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
    signal?.throwIfAborted();
    const response = await apiClient.get<AIAnalysisResponse>(
      `/ai-analyses/${analysis.analysisId}`,
      { signal },
    );
    analysis = response.data.data;
  }
  return analysis;
}
