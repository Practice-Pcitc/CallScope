import { create } from "zustand";

import { aiAnalysisApi } from "../api/aiAnalysisApi";
import { getApiError } from "../api/client";
import type { AIAnalysisData } from "../types/aiAnalysis";

interface AIAnalysisState {
  analysis: AIAnalysisData | null;
  loading: boolean;
  error: string | null;
  activeTab: string;
  focusedItemKey: string | null;
  analyzeEndpoints: (projectId: string, endpointIds: string[]) => Promise<void>;
  analyzeNode: (projectId: string, nodeId: string) => Promise<void>;
  regenerate: () => Promise<void>;
  setActiveTab: (tab: string) => void;
  setFocusedItemKey: (key: string | null) => void;
  reset: () => void;
}

let requestVersion = 0;
let controller: AbortController | undefined;

const initialState = {
  analysis: null,
  loading: false,
  error: null,
  activeTab: "overview",
  focusedItemKey: null,
};

export const useAIAnalysisStore = create<AIAnalysisState>((set, get) => ({
  ...initialState,

  analyzeEndpoints: async (projectId, endpointIds) => {
    if (!endpointIds.length) {
      set({ error: "请先从左侧选择至少一个接口" });
      return;
    }
    const version = ++requestVersion;
    controller?.abort();
    controller = new AbortController();
    set({ loading: true, error: null, focusedItemKey: null });
    try {
      const analysis = await aiAnalysisApi.endpoints(
        projectId,
        endpointIds,
        {},
        controller.signal,
      );
      if (version !== requestVersion) return;
      set({
        analysis,
        loading: false,
        activeTab: "overview",
        error: analysis.errorMessage,
      });
    } catch (error) {
      if (version !== requestVersion) return;
      set({ loading: false, error: getApiError(error).message });
    }
  },

  analyzeNode: async (projectId, nodeId) => {
    const version = ++requestVersion;
    controller?.abort();
    controller = new AbortController();
    set({ loading: true, error: null, focusedItemKey: null });
    try {
      const analysis = await aiAnalysisApi.nodeImpact(
        projectId,
        nodeId,
        {},
        controller.signal,
      );
      if (version !== requestVersion) return;
      set({
        analysis,
        loading: false,
        activeTab: "impact",
        error: analysis.errorMessage,
      });
    } catch (error) {
      if (version !== requestVersion) return;
      set({ loading: false, error: getApiError(error).message });
    }
  },

  regenerate: async () => {
    const current = get().analysis;
    if (!current) {
      return;
    }
    const version = ++requestVersion;
    controller?.abort();
    controller = new AbortController();
    set({ loading: true, error: null });
    try {
      const analysis = await aiAnalysisApi.regenerate(
        current.analysisId,
        controller.signal,
      );
      if (version !== requestVersion) return;
      set({ analysis, loading: false, error: analysis.errorMessage });
    } catch (error) {
      if (version !== requestVersion) return;
      set({ loading: false, error: getApiError(error).message });
    }
  },

  setActiveTab: (activeTab) => set({ activeTab }),
  setFocusedItemKey: (focusedItemKey) => set({ focusedItemKey }),
  reset: () => {
    controller?.abort();
    requestVersion++;
    set(initialState);
  },
}));
