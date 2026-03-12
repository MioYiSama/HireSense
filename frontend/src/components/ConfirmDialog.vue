<script setup lang="ts">
interface Props {
  show?: boolean;
  title?: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
}

const props = withDefaults(defineProps<Props>(), {
  show: false,
  title: "确认",
  message: "确定要执行此操作吗？",
  confirmText: "确定",
  cancelText: "取消",
});

const emit = defineEmits<{
  confirm: [];
  cancel: [];
}>();
</script>

<template>
  <div
    v-if="show"
    class="fixed inset-0 z-50 flex items-center justify-center"
  >
    <!-- 背景遮罩 -->
    <div
      class="absolute inset-0 bg-black/50 backdrop-blur-sm"
      @click="$emit('cancel')"
    ></div>
    
    <!-- 对话框 -->
    <div
      class="relative bg-gray-900/95 backdrop-blur-md border border-gray-700/50 rounded-2xl shadow-2xl shadow-blue-500/10 p-6 w-full max-w-md mx-4 transform transition-all duration-300"
    >
      <!-- 标题 -->
      <h3 class="text-xl font-semibold text-white mb-4">
        {{ title }}
      </h3>
      
      <!-- 消息内容 -->
      <p class="text-gray-300 mb-6 leading-relaxed">
        {{ message }}
      </p>
      
      <!-- 按钮组 -->
      <div class="flex gap-3 justify-end">
        <button
          @click="$emit('cancel')"
          class="px-6 py-2.5 rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-800/50 hover:border-gray-500 transition-all duration-300"
        >
          {{ cancelText }}
        </button>
        <button
          @click="$emit('confirm')"
          class="px-6 py-2.5 rounded-lg bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white border-none shadow-lg shadow-blue-500/20 transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/30 transform hover:-translate-y-0.5"
        >
          {{ confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>
