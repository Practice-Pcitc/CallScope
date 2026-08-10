import { createRouter, createWebHistory } from "vue-router";

import PromptHistory from "../views/PromptHistory.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/prompt-history" },
    { path: "/prompt-history", component: PromptHistory }
  ]
});
