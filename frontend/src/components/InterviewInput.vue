<template>
  <div class="w-full">
    <div
      class="flex items-center gap-2 p-1.5 bg-gray-800/30 rounded-2xl border border-gray-700/50"
    >
      <!-- 功能按钮 -->
      <button
        class="p-2.5 rounded-xl bg-gray-800/70 hover:bg-gray-700/70 text-gray-400 hover:text-white transition-all duration-300 transform hover:scale-105"
        title="添加附件"
      >
        <svg
          class="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
      </button>
      <button
        class="p-2.5 rounded-xl bg-gray-800/70 hover:bg-gray-700/70 text-gray-400 hover:text-white transition-all duration-300 transform hover:scale-105"
        title="添加表情"
      >
        <svg
          class="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </button>
      <button
        class="p-2.5 rounded-xl bg-gray-800/70 hover:bg-gray-700/70 text-gray-400 hover:text-white transition-all duration-300 transform hover:scale-105"
        title="添加链接"
      >
        <svg
          class="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
          />
        </svg>
      </button>

      <!-- 主要输入区域 -->
      <div class="flex-1 relative">
        <input
          v-model="localInput"
          type="text"
          placeholder="输入你的回答..."
          class="w-full bg-transparent border-0 text-gray-300 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30 px-4 py-3 rounded-xl transition-all duration-300"
          @keyup.enter="handleSendMessage"
        />
        <!-- 作答倒计时 -->
        <div
          v-if="isRecording"
          class="absolute top-2 right-4 flex items-center gap-1.5 bg-orange-500/20 border border-orange-500/30 rounded-full px-2.5 py-0.5 backdrop-blur-sm"
        >
          <svg
            class="w-3.5 h-3.5 text-orange-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span class="text-orange-400 text-xs font-medium">
            {{ answerCountdown }}秒内作答
          </span>
        </div>
      </div>

      <!-- 中断录音按钮 -->
      <button
        v-if="isRecording"
        @click="handleCancelRecording"
        class="p-3 rounded-xl bg-gray-800/70 text-gray-400 hover:bg-red-500/20 hover:text-red-400 transition-all duration-300 transform hover:scale-105"
        title="中断录音"
      >
        <svg
          class="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>

      <!-- 录音按钮 -->
      <button
        @click="handleToggleRecording"
        :class="[
          'p-3 rounded-xl transition-all duration-300 relative transform hover:scale-105',
          isRecording
            ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
            : 'bg-gray-800/70 text-gray-400 hover:bg-gray-700/70 hover:text-white',
        ]"
        :title="isRecording ? '完成录音' : '开始录音'"
      >
        <svg
          v-if="!isRecording"
          class="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
          />
        </svg>
        <svg
          v-else
          class="w-5 h-5 animate-pulse"
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            fill-rule="evenodd"
            d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
            clip-rule="evenodd"
          />
        </svg>

        <!-- 录音时间显示 -->
        <div
          v-if="isRecording"
          class="absolute -top-1 -right-1 bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full font-mono shadow-lg"
        >
          {{ formatRecordingTime(recordingTime) }}
        </div>
      </button>

      <!-- 发送按钮 -->
      <button
        @click="handleSendMessage"
        :disabled="!localInput.trim() || isSubmitting || isRecording"
        :class="[
          'p-3 rounded-xl transition-all duration-300 transform hover:scale-105 relative overflow-hidden',
          !localInput.trim() || isSubmitting || isRecording
            ? 'bg-gray-700/50 text-gray-400 cursor-not-allowed'
            : 'bg-linear-to-r from-blue-500 to-purple-600 text-white hover:from-blue-600 hover:to-purple-700 shadow-lg hover:shadow-blue-500/20',
        ]"
      >
        <svg
          class="w-5 h-5 relative z-10"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
          />
        </svg>
        <!-- 发送按钮背景效果 -->
        <div
          v-if="localInput.trim() && !isSubmitting && !isRecording"
          class="absolute inset-0 bg-white/10 opacity-0 hover:opacity-100 transition-opacity duration-300"
        ></div>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

// Props
const props = defineProps({
  isRecording: {
    type: Boolean,
    default: false,
  },
  isSubmitting: {
    type: Boolean,
    default: false,
  },
  recordingTime: {
    type: Number,
    default: 0,
  },
  answerCountdown: {
    type: Number,
    default: 60,
  },
});

// Emits
const emit = defineEmits([
  "send-message",
  "start-recording",
  "stop-recording",
  "cancel-recording",
]);

// Local state
const localInput = ref("");

// Format recording time
const formatRecordingTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
};

// Handle send message
const handleSendMessage = () => {
  if (!localInput.value.trim() || props.isSubmitting || props.isRecording)
    return;
  emit("send-message", localInput.value.trim());
  localInput.value = "";
};

// Handle toggle recording
const handleToggleRecording = () => {
  if (props.isRecording) {
    emit("stop-recording");
  } else {
    emit("start-recording");
  }
};

// Handle cancel recording
const handleCancelRecording = () => {
  emit("cancel-recording");
};
</script>

<style scoped></style>
