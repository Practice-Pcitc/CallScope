<script setup lang="ts">
import type { CodexSession } from "../types/prompt";

defineProps<{ items: CodexSession[]; loading: boolean }>();

const formatTime = (value: string | null) =>
  value
    ? new Intl.DateTimeFormat("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false
      }).format(new Date(value))
    : "—";
</script>

<template>
  <el-table v-loading="loading" :data="items" height="100%" empty-text="还没有 Codex 会话记录">
    <el-table-column label="开始时间" width="150">
      <template #default="scope">{{ formatTime(scope.row.startedAt) }}</template>
    </el-table-column>
    <el-table-column prop="projectName" label="项目" width="180" show-overflow-tooltip />
    <el-table-column prop="sessionId" label="Session" min-width="250" show-overflow-tooltip />
    <el-table-column label="状态" width="110">
      <template #default="scope">
        <el-tag :type="scope.row.status === 'ended' ? 'info' : 'success'" effect="dark">
          {{ scope.row.status === "ended" ? "已结束" : "进行中" }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="promptCount" label="Prompt" width="100" align="center" />
    <el-table-column prop="toolCallCount" label="工具调用" width="110" align="center" />
    <el-table-column label="结束时间" width="150">
      <template #default="scope">{{ formatTime(scope.row.endedAt) }}</template>
    </el-table-column>
    <el-table-column prop="gitBranch" label="Git Branch" width="140">
      <template #default="scope">
        <el-tag v-if="scope.row.gitBranch" effect="plain">{{ scope.row.gitBranch }}</el-tag>
        <span v-else class="muted">—</span>
      </template>
    </el-table-column>
  </el-table>
</template>
