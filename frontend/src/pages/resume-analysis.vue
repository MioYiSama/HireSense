<script setup lang="ts">
import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { ResumeAnalysisLabel } from "@/api";
import ResumeAnalysisDocument from "@/components/ResumeAnalysisDocument.vue";
import {
  generateResumeAnalysis,
  getApiErrorMessage,
  queryKeys,
  useResumeAnalysisQuery,
} from "@/lib/api";
import {
  countBlocksByLabel,
  formatResumeAnalysisTime,
  formatResumeAnalysisTone,
} from "@/lib/resumeAnalysis";
import { getUserInfo } from "@/utils/token";

const router = useRouter();
const queryClient = useQueryClient();
const storedUserInfo = getUserInfo();
const userName = ref(storedUserInfo?.name || "候选人");
const statusMessage = ref("");
const statusSuccess = ref(false);
let statusTimeout: number | null = null;

const resumeAnalysisQuery = useResumeAnalysisQuery();
const selectedBlockId = ref<string | null>(null);

const reanalyzeMutation = useMutation({
  mutationFn: generateResumeAnalysis,
  onSuccess: (analysis) => {
    queryClient.setQueryData(queryKeys.resumeAnalysis(), analysis);
    statusMessage.value = "简历分析已刷新";
    statusSuccess.value = true;
    if (statusTimeout) {
      clearTimeout(statusTimeout);
    }
    statusTimeout = window.setTimeout(() => {
      statusMessage.value = "";
      statusTimeout = null;
    }, 3000);
  },
});

const analysis = computed(() => {
  return resumeAnalysisQuery.data.value ?? null;
});

const isLoading = computed(() => {
  return resumeAnalysisQuery.isPending.value && !analysis.value;
});

const counts = computed(() => {
  if (!analysis.value) {
    return {
      strength: 0,
      probe: 0,
      risk: 0,
      neutral: 0,
    };
  }

  return countBlocksByLabel(analysis.value);
});

const selectedBlock = computed(() => {
  if (!analysis.value || !selectedBlockId.value) {
    return null;
  }

  return analysis.value.blocks.find((block) => block.id === selectedBlockId.value) ?? null;
});

const riskBlocks = computed(() => {
  return analysis.value?.blocks.filter((block) => block.label === ResumeAnalysisLabel.Risk) ?? [];
});

watch(
  analysis,
  (value) => {
    if (!value || value.blocks.length === 0) {
      selectedBlockId.value = null;
      return;
    }

    const preferredBlock =
      value.blocks.find((block) => block.label === ResumeAnalysisLabel.Risk) ?? value.blocks[0];
    selectedBlockId.value = preferredBlock?.id ?? null;
  },
  { immediate: true },
);

const goToProfile = () => {
  router.push("/profile");
};

const handleReanalyze = async () => {
  try {
    await reanalyzeMutation.mutateAsync();
  } catch (error) {
    statusMessage.value = getApiErrorMessage(error, "刷新简历分析失败");
    statusSuccess.value = false;
    if (statusTimeout) {
      clearTimeout(statusTimeout);
    }
    statusTimeout = window.setTimeout(() => {
      statusMessage.value = "";
      statusTimeout = null;
    }, 3000);
  }
};

const selectBlock = (blockId: string) => {
  selectedBlockId.value = blockId;
};
</script>

<template>
  <div class="bg-base-200 text-base-content min-h-screen">
    <div class="navbar border-base-300 bg-base-100 border-b">
      <div class="mx-auto flex w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div>
          <div class="text-base-content/60 text-xs font-semibold tracking-[0.28em]">简历评审</div>
          <div class="text-xl font-semibold sm:text-2xl">{{ userName }}的简历分析结果</div>
        </div>
        <div class="flex items-center gap-2">
          <button @click="goToProfile" class="btn btn-ghost btn-sm sm:btn-md">返回个人中心</button>
          <button
            @click="handleReanalyze"
            :disabled="reanalyzeMutation.isPending.value"
            class="btn btn-primary btn-sm sm:btn-md"
          >
            <span
              v-if="reanalyzeMutation.isPending.value"
              class="loading loading-spinner loading-xs"
            ></span>
            {{ reanalyzeMutation.isPending.value ? "重新分析中..." : "重新分析" }}
          </button>
        </div>
      </div>
    </div>

    <main class="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <section class="hero rounded-box border-base-300 bg-base-100 border">
        <div
          class="hero-content w-full flex-col items-start gap-6 py-8 lg:flex-row lg:items-end lg:justify-between"
        >
          <div class="max-w-3xl">
            <div class="badge badge-neutral badge-outline">简历分析概览</div>
            <h1 class="mt-4 text-3xl leading-tight font-semibold sm:text-4xl">
              简历中的优势项、待核验项与风险项
            </h1>
            <p class="text-base-content/70 mt-4 text-sm leading-8 sm:text-base">
              绿色表示优势项，黄色表示待进一步核验的经历，红色表示存在表述风险的内容。
            </p>
          </div>
          <div
            class="stats stats-vertical border-base-300 bg-base-200 sm:stats-horizontal border shadow-sm"
          >
            <div class="stat px-5 py-4">
              <div class="stat-title">生成时间</div>
              <div class="stat-value text-lg">
                {{ analysis ? formatResumeAnalysisTime(analysis.generated_at) : "--" }}
              </div>
            </div>
            <!-- <div class="stat px-5 py-4">
              <div class="stat-title">评估基调</div>
              <div class="stat-value text-lg">
                {{ formatResumeAnalysisTone(analysis?.overall_tone) }}
              </div>
            </div> -->
          </div>
        </div>
      </section>

      <div v-if="statusMessage" :class="['alert', statusSuccess ? 'alert-success' : 'alert-error']">
        <span>{{ statusMessage }}</span>
      </div>

      <div v-if="isLoading" class="card border-base-300 bg-base-100 border shadow-sm">
        <div class="card-body items-center py-16 text-center">
          <span class="loading loading-spinner loading-lg text-primary"></span>
          <h2 class="card-title mt-4">正在加载最近一次简历分析</h2>
          <p class="text-base-content/70">系统会展示你最近一次保存的分析结果。</p>
        </div>
      </div>

      <div
        v-else-if="!analysis"
        class="hero rounded-box border-base-300 bg-base-100 border border-dashed"
      >
        <div class="hero-content py-16 text-center">
          <div class="max-w-2xl">
            <div class="badge badge-outline">暂无分析结果</div>
            <h2 class="mt-4 text-3xl font-semibold">尚未生成简历分析结果</h2>
            <p class="text-base-content/70 mt-4 text-sm leading-8 sm:text-base">
              请先返回个人中心上传或粘贴简历，再执行“分析简历”。
              系统会先保存当前内容，再生成最新的分析结果。
            </p>
            <button @click="goToProfile" class="btn btn-primary mt-8">去个人中心</button>
          </div>
        </div>
      </div>

      <div v-else class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <ResumeAnalysisDocument
          :analysis="analysis"
          :selected-block-id="selectedBlockId"
          @select-block="selectBlock"
        />

        <aside class="space-y-6 xl:sticky xl:top-6 xl:self-start">
          <section class="card border-base-300 bg-base-100 border shadow-sm">
            <div class="card-body">
              <div class="flex items-center justify-between gap-3">
                <h2 class="card-title text-base">分析总览</h2>
                <div class="badge badge-outline">
                  {{ formatResumeAnalysisTone(analysis.overall_tone) }}
                </div>
              </div>
              <p class="text-base-content/75 text-sm leading-7">
                {{ analysis.summary }}
              </p>
              <div class="divider my-0"></div>
              <div class="stats stats-vertical bg-base-200 shadow-none">
                <div class="stat px-4 py-3">
                  <div class="stat-title">优势项</div>
                  <div class="stat-value text-success">{{ counts.strength }}</div>
                </div>
                <div class="stat px-4 py-3">
                  <div class="stat-title">待核验项</div>
                  <div class="stat-value text-warning">{{ counts.probe }}</div>
                </div>
                <div class="stat px-4 py-3">
                  <div class="stat-title">风险项</div>
                  <div class="stat-value text-error">{{ counts.risk }}</div>
                </div>
                <div class="stat px-4 py-3">
                  <div class="stat-title">中性信息</div>
                  <div class="stat-value">{{ counts.neutral }}</div>
                </div>
              </div>
            </div>
          </section>

          <section class="card border-base-300 bg-base-100 border shadow-sm">
            <div class="card-body">
              <h2 class="card-title text-base">当前说明</h2>
              <div v-if="selectedBlock" class="space-y-4">
                <div class="flex items-center gap-2">
                  <span class="badge badge-outline">{{ selectedBlock.id }}</span>
                  <span
                    :class="[
                      'badge',
                      selectedBlock.label === ResumeAnalysisLabel.Strength
                        ? 'badge-success'
                        : selectedBlock.label === ResumeAnalysisLabel.Probe
                          ? 'badge-warning'
                          : selectedBlock.label === ResumeAnalysisLabel.Risk
                            ? 'badge-error'
                            : 'badge-neutral',
                    ]"
                  >
                    {{
                      selectedBlock.label === ResumeAnalysisLabel.Strength
                        ? "优势项"
                        : selectedBlock.label === ResumeAnalysisLabel.Probe
                          ? "待核验"
                          : selectedBlock.label === ResumeAnalysisLabel.Risk
                            ? "风险项"
                            : "中性"
                    }}
                  </span>
                </div>

                <div class="rounded-box bg-base-200 text-base-content/80 p-4 text-sm leading-7">
                  {{ selectedBlock.reason }}
                </div>

                <div v-if="selectedBlock.callout" class="alert alert-error">
                  <div>
                    <div class="font-semibold">
                      {{ selectedBlock.callout.title || "高风险批注" }}
                    </div>
                    <div class="mt-1 text-sm leading-7">
                      {{ selectedBlock.callout.body }}
                    </div>
                  </div>
                </div>

                <div v-if="selectedBlock.highlight_phrases?.length" class="space-y-2">
                  <div
                    class="text-base-content/55 text-xs font-semibold tracking-[0.24em] uppercase"
                  >
                    命中短语
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <span
                      v-for="phrase in selectedBlock.highlight_phrases"
                      :key="`${selectedBlock.id}-${phrase.text}`"
                      class="badge badge-outline badge-lg"
                    >
                      {{ phrase.text }}
                    </span>
                  </div>
                </div>
              </div>
              <div v-else class="alert">
                <span>选择左侧段落后，可查看对应的分析说明与风险提示。</span>
              </div>
            </div>
          </section>

          <section class="card border-base-300 bg-base-100 border shadow-sm">
            <div class="card-body">
              <h2 class="card-title text-base">标注说明</h2>
              <ul class="menu rounded-box bg-base-200">
                <li>
                  <span
                    ><span class="badge badge-success">绿色</span>
                    优势项，建议在沟通中主动展开。</span
                  >
                </li>
                <li>
                  <span
                    ><span class="badge badge-warning">黄色</span>
                    待核验项，需要准备具体贡献与事实依据。</span
                  >
                </li>
                <li>
                  <span
                    ><span class="badge badge-error">红色</span>
                    风险项，建议收敛表述并补充证据。</span
                  >
                </li>
              </ul>
            </div>
          </section>

          <section
            v-if="riskBlocks.length > 0"
            class="card border-error/30 bg-base-100 border shadow-sm"
          >
            <div class="card-body">
              <div class="flex items-center justify-between gap-3">
                <h2 class="card-title text-base">风险项摘要</h2>
                <div class="badge badge-error">{{ riskBlocks.length }}</div>
              </div>
              <div class="join join-vertical w-full">
                <button
                  v-for="block in riskBlocks"
                  :key="block.id"
                  type="button"
                  class="btn join-item btn-ghost h-auto min-h-0 justify-start px-4 py-4 text-left normal-case"
                  @click="selectBlock(block.id)"
                >
                  <div class="space-y-1">
                    <div class="text-error text-xs font-semibold tracking-[0.18em] uppercase">
                      {{ block.id }}
                    </div>
                    <div class="text-base-content line-clamp-2 text-sm leading-7">
                      {{ block.text }}
                    </div>
                  </div>
                </button>
              </div>
            </div>
          </section>
        </aside>
      </div>
    </main>
  </div>
</template>
