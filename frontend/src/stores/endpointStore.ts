import { create } from "zustand";

import { endpointApi } from "../api/endpointApi";
import type {
  Endpoint,
  EndpointFilters,
  HttpMethod
} from "../types/endpoint";

interface EndpointState {
  endpoints: Endpoint[];
  modules: string[];
  total: number;
  selectedIds: string[];
  activeEndpointId: string | null;
  filters: EndpointFilters;
  loading: boolean;
  fetchEndpoints: (projectId: string) => Promise<void>;
  setSearch: (search: string) => void;
  setHttpMethod: (httpMethod: HttpMethod | "ALL") => void;
  setModule: (module: string) => void;
  toggleSelected: (endpointId: string) => void;
  selectEndpoint: (endpointId: string) => void;
  selectAll: () => void;
  clearSelection: () => void;
  reset: () => void;
}

const initialState = {
  endpoints: [],
  modules: [],
  total: 0,
  selectedIds: [],
  activeEndpointId: null,
  filters: {
    search: "",
    httpMethod: "ALL" as const,
    module: ""
  },
  loading: false
};

export const useEndpointStore = create<EndpointState>((set, get) => ({
  ...initialState,

  fetchEndpoints: async (projectId) => {
    set({ loading: true });
    try {
      const result = await endpointApi.list(projectId, get().filters);
      const visibleIds = new Set(result.items.map((endpoint) => endpoint.id));
      set((state) => ({
        endpoints: result.items,
        modules: result.modules,
        total: result.pagination.total,
        selectedIds: state.selectedIds.filter((id) => visibleIds.has(id)),
        activeEndpointId:
          state.activeEndpointId && visibleIds.has(state.activeEndpointId)
            ? state.activeEndpointId
            : null,
        loading: false
      }));
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  setSearch: (search) =>
    set((state) => ({ filters: { ...state.filters, search } })),
  setHttpMethod: (httpMethod) =>
    set((state) => ({ filters: { ...state.filters, httpMethod } })),
  setModule: (module) =>
    set((state) => ({ filters: { ...state.filters, module } })),

  toggleSelected: (endpointId) =>
    set((state) => ({
      selectedIds: state.selectedIds.includes(endpointId)
        ? state.selectedIds.filter((id) => id !== endpointId)
        : [...state.selectedIds, endpointId],
      activeEndpointId: endpointId
    })),

  selectEndpoint: (endpointId) =>
    set((state) => ({
      activeEndpointId: endpointId,
      selectedIds: state.selectedIds.includes(endpointId)
        ? state.selectedIds
        : [...state.selectedIds, endpointId]
    })),

  selectAll: () =>
    set((state) => ({
      selectedIds: state.endpoints.map((endpoint) => endpoint.id),
      activeEndpointId:
        state.activeEndpointId ?? state.endpoints[0]?.id ?? null
    })),

  clearSelection: () => set({ selectedIds: [], activeEndpointId: null }),
  reset: () => set(initialState)
}));

