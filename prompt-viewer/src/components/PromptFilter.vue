<script setup lang="ts">
import { reactive, watch } from "vue";

import type { PromptFilters, PromptProject } from "../types/prompt";

const props = defineProps<{
  projects: PromptProject[];
  initialProjectId?: string;
}>();
const emit = defineEmits<{ search: [filters: PromptFilters] }>();

const form = reactive({
  projectId: props.initialProjectId ?? "",
  keyword: "",
  sessionId: "",
  range: [] as Date[]
});

watch(
  () => props.initialProjectId,
  (value) => {
    form.projectId = value ?? "";
    if (value) submit();
  }
);

function submit() {
  emit("search", {
    projectId: form.projectId || undefined,
    keyword: form.keyword.trim() || undefined,
    sessionId: form.sessionId.trim() || undefined,
    startTime: form.range[0]?.toISOString(),
    endTime: form.range[1]?.toISOString()
  });
}

function reset() {
  form.projectId = "";
  form.keyword = "";
  form.sessionId = "";
  form.range = [];
  submit();
}
</script>

<template>
  <section class="filter-bar">
    <el-select v-model="form.projectId" clearable placeholder="全部项目" @change="submit">
      <el-option
        v-for="project in projects"
        :key="`${project.projectId}-${project.projectName}`"
        :label="`${project.projectName} · ${project.promptCount}`"
        :value="project.projectId ?? ''"
      />
    </el-select>
    <el-input
      v-model="form.keyword"
      clearable
      placeholder="搜索 Prompt 原文"
      @keyup.enter="submit"
    />
    <el-input
      v-model="form.sessionId"
      clearable
      placeholder="Session ID"
      @keyup.enter="submit"
    />
    <el-date-picker
      class="filter-date"
      v-model="form.range"
      type="datetimerange"
      range-separator="至"
      start-placeholder="开始时间"
      end-placeholder="结束时间"
      @change="submit"
    />
    <div class="filter-actions">
      <el-button type="primary" @click="submit">查询</el-button>
      <el-button @click="reset">重置</el-button>
    </div>
  </section>
</template>
