<script setup lang="ts">
import { computed } from "vue";

import { ResumeAnalysisLabel, type ResumeAnalysis } from "@/api";
import { buildHighlightedSegments } from "@/lib/resumeAnalysis";

const props = defineProps<{
  analysis: ResumeAnalysis;
  selectedBlockId?: string | null;
}>();

const emit = defineEmits<{
  selectBlock: [blockId: string];
}>();

const labelMeta: Record<
  ResumeAnalysisLabel,
  { chip: string; badgeClass: string; blockClass: string; markClass: string }
> = {
  [ResumeAnalysisLabel.Strength]: {
    chip: "优势项",
    badgeClass: "badge badge-success badge-sm",
    blockClass: "border-success/30 bg-success/10 hover:bg-success/15",
    markClass: "bg-success text-success-content",
  },
  [ResumeAnalysisLabel.Probe]: {
    chip: "待核验",
    badgeClass: "badge badge-warning badge-sm",
    blockClass: "border-warning/35 bg-warning/10 hover:bg-warning/15",
    markClass: "bg-warning text-warning-content",
  },
  [ResumeAnalysisLabel.Risk]: {
    chip: "风险项",
    badgeClass: "badge badge-error badge-sm",
    blockClass: "border-error/35 bg-error/10 hover:bg-error/15",
    markClass: "bg-error text-error-content",
  },
  [ResumeAnalysisLabel.Neutral]: {
    chip: "中性",
    badgeClass: "badge badge-neutral badge-sm",
    blockClass: "border-base-300 bg-base-100 hover:bg-base-200/70",
    markClass: "bg-base-300 text-base-content",
  },
};

const segmentsByBlockId = computed(() => {
  return Object.fromEntries(
    props.analysis.blocks.map((block) => {
      return [block.id, buildHighlightedSegments(block)];
    }),
  );
});

const isSelected = (blockId: string) => {
  return props.selectedBlockId === blockId;
};

const getBlockMeta = (label: ResumeAnalysisLabel) => {
  return labelMeta[label];
};

const selectBlock = (blockId: string) => {
  emit("selectBlock", blockId);
};

const getJobLabel = (job: string) => {
  if (job === "backend") {
    return "后端";
  }

  if (job === "frontend") {
    return "前端";
  }

  return "岗位";
};
</script>

<template>
  <div class="mockup-window border-base-300 bg-base-300 border shadow-xl">
    <div class="border-base-300 bg-base-200 border-b px-4 py-3 sm:px-6">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="text-base-content/60 text-xs font-semibold tracking-[0.28em]">简历评审</p>
          <h2 class="text-base-content mt-1 text-2xl font-semibold sm:text-3xl">简历标注视图</h2>
        </div>
        <div class="flex items-center gap-2">
          <span class="badge badge-outline">{{ getJobLabel(analysis.job) }}</span>
          <span class="badge badge-ghost">{{ analysis.blocks.length }} 段</span>
        </div>
      </div>
      <p class="text-base-content/70 mt-3 max-w-3xl text-sm leading-7">
        按段展示简历中的优势项、待核验项与风险项，便于快速定位需要补充事实依据的内容。
      </p>
    </div>

    <article class="bg-base-100 px-4 py-5 sm:px-6 sm:py-6">
      <div class="space-y-4">
        <button
          v-for="block in analysis.blocks"
          :key="block.id"
          type="button"
          :class="[
            'card w-full border text-left transition-all duration-200',
            getBlockMeta(block.label).blockClass,
            isSelected(block.id)
              ? 'ring-primary ring-offset-base-100 ring-2 ring-offset-2'
              : 'shadow-sm',
          ]"
          @click="selectBlock(block.id)"
        >
          <div class="card-body gap-3 p-4 sm:p-5">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div class="flex items-center gap-3">
                <span :class="getBlockMeta(block.label).badgeClass">{{
                  getBlockMeta(block.label).chip
                }}</span>
                <span class="text-base-content/55 text-xs font-medium tracking-[0.18em] uppercase">
                  {{ block.id }}
                </span>
              </div>
              <span class="badge badge-outline badge-sm">查看说明</span>
            </div>

            <div class="text-base-content text-sm leading-8 whitespace-pre-wrap sm:text-[15px]">
              <template
                v-for="(segment, index) in segmentsByBlockId[block.id]"
                :key="`${block.id}-${index}`"
              >
                <span
                  v-if="segment.label"
                  :class="[
                    'rounded-box px-1.5 py-0.5 font-semibold',
                    getBlockMeta(segment.label).markClass,
                  ]"
                  :title="segment.comment || block.reason"
                >
                  {{ segment.text }}
                </span>
                <span v-else>{{ segment.text }}</span>
              </template>
            </div>

            <div class="divider my-0"></div>

            <p class="text-base-content/70 text-sm leading-7">
              {{ block.reason }}
            </p>

            <div v-if="block.callout && isSelected(block.id)" class="alert alert-error">
              <div class="space-y-1">
                <div class="font-semibold">
                  {{ block.callout.title || "风险提示" }}
                </div>
                <div class="text-sm leading-7">
                  {{ block.callout.body }}
                </div>
              </div>
            </div>
          </div>
        </button>
      </div>
    </article>
  </div>
</template>
