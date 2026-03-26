import TailwindCSS from "@tailwindcss/vite";
import Vue from "@vitejs/plugin-vue";
import Icons from "unplugin-icons/vite";
import { defineConfig } from "vite";
import VueRouter from "vue-router/vite";

export default defineConfig({
  plugins: [VueRouter(), Vue(), TailwindCSS(), Icons({ compiler: "vue3" })],
  resolve: { tsconfigPaths: true },
  build: {
    modulePreload: {
      polyfill: false,
    },
    reportCompressedSize: false,
    rollupOptions: {
      output: {
        manualChunks(id): string | undefined {
          if (
            id.includes("node_modules/@codemirror/lang-java") ||
            id.includes("node_modules/@lezer/java")
          ) {
            return "code-editor-java";
          }

          if (
            id.includes("node_modules/@codemirror/lang-javascript") ||
            id.includes("node_modules/@lezer/javascript")
          ) {
            return "code-editor-javascript";
          }

          if (
            id.includes("node_modules/codemirror") ||
            id.includes("node_modules/@codemirror/") ||
            id.includes("node_modules/@lezer/")
          ) {
            return "code-editor-core";
          }

          if (id.includes("node_modules/echarts")) {
            return "charts";
          }

          if (id.includes("node_modules/mammoth")) {
            return "resume-parser";
          }

          if (
            id.includes("node_modules/vue") ||
            id.includes("node_modules/@vue") ||
            id.includes("node_modules/vue-router") ||
            id.includes("node_modules/@tanstack") ||
            id.includes("node_modules/axios")
          ) {
            return "vendor";
          }

          return undefined;
        },
      },
    },
  },
  server: {
    allowedHosts: ["hiresense.mioyi.net"],
  },
});
