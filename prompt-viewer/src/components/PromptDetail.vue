<script setup lang="ts">
import { ElMessage } from "element-plus";

import type { PromptRecord } from "../types/prompt";

defineProps<{
  modelValue: boolean;
  record: PromptRecord | null;
  loading: boolean;
}>();
const emit = defineEmits<{ "update:modelValue": [value: boolean] }>();

async function copyPrompt(prompt: string) {
  await navigator.clipboard.writeText(prompt);
  ElMessage.success("Prompt 已复制");
}
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    title="Prompt 详情"
    size="min(720px, 92vw)"
    destroy-on-close
    @close="emit('update:modelValue', false)"
  >
    <div v-loading="loading" class="detail-body">
      <template v-if="record">
        <div class="detail-heading">
          <div>
            <span class="eyebrow">PROMPT ORIGINAL</span>
            <h2>{{ record.projectName }}</h2>
          </div>
          <el-button type="primary" plain @click="copyPrompt(record.prompt)">复制 Prompt</el-button>
        </div>
        <pre class="prompt-original">{{ record.prompt }}</pre>
        <dl class="metadata-grid">
          <div><dt>创建时间</dt><dd>{{ new Date(record.createdAt).toLocaleString() }}</dd></div>
          <div><dt>项目名称</dt><dd>{{ record.projectName }}</dd></div>
          <div><dt>工作目录</dt><dd>{{ record.workingDirectory }}</dd></div>
          <div><dt>Git 仓库</dt><dd>{{ record.repositoryPath ?? "—" }}</dd></div>
          <div><dt>Git Branch</dt><dd>{{ record.gitBranch ?? "—" }}</dd></div>
          <div><dt>Git Commit</dt><dd>{{ record.gitCommit ?? "—" }}</dd></div>
          <div><dt>Session ID</dt><dd>{{ record.sessionId ?? "—" }}</dd></div>
          <div><dt>Turn ID</dt><dd>{{ record.turnId ?? "—" }}</dd></div>
          <div><dt>模型</dt><dd>{{ record.model ?? "—" }}</dd></div>
          <div><dt>记录来源</dt><dd>{{ record.source }}</dd></div>
        </dl>
      </template>
    </div>
  </el-drawer>
</template>
