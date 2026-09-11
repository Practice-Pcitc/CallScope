import { create } from "zustand";

import { graphApi } from "../api/graphApi";
import type {
  GraphData,
  GraphEdge,
  GraphNode,
  NodeDetail,
  RelationDetail,
  SourceData,
} from "../types/graph";

interface GraphState {
  projectId: string | null;
  roots: string[];
  nodesById: Record<string, GraphNode>;
  edgesById: Record<string, GraphEdge>;
  visibleNodeIds: string[];
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  selectedNodeDetail: NodeDetail | null;
  selectedSource: SourceData | null;
  selectedRelationDetail: RelationDetail | null;
  aiHighlightedNodeIds: string[];
  aiHighlightedEdgeIds: string[];
  loading: boolean;
  detailLoading: boolean;
  error: string | null;
  includeLowerConfidence: boolean;
  layoutVersion: number;
  loadForEndpoints: (projectId: string, endpointIds: string[]) => Promise<void>;
  expandNode: (nodeId: string) => Promise<void>;
  collapseNode: (nodeId: string) => void;
  selectNode: (nodeId: string | null) => Promise<void>;
  selectEdge: (edgeId: string | null) => Promise<void>;
  setIncludeLowerConfidence: (enabled: boolean) => void;
  setAIHighlights: (nodeIds: string[], edgeIds: string[]) => void;
  clearAIHighlights: () => void;
  requestLayout: () => void;
  reset: () => void;
}

const initialState = {
  projectId: null,
  roots: [] as string[],
  nodesById: {} as Record<string, GraphNode>,
  edgesById: {} as Record<string, GraphEdge>,
  visibleNodeIds: [] as string[],
  selectedNodeId: null,
  selectedEdgeId: null,
  selectedNodeDetail: null,
  selectedSource: null,
  selectedRelationDetail: null,
  aiHighlightedNodeIds: [] as string[],
  aiHighlightedEdgeIds: [] as string[],
  loading: false,
  detailLoading: false,
  error: null,
  includeLowerConfidence: false,
  layoutVersion: 0,
};

function graphRecords(data: GraphData) {
  const roots = new Set(data.roots);
  const expandedSources = new Set(data.edges.map((edge) => edge.source));
  return {
    nodesById: Object.fromEntries(
      data.nodes.map((node) => [
        node.id,
        {
          ...node,
          loaded: roots.has(node.id) || expandedSources.has(node.id),
          expanded: roots.has(node.id) || expandedSources.has(node.id),
        },
      ]),
    ),
    edgesById: Object.fromEntries(data.edges.map((edge) => [edge.id, edge])),
  };
}

export const useGraphStore = create<GraphState>((set, get) => ({
  ...initialState,

  loadForEndpoints: async (projectId, endpointIds) => {
    if (endpointIds.length === 0) {
      set({ ...initialState, projectId });
      return;
    }
    set({ loading: true, error: null, projectId });
    try {
      const data =
        endpointIds.length === 1
          ? await graphApi.endpointGraph(
              projectId,
              endpointIds[0],
              get().includeLowerConfidence,
            )
          : await graphApi.combinedGraph(
              projectId,
              endpointIds,
              get().includeLowerConfidence,
            );
      const records = graphRecords(data);
      set((state) => ({
        roots: data.roots,
        ...records,
        visibleNodeIds: data.nodes.map((node) => node.id),
        selectedNodeId: data.roots[0] ?? null,
        selectedEdgeId: null,
        selectedNodeDetail: null,
        selectedSource: null,
        selectedRelationDetail: null,
        aiHighlightedNodeIds: [],
        aiHighlightedEdgeIds: [],
        loading: false,
        layoutVersion: state.layoutVersion + 1,
      }));
      if (data.roots[0]) {
        await get().selectNode(data.roots[0]);
      }
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "拓扑加载失败",
      });
    }
  },

  expandNode: async (nodeId) => {
    const state = get();
    const node = state.nodesById[nodeId];
    if (!node || !state.projectId || !node.hasChildren) {
      return;
    }
    if (node.loaded) {
      set((current) => ({
        visibleNodeIds: Array.from(
          new Set([
            ...current.visibleNodeIds,
            ...Object.values(current.edgesById)
              .filter((edge) => edge.source === nodeId)
              .map((edge) => edge.target),
          ]),
        ),
        nodesById: {
          ...current.nodesById,
          [nodeId]: { ...current.nodesById[nodeId], expanded: true },
        },
        layoutVersion: current.layoutVersion + 1,
      }));
      return;
    }
    set({ loading: true, error: null });
    try {
      const data = await graphApi.children(
        state.projectId,
        nodeId,
        state.includeLowerConfidence,
      );
      set((current) => {
        const parentEntries = current.nodesById[nodeId]?.entryEndpointIds ?? [];
        const nodesById = { ...current.nodesById };
        for (const incoming of data.nodes) {
          const existing = nodesById[incoming.id];
          const entries =
            incoming.entryEndpointIds.length > 0
              ? incoming.entryEndpointIds
              : parentEntries;
          nodesById[incoming.id] = {
            ...existing,
            ...incoming,
            loaded: existing?.loaded || incoming.loaded,
            expanded: existing?.expanded || incoming.expanded,
            entryEndpointIds: Array.from(
              new Set([...(existing?.entryEndpointIds ?? []), ...entries]),
            ),
            shared:
              new Set([...(existing?.entryEndpointIds ?? []), ...entries])
                .size > 1,
          };
        }
        nodesById[nodeId] = {
          ...nodesById[nodeId],
          loaded: true,
          expanded: true,
        };
        const edgesById = { ...current.edgesById };
        for (const incoming of data.edges) {
          edgesById[incoming.id] = {
            ...edgesById[incoming.id],
            ...incoming,
            entryEndpointIds:
              incoming.entryEndpointIds.length > 0
                ? incoming.entryEndpointIds
                : parentEntries,
          };
        }
        return {
          nodesById,
          edgesById,
          visibleNodeIds: Array.from(
            new Set([
              ...current.visibleNodeIds,
              ...data.nodes.map((item) => item.id),
            ]),
          ),
          loading: false,
          layoutVersion: current.layoutVersion + 1,
        };
      });
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "节点展开失败",
      });
    }
  },

  collapseNode: (nodeId) =>
    set((state) => {
      const visible = new Set(state.visibleNodeIds);
      const roots = new Set(state.roots);
      const outgoing = new Map<string, string[]>();
      const incoming = new Map<string, string[]>();
      for (const edge of Object.values(state.edgesById)) {
        outgoing.set(edge.source, [
          ...(outgoing.get(edge.source) ?? []),
          edge.target,
        ]);
        incoming.set(edge.target, [
          ...(incoming.get(edge.target) ?? []),
          edge.source,
        ]);
      }
      const descendants = new Set<string>();
      const queue = [...(outgoing.get(nodeId) ?? [])];
      while (queue.length) {
        const current = queue.shift()!;
        if (descendants.has(current) || roots.has(current)) {
          continue;
        }
        const hasExternalParent = (incoming.get(current) ?? []).some(
          (parent) =>
            parent !== nodeId &&
            visible.has(parent) &&
            !descendants.has(parent),
        );
        if (hasExternalParent) {
          continue;
        }
        descendants.add(current);
        queue.push(...(outgoing.get(current) ?? []));
      }
      descendants.forEach((id) => visible.delete(id));
      return {
        visibleNodeIds: [...visible],
        nodesById: {
          ...state.nodesById,
          [nodeId]: { ...state.nodesById[nodeId], expanded: false },
        },
        selectedNodeId: descendants.has(state.selectedNodeId ?? "")
          ? nodeId
          : state.selectedNodeId,
        layoutVersion: state.layoutVersion + 1,
      };
    }),

  selectNode: async (nodeId) => {
    const projectId = get().projectId;
    set({
      selectedNodeId: nodeId,
      selectedEdgeId: null,
      selectedRelationDetail: null,
    });
    if (!nodeId || !projectId) {
      set({ selectedNodeDetail: null, selectedSource: null });
      return;
    }
    set({ detailLoading: true });
    try {
      const [detail, source] = await Promise.all([
        graphApi.node(projectId, nodeId),
        graphApi.source(projectId, nodeId),
      ]);
      if (get().selectedNodeId === nodeId) {
        set({
          selectedNodeDetail: detail,
          selectedSource: source,
          detailLoading: false,
        });
      }
    } catch {
      set({ detailLoading: false });
    }
  },

  selectEdge: async (edgeId) => {
    const projectId = get().projectId;
    set({
      selectedEdgeId: edgeId,
      selectedNodeId: null,
      selectedNodeDetail: null,
      selectedSource: null,
    });
    if (!edgeId || !projectId) {
      set({ selectedRelationDetail: null });
      return;
    }
    set({ detailLoading: true });
    try {
      const detail = await graphApi.relation(projectId, edgeId);
      if (get().selectedEdgeId === edgeId) {
        set({ selectedRelationDetail: detail, detailLoading: false });
      }
    } catch {
      set({ detailLoading: false });
    }
  },

  setIncludeLowerConfidence: (includeLowerConfidence) =>
    set({ includeLowerConfidence }),
  setAIHighlights: (aiHighlightedNodeIds, aiHighlightedEdgeIds) =>
    set({ aiHighlightedNodeIds, aiHighlightedEdgeIds }),
  clearAIHighlights: () =>
    set({ aiHighlightedNodeIds: [], aiHighlightedEdgeIds: [] }),
  requestLayout: () =>
    set((state) => ({ layoutVersion: state.layoutVersion + 1 })),
  reset: () => set(initialState),
}));
