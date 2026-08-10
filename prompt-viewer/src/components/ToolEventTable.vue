<script setup lang="ts">
import type { ToolEvent } from "../types/prompt";

defineProps<{ items: ToolEvent[]; loading: boolean }>();

const formatTime = (value: string) =>
  new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  }).format(new Date(value));

const formatDuration = (value: number | null) =>
  value === null ? "—" : `${Math.round(value)} ms`;
</script>

<template>
  <el-table v-loading="loading" :data="items" height="100%" empty-text="还没有工具调用记录">
    <el-table-column label="时间" width="150">
      <template #default="scope">{{ formatTime(scope.row.createdAt) }}</template>
    </el-table-column>
    <el-table-column prop="projectName" label="项目" width="180" show-overflow-tooltip />
    <el-table-column prop="toolName" label="工具" min-width="220">
      <template #default="scope"><strong>{{ scope.row.toolName }}</strong></template>
    </el-table-column>
    <el-table-column label="结果" width="110">
      <template #default="scope">
        <el-tag :type="scope.row.status === 'success' ? 'success' : 'danger'" effect="dark">
          {{ scope.row.status === "success" ? "成功" : "失败" }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="耗时" width="120">
      <template #default="scope">{{ formatDuration(scope.row.durationMs) }}</template>
    </el-table-column>
    <el-table-column prop="sessionId" label="Session" min-width="250" show-overflow-tooltip />
    <el-table-column prop="turnId" label="Turn" width="180" show-overflow-tooltip />
    <el-table-column prop="errorType" label="错误类型" width="150">
      <template #default="scope">{{ scope.row.errorType ?? "—" }}</template>
    </el-table-column>
  </el-table>
</template>
