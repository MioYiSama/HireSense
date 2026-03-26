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

type DimensionView = {
  name: string;
  score: number;
  summary: string;
  strengthPoints: string[];
  missingPoints: string[];
};

const normalizePoints = (points: unknown): string[] => {
  if (!Array.isArray(points)) return [];
  return points
    .map((item) => String(item ?? "").trim())
    .filter((item, index, array) => item.length > 0 && array.indexOf(item) === index)
    .slice(0, 3);
};

const buildDimensionViews = (
  scores?: Record<string, number>,
  details?: Record<
    string,
    {
      score?: number;
      summary?: string;
      strength_points?: string[];
      missing_points?: string[];
    }
  >,
): DimensionView[] => {
  const scoreEntries = Object.entries(scores ?? {});
  return scoreEntries.map(([name, rawScore]) => {
    const detail = details?.[name];
    const score = Number(detail?.score ?? rawScore);
    return {
      name,
      score: Number.isFinite(score) ? score : 0,
      summary: String(detail?.summary ?? "").trim(),
      strengthPoints: normalizePoints(detail?.strength_points),
      missingPoints: normalizePoints(detail?.missing_points),
    };
  });
};

const generalSkills = computed(() => {
  return buildDimensionViews(reportData.value?.general, reportData.value?.general_details);
});

const specificSkills = computed(() => {
  return buildDimensionViews(reportData.value?.specific, reportData.value?.specific_details);
});

const reportJobLabel = computed(() => {
  if (reportData.value?.job === "backend") return "后端开发工程师";
  if (reportData.value?.job === "frontend") return "前端开发工程师";
  return "技术岗位";
});

const interviewMode = computed(() => {
  return reportData.value?.mode ?? interviewData.value?.mode ?? "single";
});

const formatInterviewModeLabel = (mode?: string) => {
  return mode === "panel_trio" ? "群面模式" : "单面试官";
};

const getInterviewModeBadgeClass = (mode?: string) => {
  return mode === "panel_trio"
    ? "bg-fuchsia-500/20 text-fuchsia-300"
    : "bg-cyan-500/20 text-cyan-300";
};

const formatInterviewerRole = (role?: string) => {
  if (role === "hr") return "HR";
  if (role === "tech_lead") return "技术主管";
  if (role === "executive") return "大老板";
  return "AI 面试官";
};

const getInterviewerRoleBadgeClass = (role?: string) => {
  if (role === "hr") return "bg-emerald-500/10 text-emerald-300";
  if (role === "tech_lead") return "bg-cyan-500/10 text-cyan-300";
  if (role === "executive") return "bg-fuchsia-500/10 text-fuchsia-300";
  return "bg-blue-500/10 text-blue-300";
};

const formatDifficultyLabel = (difficulty?: string) => {
  if (difficulty === "basic") return "基础";
  if (difficulty === "intermediate") return "中等";
  if (difficulty === "advanced") return "高阶";
  return "未知难度";
};

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
              <div v-if="typeof reportData.score === 'number'" class="relative">
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
                  <span class="text-5xl font-bold text-white">{{
                    reportData.score.toFixed(2)
                  }}</span>
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
                  <span
                    class="px-3 py-1 rounded-full text-sm font-medium"
                    :class="getInterviewModeBadgeClass(interviewMode)"
                  >
                    {{ formatInterviewModeLabel(interviewMode) }}
                  </span>
                  <span v-if="interviewData.created_at" class="text-slate-400 text-sm">{{
                    formatDate(interviewData.created_at)
                  }}</span>
                </div>
                <h2 class="text-3xl font-bold text-white mb-3">{{ reportJobLabel }}面试报告</h2>
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
            <div class="mt-4 space-y-3">
              <div
                v-for="skill in generalSkills"
                :key="skill.name"
                class="rounded-2xl border border-white/6 bg-white/3 p-4"
              >
                <div class="flex items-center justify-between gap-4">
                  <h4 class="text-sm font-medium text-white">{{ skill.name }}</h4>
                  <span class="text-sm font-semibold text-cyan-300">{{ skill.score.toFixed(1) }}</span>
                </div>
                <p v-if="skill.summary" class="mt-2 text-sm leading-relaxed text-slate-400">
                  {{ skill.summary }}
                </p>
                <div v-if="skill.strengthPoints.length > 0" class="mt-3 flex flex-wrap gap-2">
                  <span
                    v-for="point in skill.strengthPoints"
                    :key="point"
                    class="rounded-full bg-cyan-500/10 px-3 py-1 text-xs text-cyan-300"
                  >
                    答到：{{ point }}
                  </span>
                </div>
                <div v-if="skill.missingPoints.length > 0" class="mt-2 flex flex-wrap gap-2">
                  <span
                    v-for="point in skill.missingPoints"
                    :key="point"
                    class="rounded-full bg-amber-500/10 px-3 py-1 text-xs text-amber-300"
                  >
                    待补：{{ point }}
                  </span>
                </div>
              </div>
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
            <div class="mt-4 space-y-3">
              <div
                v-for="skill in specificSkills"
                :key="skill.name"
                class="rounded-2xl border border-white/6 bg-white/3 p-4"
              >
                <div class="flex items-center justify-between gap-4">
                  <h4 class="text-sm font-medium text-white">{{ skill.name }}</h4>
                  <span class="text-sm font-semibold text-fuchsia-300">
                    {{ skill.score.toFixed(1) }}
                  </span>
                </div>
                <p v-if="skill.summary" class="mt-2 text-sm leading-relaxed text-slate-400">
                  {{ skill.summary }}
                </p>
                <div v-if="skill.strengthPoints.length > 0" class="mt-3 flex flex-wrap gap-2">
                  <span
                    v-for="point in skill.strengthPoints"
                    :key="point"
                    class="rounded-full bg-fuchsia-500/10 px-3 py-1 text-xs text-fuchsia-300"
                  >
                    答到：{{ point }}
                  </span>
                </div>
                <div v-if="skill.missingPoints.length > 0" class="mt-2 flex flex-wrap gap-2">
                  <span
                    v-for="point in skill.missingPoints"
                    :key="point"
                    class="rounded-full bg-amber-500/10 px-3 py-1 text-xs text-amber-300"
                  >
                    待补：{{ point }}
                  </span>
                </div>
              </div>
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
                    <div class="mt-3 flex flex-wrap gap-2">
                      <span
                        class="rounded-full px-3 py-1 text-xs"
                        :class="getInterviewerRoleBadgeClass(review.interviewer_role)"
                      >
                        {{ formatInterviewerRole(review.interviewer_role) }}
                      </span>
                      <span
                        v-if="review.concept"
                        class="rounded-full bg-blue-500/10 px-3 py-1 text-xs text-blue-300"
                      >
                        {{ review.concept }}
                      </span>
                      <span
                        class="rounded-full bg-white/5 px-3 py-1 text-xs text-slate-300"
                      >
                        {{ formatDifficultyLabel(review.difficulty_label) }}
                      </span>
                    </div>
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
                  </div>
                  <div
                    v-if="review.reason_tags && review.reason_tags.length > 0"
                    class="flex flex-wrap justify-end gap-2"
                  >
                    <span
                      v-for="tag in review.reason_tags"
                      :key="tag"
                      class="rounded-full bg-white/5 px-3 py-1 text-xs text-slate-300"
                    >
                      {{ tag }}
                    </span>
                  </div>
                </div>

                <div
                  v-if="review.score_breakdown"
                  class="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3"
                >
                  <div class="rounded-xl border border-cyan-500/10 bg-cyan-500/5 p-3">
                    <p class="text-xs text-cyan-300">主线覆盖</p>
                    <p class="mt-1 text-lg font-semibold text-white">
                      {{ Number(review.score_breakdown.coverage_score ?? 0).toFixed(1) }}
                    </p>
                  </div>
                  <div class="rounded-xl border border-blue-500/10 bg-blue-500/5 p-3">
                    <p class="text-xs text-blue-300">逻辑一致</p>
                    <p class="mt-1 text-lg font-semibold text-white">
                      {{ Number(review.score_breakdown.consistency_score ?? 0).toFixed(1) }}
                    </p>
                  </div>
                  <div class="rounded-xl border border-fuchsia-500/10 bg-fuchsia-500/5 p-3">
                    <p class="text-xs text-fuchsia-300">完整度</p>
                    <p class="mt-1 text-lg font-semibold text-white">
                      {{ Number(review.score_breakdown.completeness_score ?? 0).toFixed(1) }}
                    </p>
                  </div>
                </div>

                <div
                  v-if="
                    (review.strength_points && review.strength_points.length > 0) ||
                    (review.missing_points && review.missing_points.length > 0)
                  "
                  class="mb-4 grid grid-cols-1 gap-3 lg:grid-cols-2"
                >
                  <div
                    v-if="review.strength_points && review.strength_points.length > 0"
                    class="rounded-xl border border-emerald-500/15 bg-emerald-500/8 p-4"
                  >
                    <p class="mb-2 text-xs font-medium text-emerald-300">答到的点</p>
                    <div class="flex flex-wrap gap-2">
                      <span
                        v-for="point in review.strength_points"
                        :key="point"
                        class="rounded-full bg-emerald-500/10 px-3 py-1 text-xs text-emerald-200"
                      >
                        {{ point }}
                      </span>
                    </div>
                  </div>
                  <div
                    v-if="review.missing_points && review.missing_points.length > 0"
                    class="rounded-xl border border-amber-500/15 bg-amber-500/8 p-4"
                  >
                    <p class="mb-2 text-xs font-medium text-amber-300">缺失的点</p>
                    <div class="flex flex-wrap gap-2">
                      <span
                        v-for="point in review.missing_points"
                        :key="point"
                        class="rounded-full bg-amber-500/10 px-3 py-1 text-xs text-amber-200"
                      >
                        {{ point }}
                      </span>
                    </div>
                  </div>
                </div>

                <div
                  v-if="review.score_rationale"
                  class="mb-4 rounded-xl border border-white/6 bg-white/3 p-4"
                >
                  <p class="text-xs text-slate-400">分数解释</p>
                  <p class="mt-1 text-sm leading-relaxed text-slate-300">
                    {{ review.score_rationale }}
                  </p>
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
