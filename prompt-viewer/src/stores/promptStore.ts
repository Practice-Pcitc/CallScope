import { defineStore } from "pinia";

import {
  getCodexSessions,
  getPromptHistory,
  getPromptProjects,
  getPromptRecord,
  getPromptStats,
  getToolEvents
} from "../api/promptApi";
import type {
  CodexSession,
  Pagination,
  PromptFilters,
  PromptProject,
  PromptRecord,
  PromptStats,
  ToolEvent
} from "../types/prompt";

interface PromptState {
  items: PromptRecord[];
  stats: PromptStats;
  projects: PromptProject[];
  sessions: CodexSession[];
  toolEvents: ToolEvent[];
  filters: PromptFilters;
  pagination: Pagination;
  sessionPagination: Pagination;
  toolPagination: Pagination;
  selected: PromptRecord | null;
  loading: boolean;
  sessionsLoading: boolean;
  toolsLoading: boolean;
  detailLoading: boolean;
  error: string | null;
}

const emptyStats: PromptStats = {
  totalPromptCount: 0,
  todayPromptCount: 0,
  projectCount: 0,
  recentPromptCount: 0,
  recentDays: 7
};

export const usePromptStore = defineStore("prompt-history", {
  state: (): PromptState => ({
    items: [],
    stats: emptyStats,
    projects: [],
    sessions: [],
    toolEvents: [],
    filters: {},
    pagination: { page: 1, pageSize: 20, total: 0 },
    sessionPagination: { page: 1, pageSize: 20, total: 0 },
    toolPagination: { page: 1, pageSize: 20, total: 0 },
    selected: null,
    loading: false,
    sessionsLoading: false,
    toolsLoading: false,
    detailLoading: false,
    error: null
  }),
  actions: {
    async bootstrap() {
      await Promise.all([
        this.loadList(),
        this.loadSessions(),
        this.loadToolEvents(),
        this.loadStats(),
        this.loadProjects()
      ]);
    },
    async loadList() {
      this.loading = true;
      this.error = null;
      try {
        const data = await getPromptHistory(
          this.filters,
          this.pagination.page,
          this.pagination.pageSize
        );
        this.items = data.items;
        this.pagination = data.pagination;
      } catch {
        this.error = "无法读取 Prompt 历史，请确认 CallScope 后端已经启动。";
      } finally {
        this.loading = false;
      }
    },
    async loadStats() {
      try {
        this.stats = await getPromptStats();
      } catch {
        this.stats = emptyStats;
      }
    },
    async loadProjects() {
      try {
        this.projects = await getPromptProjects();
      } catch {
        this.projects = [];
      }
    },
    async loadSessions() {
      this.sessionsLoading = true;
      try {
        const data = await getCodexSessions(
          this.filters,
          this.sessionPagination.page,
          this.sessionPagination.pageSize
        );
        this.sessions = data.items;
        this.sessionPagination = data.pagination;
      } catch {
        this.sessions = [];
        this.sessionPagination.total = 0;
      } finally {
        this.sessionsLoading = false;
      }
    },
    async loadToolEvents() {
      this.toolsLoading = true;
      try {
        const data = await getToolEvents(
          this.filters,
          this.toolPagination.page,
          this.toolPagination.pageSize
        );
        this.toolEvents = data.items;
        this.toolPagination = data.pagination;
      } catch {
        this.toolEvents = [];
        this.toolPagination.total = 0;
      } finally {
        this.toolsLoading = false;
      }
    },
    async applyFilters(filters: PromptFilters) {
      this.filters = filters;
      this.pagination.page = 1;
      this.sessionPagination.page = 1;
      this.toolPagination.page = 1;
      await Promise.all([this.loadList(), this.loadSessions(), this.loadToolEvents()]);
    },
    async changePage(page: number, pageSize: number) {
      this.pagination.page = page;
      this.pagination.pageSize = pageSize;
      await this.loadList();
    },
    async changeSessionPage(page: number, pageSize: number) {
      this.sessionPagination.page = page;
      this.sessionPagination.pageSize = pageSize;
      await this.loadSessions();
    },
    async changeToolPage(page: number, pageSize: number) {
      this.toolPagination.page = page;
      this.toolPagination.pageSize = pageSize;
      await this.loadToolEvents();
    },
    async openDetail(id: string) {
      this.detailLoading = true;
      try {
        this.selected = await getPromptRecord(id);
      } finally {
        this.detailLoading = false;
      }
    },
    closeDetail() {
      this.selected = null;
    }
  }
});
