import { apiClient } from "./client";
import type {
  GraphData,
  NodeDetail,
  RelationDetail,
  SourceData,
} from "../types/graph";

interface DataResponse<T> {
  data: T;
}

export const graphApi = {
  async endpointGraph(
    projectId: string,
    endpointId: string,
    includeLowerConfidence = false,
    depth = 5,
  ): Promise<GraphData> {
    const response = await apiClient.get<DataResponse<GraphData>>(
      `/projects/${projectId}/endpoints/${endpointId}/graphs`,
      { params: { includeLowerConfidence, depth } },
    );
    return response.data.data;
  },

  async combinedGraph(
    projectId: string,
    endpointIds: string[],
    includeLowerConfidence = false,
    depth = 5,
  ): Promise<GraphData> {
    const response = await apiClient.post<DataResponse<GraphData>>(
      `/projects/${projectId}/graphs/combined`,
      { endpointIds, includeLowerConfidence, depth },
    );
    return response.data.data;
  },

  async children(
    projectId: string,
    nodeId: string,
    includeLowerConfidence = false,
  ): Promise<GraphData> {
    const response = await apiClient.get<DataResponse<GraphData>>(
      `/projects/${projectId}/nodes/${nodeId}/children`,
      { params: { includeLowerConfidence } },
    );
    return response.data.data;
  },

  async node(projectId: string, nodeId: string): Promise<NodeDetail> {
    const response = await apiClient.get<DataResponse<NodeDetail>>(
      `/projects/${projectId}/nodes/${nodeId}`,
    );
    return response.data.data;
  },

  async source(projectId: string, nodeId: string): Promise<SourceData> {
    const response = await apiClient.get<DataResponse<SourceData>>(
      `/projects/${projectId}/nodes/${nodeId}/source`,
    );
    return response.data.data;
  },

  async relation(
    projectId: string,
    relationId: string,
  ): Promise<RelationDetail> {
    const response = await apiClient.get<DataResponse<RelationDetail>>(
      `/projects/${projectId}/relations/${relationId}`,
    );
    return response.data.data;
  },
};
