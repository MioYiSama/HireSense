<style scoped>
@keyframes scoreReveal {
  from {
    stroke-dashoffset: 283;
  }
}

.score-animate {
  animation: scoreReveal 1.5s ease-out forwards;
}
</style>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getApiErrorMessage, useInterviewsQuery } from "@/lib/api";
import { getAccessToken } from "@/utils/token";

const route = useRoute();
const router = useRouter();

const interviewId = route.params["id"] as string;
const interviewsQuery = useInterviewsQuery();

const isLoading = computed(() => {
  return interviewsQuery.isPending.value || interviewsQuery.isFetching.value;
});

const interviewData = computed(() => {
  const interviews = interviewsQuery.data.value ?? [];
  return interviews.find((item) => item.id === interviewId) ?? null;
});

const reportData = computed(() => {
  return interviewData.value?.report ?? null;
});

const resourceUrlPattern = /(https?:\/\/[^\s]+)/i;

const parsedResources = computed(() => {
  return (reportData.value?.resources ?? []).map((resource) => {
    const raw = String(resource).trim();
    const matchedUrl = raw.match(resourceUrlPattern)?.[1] ?? "";
    const label = matchedUrl ? raw.replace(matchedUrl, "").trim() || matchedUrl : raw;

    return {
      label,
      raw,
      url: matchedUrl,
    };
  });
});

const errorMessage = computed(() => {
  if (!getAccessToken()) {
    return "请先登录";
  }

  if (interviewsQuery.error.value) {
    return getApiErrorMessage(interviewsQuery.error.value, "获取面试记录失败");
  }

  if (!isLoading.value && !reportData.value) {
    return "未找到面试报告";
  }

  return "";
});

const loadReport = async () => {
  await interviewsQuery.refetch();
};

const goBack = () => {
  router.push("/dashboard");
};

// 计算通用能力和专业能力数据
const generalSkills = computed(() => {
  if (!reportData.value || !reportData.value.general) return [];
  return Object.entries(reportData.value.general).map(([name, score]) => ({
    name,
    score: Number(score),
  }));
});

const specificSkills = computed(() => {
  if (!reportData.value || !reportData.value.specific) return [];
  return Object.entries(reportData.value.specific).map(([name, score]) => ({
    name,
    score: Number(score),
  }));
});

// 格式化日期
const formatDate = (timestamp: number) => {
  const date = new Date(timestamp);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day} ${hours}:${minutes}`;
};

// 生成雷达图多边形点
const generateRadarPolygon = (
  count: number,
  radius: number,
  skills?: Array<{ name: string; score: number }>,
) => {
  if (count === 0) return "";

  let points = "";
  for (let i = 0; i < count; i++) {
    const angle = i * ((2 * Math.PI) / count) - Math.PI / 2;
    const r =
      skills && skills[i] && typeof skills[i]!.score === "number"
        ? (skills[i]?.score ?? 0) * 10
        : radius;
    const x = Math.cos(angle) * r;
    const y = Math.sin(angle) * r;
    points += `${x},${y} `;
  }
  return points.trim();
};
</script>

<template>
  <div
    class="min-h-screen bg-linear-to-br from-gray-900 via-gray-800 to-gray-900 relative overflow-hidden"
  >
    <!-- 背景 -->
    <div class="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl"></div>
    <div class="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl"></div>
    <div class="absolute top-1/2 right-1/3 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl"></div>

    <!-- 导航栏 -->
    <div
      class="navbar bg-gray-900/60 backdrop-blur-md border-b border-gray-700/50 shadow-lg relative z-10"
    >
      <div class="flex-1">
        <button
          @click="goBack"
          class="flex items-center gap-3 transition-all duration-300 hover:scale-105 hover:opacity-90 cursor-pointer"
        >
          <div class="flex items-center gap-2">
            <img src="/favicon.png" alt="HireSense" class="h-8 w-8 rounded-md object-contain" />
            <span class="text-xl font-bold text-white tracking-tight">Hire Sense</span>
          </div>
        </button>
      </div>
      <div class="flex-none">
        <button
          @click="goBack"
          class="flex items-center gap-2 px-4 py-2 rounded-xl bg-linear-to-r from-blue-600/20 to-purple-600/20 hover:from-blue-600/30 hover:to-purple-600/30 border border-blue-500/30 transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/10 cursor-pointer"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M10 19l-7-7m0 0l7-7m-7 7h18"
            />
          </svg>
          <span class="text-sm text-gray-300">返回面试中心</span>
        </button>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="container mx-auto px-4 py-8">
      <!-- 加载状态 -->
      <div v-if="isLoading" class="flex justify-center items-center py-20">
        <div class="flex flex-col items-center">
          <svg
            class="w-12 h-12 text-blue-400 animate-spin"
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
          <span class="text-lg text-gray-400 mt-4">加载中...</span>
        </div>
      </div>

      <!-- 错误信息 -->
      <div
        v-else-if="errorMessage"
        class="max-w-2xl mx-auto p-6 rounded-xl bg-red-500/20 border border-red-500/40 text-red-400"
      >
        <div class="flex items-center gap-3">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
            />
          </svg>
          <span class="text-lg">{{ errorMessage }}</span>
        </div>
        <button
          @click="loadReport"
          class="mt-4 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
        >
          重试
        </button>
      </div>

      <!-- 报告内容 -->
      <main v-else-if="reportData" class="max-w-7xl mx-auto pt-6 pb-12 px-6 relative space-y-6">
        <!-- 报告头部 -->
        <section class="mb-8 animate-slide-up">
          <div
            class="bg-gray-900/60 backdrop-blur-md border border-gray-700/50 rounded-3xl p-8 shadow-lg relative overflow-hidden"
          >
            <div
              class="absolute top-0 right-0 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl"
            ></div>
            <div class="relative flex flex-col lg:flex-row items-center gap-8">
              <!-- 分数展示 -->
              <div v-if="reportData.score" class="relative">
                <svg class="w-44 h-44 progress-ring" viewBox="0 0 100 100">
                  <circle
                    cx="50"
                    cy="50"
                    r="45"
                    fill="none"
                    stroke="rgba(255,255,255,0.05)"
                    stroke-width="6"
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="45"
                    fill="none"
                    stroke="url(#scoreGrad)"
                    stroke-width="6"
                    stroke-linecap="round"
                    :stroke-dasharray="283"
                    :stroke-dashoffset="283 - (283 * reportData.score) / 100"
                    class="score-animate"
                    transform="rotate(-90 50 50)"
                  />
                  <defs>
                    <linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stop-color="#06b6d4" />
                      <stop offset="100%" stop-color="#22d3ee" />
                    </linearGradient>
                  </defs>
                </svg>
                <div class="absolute inset-0 flex flex-col items-center justify-center">
                  <span class="text-5xl font-bold text-white">{{ reportData.score }}</span>
                  <span class="text-sm text-slate-400 mt-1">综合评分</span>
                </div>
              </div>
              <!-- 基本信息 -->
              <div class="flex-1 text-center lg:text-left">
                <div class="flex items-center justify-center lg:justify-start gap-3 mb-4">
                  <span
                    class="px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-sm font-medium flex items-center gap-1"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                      /></svg
                    >已完成
                  </span>
                  <span v-if="interviewData.created_at" class="text-slate-400 text-sm">{{
                    formatDate(interviewData.created_at)
                  }}</span>
                </div>
                <h2 class="text-3xl font-bold text-white mb-3">前端开发工程师面试报告</h2>
                <p v-if="reportData.feedback" class="text-slate-400 max-w-2xl">
                  {{ reportData.feedback }}
                </p>
              </div>
            </div>
          </div>
        </section>

        <!-- 双雷达图区域 -->
        <section class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <!-- 通用能力 -->
          <div
            v-if="generalSkills.length > 0"
            class="bg-gray-900/60 backdrop-blur-md border border-gray-700/50 rounded-2xl p-6 shadow-lg hover:shadow-xl transition-shadow animate-slide-up"
            style="animation-delay: 0.1s"
          >
            <h3 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5 text-blue-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                /></svg
              >通用能力评估
            </h3>
            <div class="flex justify-center">
              <svg width="280" height="260" viewBox="0 0 280 260">
                <g transform="translate(140, 130)">
                  <!-- 网格 -->
                  <template v-for="(_, index) in 3" :key="index">
                    <polygon
                      :points="generateRadarPolygon(generalSkills.length, 100 - index * 25)"
                      fill="none"
                      stroke="rgba(255,255,255,0.05)"
                    />
                  </template>
                  <!-- 轴线 -->
                  <template v-for="(_, index) in generalSkills" :key="index">
                    <line
                      x1="0"
                      y1="0"
                      :x2="
                        Math.cos(index * ((2 * Math.PI) / generalSkills.length) - Math.PI / 2) * 100
                      "
                      :y2="
                        Math.sin(index * ((2 * Math.PI) / generalSkills.length) - Math.PI / 2) * 100
                      "
                      stroke="rgba(255,255,255,0.08)"
                    />
                  </template>
                  <!-- 数据路径 -->
                  <polygon
                    :points="generateRadarPolygon(generalSkills.length, 0, generalSkills)"
                    fill="rgba(6,182,212,0.2)"
                    stroke="#06b6d4"
                    stroke-width="2"
                  />
                  <!-- 数据点 -->
                  <template v-for="(skill, index) in generalSkills" :key="index">
                    <circle
                      :cx="
                        Math.cos(index * ((2 * Math.PI) / generalSkills.length) - Math.PI / 2) *
                        (skill.score * 10)
                      "
                      :cy="
                        Math.sin(index * ((2 * Math.PI) / generalSkills.length) - Math.PI / 2) *
                        (skill.score * 10)
                      "
                      r="4"
                      fill="#06b6d4"
                    />
                  </template>
                </g>
                <!-- 技能标签 -->
                <template v-for="(skill, index) in generalSkills" :key="index">
                  <text
                    :x="
                      140 +
                      Math.cos(index * ((2 * Math.PI) / generalSkills.length) - Math.PI / 2) * 90
                    "
                    :y="
                      130 +
                      Math.sin(index * ((2 * Math.PI) / generalSkills.length) - Math.PI / 2) * 90
                    "
                    :text-anchor="
                      Math.cos(index * ((2 * Math.PI) / generalSkills.length) - Math.PI / 2) > 0
                        ? 'start'
                        : 'end'
                    "
                    :dominant-baseline="
                      Math.sin(index * ((2 * Math.PI) / generalSkills.length) - Math.PI / 2) > 0
                        ? 'text-before-edge'
                        : 'text-after-edge'
                    "
                    fill="#94a3b8"
                    font-size="11"
                  >
                    {{ skill.name }} {{ skill.score.toFixed(1) }}
                  </text>
                </template>
              </svg>
            </div>
          </div>

          <!-- 专业能力 -->
          <div
            v-if="specificSkills.length > 0"
            class="bg-gray-900/60 backdrop-blur-md border border-gray-700/50 rounded-2xl p-6 shadow-lg hover:shadow-xl transition-shadow animate-slide-up"
            style="animation-delay: 0.2s"
          >
            <h3 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5 text-purple-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
                /></svg
              >专业能力评估
            </h3>
            <div class="flex justify-center">
              <svg width="280" height="260" viewBox="0 0 280 260">
                <g transform="translate(140, 130)">
                  <!-- 网格 -->
                  <template v-for="(_, index) in 3" :key="index">
                    <polygon
                      :points="generateRadarPolygon(specificSkills.length, 100 - index * 25)"
                      fill="none"
                      stroke="rgba(255,255,255,0.05)"
                    />
                  </template>
                  <!-- 轴线 -->
                  <template v-for="(_, index) in specificSkills" :key="index">
                    <line
                      x1="0"
                      y1="0"
                      :x2="
                        Math.cos(index * ((2 * Math.PI) / specificSkills.length) - Math.PI / 2) *
                        100
                      "
                      :y2="
                        Math.sin(index * ((2 * Math.PI) / specificSkills.length) - Math.PI / 2) *
                        100
                      "
                      stroke="rgba(255,255,255,0.08)"
                    />
                  </template>
                  <!-- 数据路径 -->
                  <polygon
                    :points="generateRadarPolygon(specificSkills.length, 0, specificSkills)"
                    fill="rgba(168,85,247,0.2)"
                    stroke="#a855f7"
                    stroke-width="2"
                  />
                  <!-- 数据点 -->
                  <template v-for="(skill, index) in specificSkills" :key="index">
                    <circle
                      :cx="
                        Math.cos(index * ((2 * Math.PI) / specificSkills.length) - Math.PI / 2) *
                        (skill.score * 10)
                      "
                      :cy="
                        Math.sin(index * ((2 * Math.PI) / specificSkills.length) - Math.PI / 2) *
                        (skill.score * 10)
                      "
                      r="4"
                      fill="#a855f7"
                    />
                  </template>
                </g>
                <!-- 技能标签 -->
                <template v-for="(skill, index) in specificSkills" :key="index">
                  <text
                    :x="
                      140 +
                      Math.cos(index * ((2 * Math.PI) / specificSkills.length) - Math.PI / 2) * 90
                    "
                    :y="
                      130 +
                      Math.sin(index * ((2 * Math.PI) / specificSkills.length) - Math.PI / 2) * 90
                    "
                    :text-anchor="
                      Math.cos(index * ((2 * Math.PI) / specificSkills.length) - Math.PI / 2) > 0
                        ? 'start'
                        : 'end'
                    "
                    :dominant-baseline="
                      Math.sin(index * ((2 * Math.PI) / specificSkills.length) - Math.PI / 2) > 0
                        ? 'text-before-edge'
                        : 'text-after-edge'
                    "
                    fill="#94a3b8"
                    font-size="11"
                  >
                    {{ skill.name }} {{ skill.score.toFixed(1) }}
                  </text>
                </template>
              </svg>
            </div>
          </div>
        </section>

        <!-- 复盘结果列表 -->
        <section
          v-if="reportData.reviews && reportData.reviews.length > 0"
          class="mb-8 animate-slide-up"
          style="animation-delay: 0.2s"
        >
          <div
            class="bg-gray-900/60 backdrop-blur-md border border-gray-700/50 rounded-2xl p-6 shadow-lg"
          >
            <h3 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5 text-blue-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                /></svg
              >面试复盘详情
            </h3>
            <div class="space-y-6">
              <div
                v-for="(review, index) in reportData.reviews"
                :key="index"
                class="bg-gray-800/30 border border-gray-700/30 rounded-2xl p-5 hover:border-blue-500/30 transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/5"
              >
                <div class="flex items-start gap-4 mb-4">
                  <div
                    class="w-10 h-10 rounded-full bg-linear-to-br from-blue-400 to-blue-600 flex items-center justify-center shrink-0"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-5 w-5 text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                      />
                    </svg>
                  </div>
                  <div class="flex-1">
                    <p class="text-xs text-slate-400 mb-1">面试官提问</p>
                    <p class="text-white">{{ review.interviewer }}</p>
                  </div>
                </div>

                <div class="flex items-start gap-4 mb-4 ml-12">
                  <div
                    class="w-10 h-10 rounded-full bg-linear-to-br from-blue-400 to-blue-600 flex items-center justify-center shrink-0"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-5 w-5 text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                      />
                    </svg>
                  </div>
                  <div class="flex-1">
                    <p class="text-xs text-slate-400 mb-1">你的回答</p>
                    <p class="text-slate-300">{{ review.interviewee }}</p>
                  </div>
                </div>

                <div class="flex items-center justify-between pt-4 border-t border-white/5 mb-4">
                  <div class="flex items-center gap-4">
                    <div class="flex items-center gap-2">
                      <span class="text-xs text-slate-400">得分</span>
                      <span class="text-lg font-bold text-yellow-400">{{ review.score }}</span>
                    </div>
                    <div class="h-4 w-px bg-white/10"></div>
                    <div class="flex items-center gap-1">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-4 w-4 text-yellow-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
                        />
                      </svg>
                      <span class="text-xs text-slate-400">待提升</span>
                    </div>
                  </div>
                </div>

                <div class="mt-4 p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
                  <p class="text-xs text-yellow-400 mb-1 font-medium">改进建议</p>
                  <p class="text-sm text-slate-300">{{ review.advice }}</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 不足与建议 -->
        <section
          class="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-slide-up"
          style="animation-delay: 0.25s"
        >
          <!-- 待改进项 -->
          <div
            v-if="reportData.shortcomings && reportData.shortcomings.length > 0"
            class="bg-gray-900/60 backdrop-blur-md border border-gray-700/50 rounded-2xl p-6 shadow-lg hover:shadow-xl transition-shadow"
          >
            <h3 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5 text-yellow-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
                /></svg
              >待改进项
            </h3>
            <ul class="space-y-3">
              <li
                v-for="(item, index) in reportData.shortcomings"
                :key="index"
                class="flex items-start gap-3 p-3 rounded-xl bg-yellow-500/10"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-5 w-5 text-yellow-400 mt-0.5 shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span class="text-sm text-slate-300">{{ item }}</span>
              </li>
            </ul>
          </div>

          <!-- 改进建议 -->
          <div
            v-if="reportData.advice"
            class="bg-gray-900/60 backdrop-blur-md border border-gray-700/50 rounded-2xl p-6 shadow-lg hover:shadow-xl transition-shadow"
          >
            <h3 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5 text-blue-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                /></svg
              >改进建议
            </h3>
            <p class="text-sm text-slate-300 leading-relaxed">
              {{ reportData.advice }}
            </p>
          </div>

          <!-- 推荐资源 -->
          <div
            v-if="parsedResources.length > 0"
            class="bg-gray-900/60 backdrop-blur-md border border-gray-700/50 rounded-2xl p-6 shadow-lg hover:shadow-xl transition-shadow"
          >
            <h3 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5 text-green-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                /></svg
              >推荐资源
            </h3>
            <ul class="space-y-2">
              <li
                v-for="(resource, index) in parsedResources"
                :key="index"
                class="flex items-start gap-2 text-wrap break-all text-sm text-slate-300"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-3 w-3 text-slate-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
                <a
                  v-if="resource.url"
                  :href="resource.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-slate-300 hover:text-blue-400 transition-colors"
                >
                  {{ resource.label }}
                </a>
                <span v-else>{{ resource.raw }}</span>
              </li>
            </ul>
          </div>
        </section>
      </main>

      <!-- 空状态 -->
      <div v-else class="flex justify-center items-center py-20">
        <div class="text-center">
          <svg
            class="w-16 h-16 text-gray-600 mx-auto mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.5"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <h3 class="text-xl font-semibold text-gray-400 mb-2">暂无报告数据</h3>
          <p class="text-gray-500">报告可能正在生成中，请稍后再试</p>
        </div>
      </div>
    </div>
  </div>
</template>
