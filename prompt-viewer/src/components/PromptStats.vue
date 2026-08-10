<script setup lang="ts">
import type { PromptStats } from "../types/prompt";

defineProps<{ stats: PromptStats }>();
</script>

<template>
  <section class="stats-grid" aria-label="Prompt 统计">
    <article class="stat-card">
      <span>总记录</span>
      <strong>{{ stats.totalPromptCount }}</strong>
      <small>本机累计 Prompt</small>
    </article>
    <article class="stat-card accent-green">
      <span>今日</span>
      <strong>{{ stats.todayPromptCount }}</strong>
      <small>今天新增记录</small>
    </article>
    <article class="stat-card accent-blue">
      <span>项目</span>
      <strong>{{ stats.projectCount }}</strong>
      <small>关联项目数量</small>
    </article>
    <article class="stat-card accent-orange">
      <span>最近 {{ stats.recentDays }} 天</span>
      <strong>{{ stats.recentPromptCount }}</strong>
      <small>近期使用次数</small>
    </article>
  </section>
</template>
