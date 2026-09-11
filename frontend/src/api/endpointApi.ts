import { apiClient } from "./client";
import type { Endpoint, EndpointFilters } from "../types/endpoint";
import type { PaginationMeta } from "../types/project";

interface EndpointListResponse {
  data: {
    items: Endpoint[];
    modules: string[];
    pagination: PaginationMeta;
  };
}

interface EndpointResponse {
  data: Endpoint;
}

export const endpointApi = {
  async list(
    projectId: string,
    filters: EndpointFilters,
  ): Promise<EndpointListResponse["data"]> {
    const response = await apiClient.get<EndpointListResponse>(
      `/projects/${projectId}/endpoints`,
      {
        params: {
          search: filters.search || undefined,
          httpMethod:
            filters.httpMethod === "ALL" ? undefined : filters.httpMethod,
          module: filters.module || undefined,
          pageSize: 200,
        },
      },
    );
    return response.data.data;
  },

  async get(projectId: string, endpointId: string): Promise<Endpoint> {
    const response = await apiClient.get<EndpointResponse>(
      `/projects/${projectId}/endpoints/${endpointId}`,
    );
    return response.data.data;
  },
};
