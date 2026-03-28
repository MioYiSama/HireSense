<script setup lang="ts">
import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";

import type { FavoriteQuestion, FavoriteQuestionSource } from "@/api";
import {
  getApiErrorMessage,
  queryKeys,
  removeFavoriteQuestion,
  useFavoriteQuestionsQuery,
} from "@/lib/api";
import { getUserInfo } from "@/utils/token";

const router = useRouter();
const queryClient = useQueryClient();
const storedUserInfo = getUserInfo();
const userName = computed(() => storedUserInfo?.name || "候选人");

const favoritesQuery = useFavoriteQuestionsQuery();
const selectedSourceKeys = ref<Record<string, string>>({});
const statusMessage = ref("");
const statusSuccess = ref(false);
const removingFavoriteID = ref<string | null>(null);
let statusTimeout: number | null = null;

const favorites = computed(() => favoritesQuery.data.value ?? []);
const isLoading = computed(() => favoritesQuery.isPending.value && favorites.value.length === 0);
const errorMessage = computed(() => {
  if (!favoritesQuery.error.value) {
    return "";
  }
  return getApiErrorMessage(favoritesQuery.error.value, "读取收藏题失败");
});
const latestUpdatedAt = computed(() => {
  return favorites.value[0]?.updated_at ?? "";
});

const showStatus = (message: string, success: boolean) => {
  if (statusTimeout) {
    clearTimeout(statusTimeout);
  }
  statusMessage.value = message;
  statusSuccess.value = success;
  statusTimeout = window.setTimeout(() => {
    statusMessage.value = "";
    statusTimeout = null;
  }, 3000);
};

const buildSourceKey = (source: FavoriteQuestionSource) => {
  return `${source.interview_id}:${source.review_index}`;
};

watch(
  favorites,
  (items) => {
    const nextSelection: Record<string, string> = { ...selectedSourceKeys.value };
    const validFavoriteIDs = new Set(items.map((item) => item.id));

    items.forEach((favorite) => {
      const selectedKey = nextSelection[favorite.id];
      const hasSelectedSource = favorite.sources.some(
        (source) => buildSourceKey(source) === selectedKey,
      );
      if (!hasSelectedSource && favorite.sources[0]) {
        nextSelection[favorite.id] = buildSourceKey(favorite.sources[0]);
      }
    });

    Object.keys(nextSelection).forEach((favoriteID) => {
      if (!validFavoriteIDs.has(favoriteID)) {
        delete nextSelection[favoriteID];
      }
    });

    selectedSourceKeys.value = nextSelection;
  },
  { immediate: true },
);

const getSelectedSource = (favorite: FavoriteQuestion) => {
  const selectedKey = selectedSourceKeys.value[favorite.id];
  return (
    favorite.sources.find((source) => buildSourceKey(source) === selectedKey) ?? favorite.sources[0]
  );
};

const getSelectedSources = (favorite: FavoriteQuestion) => {
  const selectedSource = getSelectedSource(favorite);
  return selectedSource ? [selectedSource] : [];
};

const selectSource = (favoriteID: string, source: FavoriteQuestionSource) => {
  selectedSourceKeys.value = {
    ...selectedSourceKeys.value,
    [favoriteID]: buildSourceKey(source),
  };
};

const isSelectedSource = (favorite: FavoriteQuestion, source: FavoriteQuestionSource) => {
  const selectedSource = getSelectedSource(favorite);
  if (!selectedSource) {
    return false;
  }
  return buildSourceKey(source) === buildSourceKey(selectedSource);
};

const removeFavoriteMutation = useMutation({
  mutationFn: removeFavoriteQuestion,
  onMutate: (favoriteID) => {
    removingFavoriteID.value = favoriteID;
  },
  onSuccess: async () => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.favoriteQuestions() });
    showStatus("收藏题已移除", true);
  },
  onError: (error) => {
    showStatus(getApiErrorMessage(error, "移除收藏题失败"), false);
  },
  onSettled: () => {
    removingFavoriteID.value = null;
  },
});

const handleRemoveFavorite = (favoriteID: string) => {
  if (removingFavoriteID.value === favoriteID) {
    return;
  }
  removeFavoriteMutation.mutate(favoriteID);
};

const goToDashboard = () => {
  router.push("/dashboard");
};

const openSourceReport = (source: FavoriteQuestionSource) => {
  router.push(`/interview/${source.interview_id}/report`);
};

const formatDateTime = (value?: string) => {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "--";
  }
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
};

const formatTimestamp = (value?: number) => {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "--";
  }
  return `${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
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
  return difficulty?.trim() || "未知难度";
};
</script>

<template>
  <div
    class="min-h-screen bg-linear-to-br from-gray-950 via-gray-900 to-gray-950 relative overflow-hidden"
  >
    <div class="absolute top-0 left-1/4 h-96 w-96 rounded-full bg-amber-400/10 blur-3xl"></div>
    <div class="absolute right-0 top-1/3 h-96 w-96 rounded-full bg-orange-400/10 blur-3xl"></div>
    <div class="absolute bottom-0 left-1/3 h-80 w-80 rounded-full bg-cyan-500/8 blur-3xl"></div>

    <div
      class="sticky top-0 z-40 border-b border-white/8 bg-gray-950/75 backdrop-blur-xl supports-[backdrop-filter]:bg-gray-950/65"
    >
      <div class="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
        <div>
          <p class="text-xs font-semibold tracking-[0.28em] text-amber-200/70">
            FAVORITE QUESTIONS
          </p>
          <h1 class="mt-2 text-2xl font-semibold text-white">{{ userName }}的收藏题</h1>
        </div>
        <button
          type="button"
          @click="goToDashboard"
          class="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition-all hover:border-white/20 hover:bg-white/10"
        >
          返回仪表盘
        </button>
      </div>
    </div>

    <main class="relative mx-auto max-w-7xl space-y-6 px-6 py-8">
      <section
        class="rounded-[2rem] border border-white/8 bg-white/5 p-6 shadow-2xl shadow-black/20"
      >
        <div class="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div class="max-w-3xl">
            <h2 class="mt-4 text-3xl font-semibold text-white sm:text-4xl">收藏题</h2>
            <p class="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
              每道题默认展示最近一次来源报告的完整复盘，你可以切换不同来源，快速对比自己在不同时间点的回答变化。
            </p>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <div class="rounded-2xl border border-white/8 bg-black/20 px-5 py-4">
              <p class="text-xs text-slate-400">收藏题数</p>
              <p class="mt-2 text-3xl font-semibold text-white">{{ favorites.length }}</p>
            </div>
            <div class="rounded-2xl border border-white/8 bg-black/20 px-5 py-4">
              <p class="text-xs text-slate-400">最近更新</p>
              <p class="mt-2 text-base font-medium text-white">
                {{ formatDateTime(latestUpdatedAt) }}
              </p>
            </div>
          </div>
        </div>
      </section>

      <div
        v-if="statusMessage"
        :class="[
          'rounded-2xl border px-4 py-3 text-sm backdrop-blur-md',
          statusSuccess
            ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200'
            : 'border-rose-500/30 bg-rose-500/10 text-rose-200',
        ]"
      >
        {{ statusMessage }}
      </div>

      <section
        v-if="isLoading"
        class="rounded-[2rem] border border-white/8 bg-white/5 px-6 py-16 text-center"
      >
        <div class="mx-auto flex max-w-md flex-col items-center gap-4">
          <span
            class="h-10 w-10 animate-spin rounded-full border-2 border-white/15 border-t-amber-300"
          ></span>
          <h3 class="text-xl font-semibold text-white">正在加载收藏题</h3>
          <p class="text-sm text-slate-400">系统正在拉取你最近保存的收藏题分组。</p>
        </div>
      </section>

      <section
        v-else-if="errorMessage"
        class="rounded-[2rem] border border-rose-500/20 bg-rose-500/8 px-6 py-12"
      >
        <div class="mx-auto flex max-w-xl flex-col items-center gap-4 text-center">
          <h3 class="text-xl font-semibold text-white">收藏题加载失败</h3>
          <p class="text-sm text-rose-100/80">{{ errorMessage }}</p>
          <button
            type="button"
            @click="favoritesQuery.refetch()"
            class="rounded-full border border-rose-300/20 bg-rose-400/10 px-4 py-2 text-sm text-rose-100 transition-all hover:bg-rose-400/15"
          >
            重试
          </button>
        </div>
      </section>

      <section
        v-else-if="favorites.length === 0"
        class="rounded-[2rem] border border-dashed border-white/12 bg-white/4 px-6 py-16 text-center"
      >
        <div class="mx-auto flex max-w-2xl flex-col items-center gap-5">
          <div
            class="flex h-16 w-16 items-center justify-center rounded-[1.5rem] bg-amber-400/12 text-amber-300"
          >
            <svg class="h-8 w-8" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path
                d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
              />
            </svg>
          </div>
          <div>
            <h3 class="text-2xl font-semibold text-white">还没有收藏题</h3>
            <p class="mt-3 text-sm leading-7 text-slate-400 sm:text-base">
              回到报告页，在你想反复复盘的“面试官提问”卡上点击收藏题，这里会自动按题目聚合。
            </p>
          </div>
          <button
            type="button"
            @click="goToDashboard"
            class="rounded-full border border-amber-400/20 bg-amber-400/10 px-5 py-2.5 text-sm text-amber-100 transition-all hover:bg-amber-400/15"
          >
            去仪表盘查看报告
          </button>
        </div>
      </section>

      <div v-else class="space-y-6">
        <section
          v-for="favorite in favorites"
          :key="favorite.id"
          class="rounded-[2rem] border border-white/8 bg-white/5 p-6 shadow-2xl shadow-black/15"
        >
          <div
            class="flex flex-col gap-4 border-b border-white/8 pb-5 lg:flex-row lg:items-start lg:justify-between"
          >
            <div class="space-y-3">
              <div class="flex flex-wrap items-center gap-2">
                <span class="rounded-full bg-amber-400/12 px-3 py-1 text-xs text-amber-200">
                  {{ favorite.source_count }} 个来源
                </span>
                <span class="rounded-full bg-white/6 px-3 py-1 text-xs text-slate-300">
                  最近更新 {{ formatDateTime(favorite.updated_at) }}
                </span>
              </div>
              <h3 class="text-2xl font-semibold text-white">{{ favorite.question }}</h3>
            </div>
            <button
              type="button"
              @click="handleRemoveFavorite(favorite.id)"
              :disabled="removingFavoriteID === favorite.id"
              class="inline-flex items-center justify-center rounded-full border border-rose-400/20 bg-rose-400/10 px-4 py-2 text-sm text-rose-100 transition-all hover:bg-rose-400/15 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {{ removingFavoriteID === favorite.id ? "移除中..." : "移除整题收藏" }}
            </button>
          </div>

          <div
            v-if="favorite.sources.length > 1"
            class="mt-5 flex flex-wrap gap-2 border-b border-white/8 pb-5"
          >
            <button
              v-for="(source, sourceIndex) in favorite.sources"
              :key="buildSourceKey(source)"
              type="button"
              @click="selectSource(favorite.id, source)"
              :class="[
                'rounded-full border px-3 py-1.5 text-xs transition-all',
                isSelectedSource(favorite, source)
                  ? 'border-amber-300/30 bg-amber-300/12 text-amber-100'
                  : 'border-white/10 bg-white/5 text-slate-300 hover:border-white/20 hover:bg-white/10',
              ]"
            >
              来源 {{ sourceIndex + 1 }} · {{ formatTimestamp(source.interview_created_at) }}
            </button>
          </div>

          <div
            v-for="source in getSelectedSources(favorite)"
            :key="buildSourceKey(source)"
            class="mt-5"
          >
            <div class="flex items-start gap-4">
              <div
                class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-linear-to-br from-amber-400 to-orange-500"
              >
                <svg
                  class="h-5 w-5 text-white"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path
                    d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
                  />
                </svg>
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex flex-wrap items-center gap-2">
                  <span
                    class="rounded-full px-3 py-1 text-xs"
                    :class="getInterviewerRoleBadgeClass(source.interviewer_role)"
                  >
                    {{ formatInterviewerRole(source.interviewer_role) }}
                  </span>
                  <span
                    v-if="source.concept"
                    class="rounded-full bg-blue-500/10 px-3 py-1 text-xs text-blue-300"
                  >
                    {{ source.concept }}
                  </span>
                  <span class="rounded-full bg-white/6 px-3 py-1 text-xs text-slate-300">
                    {{ formatDifficultyLabel(source.difficulty_label) }}
                  </span>
                  <span class="rounded-full bg-white/6 px-3 py-1 text-xs text-slate-400">
                    收藏于 {{ formatDateTime(source.favorited_at) }}
                  </span>
                </div>
                <p class="mt-4 text-xs text-slate-400">面试官提问</p>
                <p class="mt-1 text-lg font-medium text-white">{{ source.interviewer }}</p>
              </div>
            </div>

            <div
              class="mt-6 grid grid-cols-1 gap-4"
              :class="source.standard_answer ? 'lg:grid-cols-2' : 'lg:grid-cols-1'"
            >
              <div class="rounded-2xl border border-blue-500/15 bg-blue-500/6 p-4">
                <div class="flex items-start gap-4">
                  <div
                    class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-linear-to-br from-blue-400 to-blue-600"
                  >
                    <svg
                      class="h-5 w-5 text-white"
                      viewBox="0 0 24 24"
                      fill="none"
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
                    <div class="flex items-center justify-between gap-3">
                      <p class="text-xs text-slate-400">你的回答</p>
                      <span
                        class="rounded-full border border-blue-400/15 bg-blue-400/10 px-2.5 py-1 text-[11px] text-blue-200"
                      >
                        实际作答
                      </span>
                    </div>
                    <p class="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-300">
                      {{ source.interviewee }}
                    </p>
                  </div>
                </div>
              </div>

              <div
                v-if="source.standard_answer"
                class="rounded-2xl border border-emerald-500/15 bg-emerald-500/6 p-4"
              >
                <div class="flex items-start gap-4">
                  <div
                    class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-linear-to-br from-emerald-400 to-cyan-500"
                  >
                    <svg
                      class="h-5 w-5 text-white"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </div>
                  <div class="flex-1">
                    <div class="flex items-center justify-between gap-3">
                      <p class="text-xs text-slate-400">标准答案</p>
                      <span
                        class="rounded-full border border-emerald-400/15 bg-emerald-400/10 px-2.5 py-1 text-[11px] text-emerald-200"
                      >
                        评分参考
                      </span>
                    </div>
                    <p class="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-200">
                      {{ source.standard_answer }}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div
              class="mt-5 flex flex-col gap-4 border-t border-white/8 pt-5 lg:flex-row lg:items-start lg:justify-between"
            >
              <div class="flex items-center gap-2">
                <span class="text-xs text-slate-400">得分</span>
                <span class="text-2xl font-semibold text-amber-300">{{
                  source.score.toFixed(1)
                }}</span>
              </div>
              <div v-if="source.reason_tags.length > 0" class="flex flex-wrap gap-2">
                <span
                  v-for="tag in source.reason_tags"
                  :key="tag"
                  class="rounded-full bg-white/6 px-3 py-1 text-xs text-slate-300"
                >
                  {{ tag }}
                </span>
              </div>
            </div>

            <div v-if="source.score_breakdown" class="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div class="rounded-xl border border-cyan-500/10 bg-cyan-500/5 p-3">
                <p class="text-xs text-cyan-300">主线覆盖</p>
                <p class="mt-1 text-lg font-semibold text-white">
                  {{ Number(source.score_breakdown.coverage_score ?? 0).toFixed(1) }}
                </p>
              </div>
              <div class="rounded-xl border border-blue-500/10 bg-blue-500/5 p-3">
                <p class="text-xs text-blue-300">逻辑一致</p>
                <p class="mt-1 text-lg font-semibold text-white">
                  {{ Number(source.score_breakdown.consistency_score ?? 0).toFixed(1) }}
                </p>
              </div>
              <div class="rounded-xl border border-fuchsia-500/10 bg-fuchsia-500/5 p-3">
                <p class="text-xs text-fuchsia-300">完整度</p>
                <p class="mt-1 text-lg font-semibold text-white">
                  {{ Number(source.score_breakdown.completeness_score ?? 0).toFixed(1) }}
                </p>
              </div>
            </div>

            <div
              v-if="source.strength_points.length > 0 || source.missing_points.length > 0"
              class="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-2"
            >
              <div
                v-if="source.strength_points.length > 0"
                class="rounded-xl border border-emerald-500/15 bg-emerald-500/8 p-4"
              >
                <p class="mb-2 text-xs font-medium text-emerald-300">答到的点</p>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="point in source.strength_points"
                    :key="point"
                    class="rounded-full bg-emerald-500/10 px-3 py-1 text-xs text-emerald-200"
                  >
                    {{ point }}
                  </span>
                </div>
              </div>

              <div
                v-if="source.missing_points.length > 0"
                class="rounded-xl border border-amber-500/15 bg-amber-500/8 p-4"
              >
                <p class="mb-2 text-xs font-medium text-amber-300">缺失的点</p>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="point in source.missing_points"
                    :key="point"
                    class="rounded-full bg-amber-500/10 px-3 py-1 text-xs text-amber-200"
                  >
                    {{ point }}
                  </span>
                </div>
              </div>
            </div>

            <div
              v-if="source.score_rationale"
              class="mt-5 rounded-xl border border-white/6 bg-white/3 p-4"
            >
              <p class="text-xs text-slate-400">分数解释</p>
              <p class="mt-1 text-sm leading-relaxed text-slate-300">
                {{ source.score_rationale }}
              </p>
            </div>

            <div class="mt-5 rounded-xl border border-amber-400/20 bg-amber-400/8 p-4">
              <p class="text-xs font-medium text-amber-300">改进建议</p>
              <p class="mt-1 text-sm leading-relaxed text-slate-200">{{ source.advice }}</p>
            </div>

            <div class="mt-5 flex justify-end">
              <button
                type="button"
                @click="openSourceReport(source)"
                class="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-100 transition-all hover:border-white/20 hover:bg-white/10"
              >
                查看原报告
              </button>
            </div>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>
