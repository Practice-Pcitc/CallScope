<script setup lang="ts">
import type { PromptRecord } from "../types/prompt";

defineProps<{ items: PromptRecord[]; loading: boolean }>();
const emit = defineEmits<{ select: [id: string] }>();

const formatTime = (value: string) =>
  new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  }).format(new Date(value));
</script>

<template>
  <el-table
    v-loading="loading"
    :data="items"
    height="100%"
    row-class-name="prompt-row"
    empty-text="还没有 Prompt 记录"
    @row-click="(row: PromptRecord) => emit('select', row.id)"
  >
    <el-table-column label="时间" width="150">
      <template #default="scope">{{ formatTime(scope.row.createdAt) }}</template>
    </el-table-column>
    <el-table-column prop="projectName" label="项目" width="190" show-overflow-tooltip />
    <el-table-column label="Prompt" min-width="440">
      <template #default="scope">
        <div class="prompt-cell">
          <strong>{{ scope.row.prompt }}</strong>
          <span>{{ scope.row.promptLength }} 字符 · {{ scope.row.model ?? "未知模型" }}</span>
        </div>
      </template>
    </el-table-column>
    <el-table-column prop="sessionId" label="Session" width="180" show-overflow-tooltip />
    <el-table-column prop="gitBranch" label="Git Branch" width="150">
      <template #default="scope">
        <el-tag v-if="scope.row.gitBranch" effect="plain">{{ scope.row.gitBranch }}</el-tag>
        <span v-else class="muted">—</span>
      </template>
    </el-table-column>
  </el-table>
</template>
