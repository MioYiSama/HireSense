import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import { handleHotUpdate, routes } from "vue-router/auto-routes";

import { QueryClient, VueQueryPlugin } from "@tanstack/vue-query";
import App from "./App.vue";

const router = createRouter({
  history: createWebHistory(),
  routes,
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnReconnect: false,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
    },
    mutations: {
      retry: false,
    },
  },
});

createApp(App).use(router).use(VueQueryPlugin, { queryClient }).mount("#app");

if (import.meta.hot) {
  handleHotUpdate(router);
}
