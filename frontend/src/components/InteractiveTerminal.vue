<script setup lang="ts">
import { ref } from "vue";

// 互动终端状态管理
const terminalState = ref("start"); // start, question, analysis
const scores = ref({
  tech: 0,
  comm: 0,
  biz: 0,
});
const aiFeedback = ref("分析中...");

// 互动终端事件处理
const startSimulation = () => {
  terminalState.value = "question";
};

const selectOption = (option: string) => {
  terminalState.value = "analysis";

  // 模拟评分动画
  let techScore = 0;
  let commScore = 0;
  let bizScore = 0;

  // 根据选择的选项设置不同的分数
  if (option === "1") {
    techScore = 85;
    commScore = 70;
    bizScore = 65;
  } else if (option === "2") {
    techScore = 70;
    commScore = 85;
    bizScore = 75;
  } else if (option === "3") {
    techScore = 65;
    commScore = 75;
    bizScore = 85;
  }

  // 动画效果
  const techInterval = setInterval(() => {
    if (scores.value.tech < techScore) {
      scores.value.tech += 1;
    } else {
      clearInterval(techInterval);
    }
  }, 20);

  const commInterval = setInterval(() => {
    if (scores.value.comm < commScore) {
      scores.value.comm += 1;
    } else {
      clearInterval(commInterval);
    }
  }, 25);

  const bizInterval = setInterval(() => {
    if (scores.value.biz < bizScore) {
      scores.value.biz += 1;
    } else {
      clearInterval(bizInterval);
    }
  }, 30);

  // 模拟AI评价
  setTimeout(() => {
    if (option === "1") {
      aiFeedback.value =
        "你的技术深度表现出色，特别是在解决复杂技术问题方面。建议加强沟通表达能力，以便更好地向团队展示你的技术方案。";
    } else if (option === "2") {
      aiFeedback.value =
        "你的沟通表达能力很强，能够有效地与团队协作。建议进一步提升技术深度，特别是在性能优化方面。";
    } else if (option === "3") {
      aiFeedback.value =
        "你的业务思维非常出色，能够从商业角度思考问题。建议加强技术基础，以便更好地实现你的业务想法。";
    }
  }, 2000);
};

const restartSimulation = () => {
  terminalState.value = "start";
  scores.value = {
    tech: 0,
    comm: 0,
    biz: 0,
  };
  aiFeedback.value = "分析中...";
};
</script>

<template>
  <div class="relative w-full max-w-md float-animation">
    <!-- 终端外框 -->
    <div
      class="border-gradient p-1 rounded-3xl bg-gray-900/80 backdrop-blur-xl shadow-2xl"
    >
      <!-- 顶部栏 -->
      <div
        class="flex items-center gap-2 px-4 py-3 border-b border-gray-700/50"
      >
        <div class="w-3 h-3 rounded-full bg-red-500/80"></div>
        <div class="w-3 h-3 rounded-full bg-yellow-500/80"></div>
        <div class="w-3 h-3 rounded-full bg-green-500/80"></div>
        <span class="ml-4 text-xs text-gray-500"
          >AI Interview Simulator</span
        >
      </div>
      <!-- 内容区 -->
      <div class="p-6 min-h-[300px] flex flex-col">
        <!-- 初始状态：开始按钮 -->
        <div
          v-if="terminalState === 'start'"
          class="flex-1 flex flex-col items-center justify-center text-center"
        >
          <div
            class="w-16 h-16 rounded-2xl bg-linear-to-br from-blue-500 to-purple-500 flex items-center justify-center mb-4 animate-pulse"
          >
            <svg
              class="w-8 h-8 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
          </div>
          <h3 class="text-lg font-semibold text-white mb-2">
            准备好开始模拟面试了吗？
          </h3>
          <p class="text-sm text-gray-400 mb-6">
            体验真实的 AI 面试官互动
          </p>
          <button
            @click="startSimulation"
            class="px-6 py-2 bg-blue-500 text-white text-sm font-medium rounded-lg hover:bg-blue-600 transition-colors cursor-pointer"
          >
            开始体验
          </button>
        </div>

        <!-- 状态 1：提问 -->
        <div
          v-if="terminalState === 'question'"
          class="flex-1 flex flex-col"
        >
          <div class="flex items-start gap-3 mb-6">
            <div
              class="w-8 h-8 rounded-lg bg-linear-to-br from-blue-500 to-purple-500 flex items-center justify-center shrink-0"
            >
              <svg
                class="w-4 h-4 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                />
              </svg>
            </div>
            <div class="glass rounded-xl rounded-tl-none p-3">
              <p class="text-sm text-gray-300">
                请描述一下你在项目中遇到的最大技术挑战是什么？你是如何解决的？
              </p>
            </div>
          </div>
          <p class="text-xs text-gray-500 mb-3">
            请选择你的回答方向：
          </p>
          <div class="space-y-2 flex-1">
            <button
              @click="selectOption('1')"
              class="w-full text-left p-3 rounded-lg text-sm text-gray-300 border border-gray-700/50 hover:border-blue-500/50 hover:bg-blue-500/10 transition-colors cursor-pointer"
            >
              A. 侧重技术难点攻克（高并发/性能优化）
            </button>
            <button
              @click="selectOption('2')"
              class="w-full text-left p-3 rounded-lg text-sm text-gray-300 border border-gray-700/50 hover:border-blue-500/50 hover:bg-blue-500/10 transition-colors cursor-pointer"
            >
              B. 侧重团队协作与沟通（跨部门/需求变更）
            </button>
            <button
              @click="selectOption('3')"
              class="w-full text-left p-3 rounded-lg text-sm text-gray-300 border border-gray-700/50 hover:border-blue-500/50 hover:bg-blue-500/10 transition-colors cursor-pointer"
            >
              C. 侧重业务理解与创新（商业模式/增长)
            </button>
          </div>
        </div>

        <!-- 状态 2：分析结果 -->
        <div v-if="terminalState === 'analysis'" class="flex-1">
          <div class="flex items-center gap-2 text-blue-400 mb-4">
            <svg
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
              />
            </svg>
            <span class="text-sm font-medium">实时能力分析</span>
          </div>
          <div class="space-y-4">
            <div>
              <div class="flex justify-between text-xs mb-1">
                <span class="text-gray-400">技术深度</span>
                <span class="text-white">{{ scores.tech }}</span>
              </div>
              <div
                class="h-2 bg-gray-700/50 rounded-full overflow-hidden"
              >
                <div
                  class="h-full bg-linear-to-r from-blue-400 to-blue-600 rounded-full transition-all duration-1000 ease-out"
                  :style="{ width: scores.tech + '%' }"
                ></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between text-xs mb-1">
                <span class="text-gray-400">沟通表达</span>
                <span class="text-white">{{ scores.comm }}</span>
              </div>
              <div
                class="h-2 bg-gray-700/50 rounded-full overflow-hidden"
              >
                <div
                  class="h-full bg-linear-to-r from-purple-400 to-pink-500 rounded-full transition-all duration-1000 ease-out"
                  :style="{ width: scores.comm + '%' }"
                ></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between text-xs mb-1">
                <span class="text-gray-400">业务思维</span>
                <span class="text-white">{{ scores.biz }}</span>
              </div>
              <div
                class="h-2 bg-gray-700/50 rounded-full overflow-hidden"
              >
                <div
                  class="h-full bg-linear-to-r from-green-400 to-emerald-500 rounded-full transition-all duration-1000 ease-out"
                  :style="{ width: scores.biz + '%' }"
                ></div>
              </div>
            </div>
          </div>
          <div class="mt-6 p-3 rounded-lg glass">
            <p class="text-xs text-gray-400 mb-1">AI 评价</p>
            <p class="text-sm text-gray-300">{{ aiFeedback }}</p>
          </div>
          <button
            @click="restartSimulation"
            class="mt-4 w-full py-2 border border-gray-700/50 rounded-lg text-sm text-gray-400 hover:bg-gray-700/30 transition-colors cursor-pointer"
          >
            重新开始
          </button>
        </div>
      </div>
    </div>
  </div>
</template>