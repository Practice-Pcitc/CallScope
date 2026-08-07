import { create } from "zustand";

import { getApiError } from "../api/client";
import { projectApi } from "../api/projectApi";
import { scanApi } from "../api/scanApi";
import type { Project, ProjectCreate } from "../types/project";
import type { ScanTask } from "../types/scan";

interface ProjectState {
  projects: Project[];
  activeProject: Project | null;
  activeScan: ScanTask | null;
  loading: boolean;
  error: string | null;
  setProjects: (projects: Project[]) => void;
  setActiveProject: (project: Project | null) => void;
  fetchProjects: (search?: string) => Promise<void>;
  fetchProject: (projectId: string) => Promise<Project>;
  createProject: (payload: ProjectCreate) => Promise<Project>;
  deleteProject: (projectId: string) => Promise<void>;
  startScan: (projectId: string) => Promise<ScanTask>;
  refreshScan: (projectId: string) => Promise<ScanTask | null>;
}

export const useProjectStore = create<ProjectState>((set) => ({
  projects: [],
  activeProject: null,
  activeScan: null,
  loading: false,
  error: null,
  setProjects: (projects) => set({ projects }),
  setActiveProject: (activeProject) => set({ activeProject }),

  fetchProjects: async (search) => {
    set({ loading: true, error: null });
    try {
      const result = await projectApi.list(search);
      set({ projects: result.items, loading: false });
    } catch (error) {
      const apiError = getApiError(error);
      set({ loading: false, error: apiError.message });
      throw error;
    }
  },

  fetchProject: async (projectId) => {
    set({ loading: true, error: null });
    try {
      const project = await projectApi.get(projectId);
      set({ activeProject: project, loading: false });
      return project;
    } catch (error) {
      const apiError = getApiError(error);
      set({ loading: false, error: apiError.message });
      throw error;
    }
  },

  createProject: async (payload) => {
    set({ loading: true, error: null });
    try {
      const project = await projectApi.create(payload);
      set((state) => ({
        projects: [project, ...state.projects],
        loading: false
      }));
      return project;
    } catch (error) {
      const apiError = getApiError(error);
      set({ loading: false, error: apiError.message });
      throw error;
    }
  },

  deleteProject: async (projectId) => {
    await projectApi.delete(projectId);
    set((state) => ({
      projects: state.projects.filter((project) => project.id !== projectId),
      activeProject:
        state.activeProject?.id === projectId ? null : state.activeProject
    }));
  },

  startScan: async (projectId) => {
    const task = await scanApi.start(projectId);
    set((state) => ({
      activeScan: task,
      activeProject:
        state.activeProject?.id === projectId
          ? { ...state.activeProject, scanStatus: "SCANNING" }
          : state.activeProject
    }));
    return task;
  },

  refreshScan: async (projectId) => {
    try {
      const task = await scanApi.getStatus(projectId);
      set({ activeScan: task });
      return task;
    } catch (error) {
      const apiError = getApiError(error);
      if (apiError.code === "SCAN_NOT_FOUND") {
        set({ activeScan: null });
        return null;
      }
      throw error;
    }
  }
}));

