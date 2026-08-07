import type {
  AIAnalysisData,
  AnalysisRequest
} from "../types/aiAnalysis";
import { apiClient } from "./client";

interface AIAnalysisResponse {
  data: AIAnalysisData;
}

const defaults: AnalysisRequest = {
  depth: 5,
  includeSource: true,
  includeMediumConfidence: false,
  forceRegenerate: false
};

export const aiAnalysisApi = {
  async endpoints(
    projectId: string,
    endpointIds: string[],
    request: AnalysisRequest = {}
  ): Promise<AIAnalysisData> {
    const payload = { ...defaults, ...request };
    const response =
      endpointIds.length === 1
        ? await apiClient.post<AIAnalysisResponse>(
            `/projects/${projectId}/endpoints/${endpointIds[0]}/ai-analysis`,
            payload,
            { timeout: 120_000 }
          )
        : await apiClient.post<AIAnalysisResponse>(
            `/projects/${projectId}/endpoints/ai-combined-analysis`,
            { ...payload, endpointIds },
            { timeout: 120_000 }
          );
    return response.data.data;
  },

  async nodeImpact(
    projectId: string,
    nodeId: string,
    request: AnalysisRequest = {}
  ): Promise<AIAnalysisData> {
    const response = await apiClient.post<AIAnalysisResponse>(
      `/projects/${projectId}/nodes/${nodeId}/ai-impact-analysis`,
      { ...defaults, ...request },
      { timeout: 120_000 }
    );
    return response.data.data;
  },

  async regenerate(analysisId: string): Promise<AIAnalysisData> {
    const response = await apiClient.post<AIAnalysisResponse>(
      `/ai-analyses/${analysisId}/regenerate`,
      undefined,
      { timeout: 120_000 }
    );
    return response.data.data;
  }
};
