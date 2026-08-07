import { apiClient } from "./client";
import type {
  PaginationMeta,
  Project,
  ProjectCreate
} from "../types/project";

interface ProjectResponse {
  data: Project;
}

interface ProjectListResponse {
  data: {
    items: Project[];
    pagination: PaginationMeta;
  };
}

export const projectApi = {
  async list(search?: string): Promise<ProjectListResponse["data"]> {
    const response = await apiClient.get<ProjectListResponse>("/projects", {
      params: search ? { search } : undefined
    });
    return response.data.data;
  },

  async get(projectId: string): Promise<Project> {
    const response = await apiClient.get<ProjectResponse>(`/projects/${projectId}`);
    return response.data.data;
  },

  async create(payload: ProjectCreate): Promise<Project> {
    const response = await apiClient.post<ProjectResponse>("/projects", payload);
    return response.data.data;
  },

  async delete(projectId: string): Promise<void> {
    await apiClient.delete(`/projects/${projectId}`);
  }
};

