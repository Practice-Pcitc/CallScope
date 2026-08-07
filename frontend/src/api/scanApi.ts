import { apiClient } from "./client";
import type { ScanTask } from "../types/scan";

interface ScanTaskResponse {
  data: ScanTask;
}

export const scanApi = {
  async start(projectId: string): Promise<ScanTask> {
    const response = await apiClient.post<ScanTaskResponse>(
      `/projects/${projectId}/scan`
    );
    return response.data.data;
  },

  async getStatus(projectId: string): Promise<ScanTask> {
    const response = await apiClient.get<ScanTaskResponse>(
      `/projects/${projectId}/scan-status`
    );
    return response.data.data;
  }
};

