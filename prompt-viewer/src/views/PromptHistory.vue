<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import PromptDetail from "../components/PromptDetail.vue";
import PromptFilter from "../components/PromptFilter.vue";
import PromptStats from "../components/PromptStats.vue";
import PromptTable from "../components/PromptTable.vue";
import SessionTable from "../components/SessionTable.vue";
import ToolEventTable from "../components/ToolEventTable.vue";
import { usePromptStore } from "../stores/promptStore";
import type { PromptFilters } from "../types/prompt";

const route = useRoute();
const store = usePromptStore();
const activeTab = ref<"prompts" | "sessions" | "tools">("prompts");
const callscopeUrl = import.meta.env.VITE_CALLSCOPE_URL ?? "http://localhost:5173";
const initialProjectId = computed(() => {
  const value = route.query.projectId;
  return typeof value === "string" ? value : undefined;
});
const detailOpen = computed({
  get: () => store.selected !== null || store.detailLoading,
  set: (value) => {
    if (!value) store.closeDetail();
  }
});
const activePagination = computed(() => {
  if (activeTab.value === "sessions") return store.sessionPagination;
  if (activeTab.value === "tools") return store.toolPagination;
  return store.pagination;
});
const activeHint = computed(() => {
  if (activeTab.value === "sessions") return "查看会话开始、结束状态和活动数量";
  if (activeTab.value === "tools") return "仅保存工具名称、结果和耗时，不保存输入输出";
  return "点击任意记录查看完整 Prompt";
});

onMounted(async () => {
  if (initialProjectId.value) store.filters.projectId = initialProjectId.value;
  await store.bootstrap();
});

const search = (filters: PromptFilters) => store.applyFilters(filters);
const changePage = (page: number, pageSize: number) => {
  if (activeTab.value === "sessions") return store.changeSessionPage(page, pageSize);
  if (activeTab.value === "tools") return store.changeToolPage(page, pageSize);
  return store.changePage(page, pageSize);
};
</script>

<template>
  <main class="history-page">
    <header class="topbar">
      <a class="brand" :href="callscopeUrl">
        <span class="brand-mark">⌁</span>
        <span><strong>CallScope</strong><small>Prompt History</small></span>
      </a>
      <div class="privacy-note"><i />仅保存在本机</div>
    </header>

    <section class="page-content">
      <div class="page-heading">
        <div>
          <span class="eyebrow">LOCAL AUDIT TRAIL</span>
          <h1>Prompt History</h1>
          <p>查看开发过程中提交给 Codex 的原始问题，并按项目追溯工作上下文。</p>
        </div>
        <el-button @click="store.bootstrap">刷新记录</el-button>
      </div>

      <PromptStats :stats="store.stats" />
      <PromptFilter
        :projects="store.projects"
        :initial-project-id="initialProjectId"
        @search="search"
      />

      <el-alert v-if="store.error" :title="store.error" type="error" show-icon :closable="false" />

      <section class="table-card">
        <div class="table-heading lifecycle-heading">
          <el-tabs v-model="activeTab" class="record-tabs">
            <el-tab-pane name="prompts">
              <template #label>Prompt 记录 <em>{{ store.pagination.total }}</em></template>
            </el-tab-pane>
            <el-tab-pane name="sessions">
              <template #label>Codex 会话 <em>{{ store.sessionPagination.total }}</em></template>
            </el-tab-pane>
            <el-tab-pane name="tools">
              <template #label>工具调用 <em>{{ store.toolPagination.total }}</em></template>
            </el-tab-pane>
          </el-tabs>
          <small>{{ activeHint }}</small>
        </div>
        <div class="table-body">
          <PromptTable
            v-if="activeTab === 'prompts'"
            :items="store.items"
            :loading="store.loading"
            @select="store.openDetail"
          />
          <SessionTable
            v-else-if="activeTab === 'sessions'"
            :items="store.sessions"
            :loading="store.sessionsLoading"
          />
          <ToolEventTable
            v-else
            :items="store.toolEvents"
            :loading="store.toolsLoading"
          />
        </div>
        <el-pagination
          background
          layout="total, sizes, prev, pager, next"
          :total="activePagination.total"
          :current-page="activePagination.page"
          :page-size="activePagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          @change="changePage"
        />
      </section>
    </section>

    <PromptDetail
      v-model="detailOpen"
      :record="store.selected"
      :loading="store.detailLoading"
    />
  </main>
</template>
