<script setup lang="ts">
interface Props {
  show?: boolean;
  title?: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
  type?: "default" | "warning" | "danger";
  loading?: boolean;
  errorMessage?: string;
}

const props = withDefaults(defineProps<Props>(), {
  show: false,
  title: "确认",
  message: "确定要执行此操作吗？",
  confirmText: "确定",
  cancelText: "取消",
  type: "default",
  loading: false,
  errorMessage: "",
});

const emit = defineEmits<{
  confirm: [];
  cancel: [];
}>();

const typeStyles = {
  default: {
    icon: "text-blue-400",
    iconBg: "bg-blue-500/20",
    shadow: "shadow-blue-500/10",
    confirmBtn:
      "from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 shadow-blue-500/20 hover:shadow-blue-500/30",
  },
  warning: {
    icon: "text-yellow-400",
    iconBg: "bg-yellow-500/20",
    shadow: "shadow-yellow-500/10",
    confirmBtn:
      "from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700 shadow-yellow-500/20 hover:shadow-yellow-500/30",
  },
  danger: {
    icon: "text-red-400",
    iconBg: "bg-red-500/20",
    shadow: "shadow-red-500/10",
    confirmBtn:
      "from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 shadow-red-500/20 hover:shadow-red-500/30",
  },
};
</script>

<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- 背景遮罩 -->
    <div
      class="absolute inset-0 bg-black/60 backdrop-blur-sm"
      @click="$emit('cancel')"
    ></div>

    <!-- 对话框 -->
    <div
      class="relative bg-gray-900/95 backdrop-blur-md border border-gray-700/50 rounded-2xl shadow-2xl p-6 w-full max-w-md mx-4 transform transition-all duration-300"
      :class="typeStyles[type].shadow"
    >
      <!-- 图标 -->
      <div class="flex items-center justify-center mb-4">
        <div
          class="w-16 h-16 rounded-full flex items-center justify-center"
          :class="typeStyles[type].iconBg"
        >
          <svg
            v-if="type === 'warning' || type === 'danger'"
            class="w-8 h-8"
            :class="typeStyles[type].icon"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <svg
            v-else
            class="w-8 h-8"
            :class="typeStyles[type].icon"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
      </div>

      <!-- 标题 -->
      <h3 class="text-xl font-semibold text-white text-center mb-2">
        {{ title }}
      </h3>

      <!-- 消息内容 -->
      <p class="text-gray-400 text-center mb-6 leading-relaxed">
        {{ message }}
      </p>

      <!-- 错误消息 -->
      <div
        v-if="errorMessage"
        class="mb-4 px-4 py-2 rounded-lg bg-red-500/20 border border-red-500/40 text-red-400 text-sm"
      >
        {{ errorMessage }}
      </div>

      <!-- 按钮组 -->
      <div class="flex gap-3">
        <button
          @click="$emit('cancel')"
          :disabled="loading"
          class="flex-1 py-2.5 px-4 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 font-medium transition-all border border-gray-700 hover:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ cancelText }}
        </button>
        <button
          @click="$emit('confirm')"
          :disabled="loading"
          class="flex-1 py-2.5 px-4 rounded-xl bg-linear-to-r text-white font-semibold transition-all shadow-lg transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
          :class="typeStyles[type].confirmBtn"
        >
          <svg
            v-if="loading"
            class="w-4 h-4 mr-2 animate-spin"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          {{ loading ? "处理中..." : confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>
