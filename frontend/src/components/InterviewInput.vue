<template>
  <div class="w-full">
    <div class="flex items-center gap-2 rounded-2xl border border-gray-700/50 bg-gray-800/30 p-1.5">
      <!-- 中断录音按钮 -->
      <button
        v-if="isRecording"
        @click="handleCancelRecording"
        class="transform rounded-xl bg-gray-800/70 p-3 text-gray-400 transition-all duration-300 hover:scale-105 hover:bg-red-500/20 hover:text-red-400"
        title="中断录音"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
        :disabled="isSubmitting || isInterviewEnded"
        :class="[
          'relative transform rounded-xl p-3 transition-all duration-300 hover:scale-105',
          isRecording
            ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
            : 'bg-gray-800/70 text-gray-400 hover:bg-gray-700/70 hover:text-white disabled:cursor-not-allowed disabled:bg-gray-700/50 disabled:text-gray-500 disabled:hover:scale-100',
        ]"
        :title="isRecording ? '完成录音' : '开始录音'"
      >
        <svg
          v-if="!isRecording"
          class="h-5 w-5"
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
        <svg v-else class="h-5 w-5 animate-pulse" fill="currentColor" viewBox="0 0 24 24">
          <path fill-rule="evenodd" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" clip-rule="evenodd" />
        </svg>

        <!-- 录音时间显示 -->
        <div
          v-if="isRecording"
          class="absolute -top-1 -right-1 rounded-full bg-red-500 px-1.5 py-0.5 font-mono text-xs text-white shadow-lg"
        >
          {{ formatRecordingTime(recordingTime) }}
        </div>
      </button>

      <!-- 作答倒计时 -->
      <p
        v-if="isRecording"
        class="relative flex-1 gap-1.5 rounded-xl border border-orange-500/30 bg-orange-500/20 px-2.5 py-2 text-center text-orange-300 backdrop-blur-sm"
        :class="{ hidden: !isRecording }"
      >
        {{ answerCountdown }}秒内作答
      </p>

      <!-- 主要输入区域 -->
      <div class="relative flex-1" :class="{ hidden: isRecording }">
        <input
          v-model="localInput"
          type="text"
          :disabled="isSubmitting || isInterviewEnded"
          :placeholder="isInterviewEnded ? '面试已结束' : '输入你的回答...'"
          class="w-full rounded-xl border-0 bg-transparent px-4 py-3 text-gray-300 placeholder-gray-500 transition-all duration-300 focus:ring-2 focus:ring-blue-500/30 focus:outline-none"
          @keyup.enter="handleSendMessage"
        />
      </div>

      <button
        @click="handleOpenCodeEditor"
        :disabled="isSubmitting || isRecording || isInterviewEnded"
        :class="[
          'transform rounded-xl p-3 text-gray-300 transition-all duration-300 hover:scale-105',
          isRecording ? 'hidden' : '',
          isSubmitting || isInterviewEnded
            ? 'cursor-not-allowed bg-gray-700/50 text-gray-500 hover:scale-100'
            : 'bg-gray-800/70 hover:bg-gray-700/70 hover:text-white',
        ]"
        title="打开代码编辑器"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 48 48">
          <path
            fill="none"
            stroke="currentColor"
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M17.592 37.092L4.5 24l13.092-13.092m2.824 26.202l7.218-26.219m2.774.017L43.5 24L30.408 37.092"
            stroke-width="4"
          />
        </svg>
      </button>

      <!-- 发送按钮 -->
      <button
        @click="handleSendMessage"
        :disabled="!localInput.trim() || isSubmitting || isRecording || isInterviewEnded"
        :class="[
          'relative transform overflow-hidden rounded-xl p-3 transition-all duration-300 hover:scale-105',
          !localInput.trim() || isSubmitting || isRecording || isInterviewEnded
            ? 'cursor-not-allowed bg-gray-700/50 text-gray-400'
            : 'bg-linear-to-r from-blue-500 to-purple-600 text-white shadow-lg hover:from-blue-600 hover:to-purple-700 hover:shadow-blue-500/20',
          isRecording ? 'hidden' : '',
        ]"
      >
        <svg class="relative z-10 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
          class="absolute inset-0 bg-white/10 opacity-0 transition-opacity duration-300 hover:opacity-100"
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
  isInterviewEnded: {
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
  "open-code-editor",
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
  if (
    !localInput.value.trim() ||
    props.isSubmitting ||
    props.isRecording ||
    props.isInterviewEnded
  ) {
    return;
  }

  emit("send-message", localInput.value.trim());
  localInput.value = "";
};

// Handle toggle recording
const handleToggleRecording = () => {
  if (props.isSubmitting || props.isInterviewEnded) {
    return;
  }

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

const handleOpenCodeEditor = () => {
  if (props.isSubmitting || props.isRecording || props.isInterviewEnded) {
    return;
  }

  emit("open-code-editor");
};
</script>

<style scoped></style>
