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
  },
});
