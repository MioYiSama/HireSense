<template>
  <div
    class="pointer-events-none fixed right-3 bottom-24 z-30 md:right-6 md:bottom-auto md:top-1/2 md:-translate-y-1/2"
  >
    <div
      v-if="snapshot.visible"
      :class="[
        'relative w-[min(18.75rem,calc(100vw-1.5rem))] overflow-hidden rounded-[2rem] border px-4 py-4 text-white shadow-2xl backdrop-blur-xl transition-all duration-300 md:w-76',
        zoneMeta.shellClass,
        snapshot.active ? 'translate-y-0 scale-100 opacity-100' : 'translate-y-1 scale-[0.985] opacity-95',
      ]"
    >
      <div class="pointer-events-none absolute inset-0 overflow-hidden rounded-[2rem]">
        <div :class="['absolute inset-0 opacity-90', zoneMeta.glowClass]"></div>
        <div class="meter-grid absolute inset-x-5 top-3 bottom-3 opacity-35"></div>
        <div
          v-if="snapshot.active && snapshot.zone === 'red'"
          class="meter-alert absolute inset-0 rounded-[2rem] border border-red-400/30"
        ></div>
      </div>

      <div class="relative flex items-start justify-between gap-3">
        <div>
          <p class="text-[11px] font-semibold tracking-[0.28em] text-white/45">实时自信度</p>
          <p class="mt-1 text-sm font-medium text-white/85">
            {{ snapshot.active ? "语音流畅追踪" : "待命中" }}
          </p>
        </div>
        <div
          class="rounded-full border px-2.5 py-1 text-[11px] font-semibold tracking-[0.12em]"
          :class="zoneMeta.pillClass"
        >
          {{ zoneMeta.zoneText }}
        </div>
      </div>

      <div class="relative mt-3">
        <svg viewBox="0 0 220 172" class="h-auto w-full overflow-visible">
          <defs>
            <linearGradient id="confidence-trace" x1="0%" x2="100%" y1="0%" y2="0%">
              <stop offset="0%" stop-color="#f25d5d" />
              <stop offset="50%" stop-color="#f7bc4b" />
              <stop offset="100%" stop-color="#93f968" />
            </linearGradient>
            <filter id="confidence-blur" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="3" />
            </filter>
          </defs>

          <path
            :d="gaugeArcPath"
            fill="none"
            stroke="rgba(255,255,255,0.08)"
            stroke-linecap="round"
            stroke-width="15"
          />
          <path
            :d="segmentPaths.red"
            fill="none"
            stroke="rgba(242,93,93,0.82)"
            stroke-linecap="round"
            stroke-width="14"
          />
          <path
            :d="segmentPaths.amber"
            fill="none"
            stroke="rgba(247,188,75,0.82)"
            stroke-linecap="round"
            stroke-width="14"
          />
          <path
            :d="segmentPaths.green"
            fill="none"
            stroke="rgba(147,249,104,0.82)"
            stroke-linecap="round"
            stroke-width="14"
          />

          <line
            v-for="tick in ticks"
            :key="tick.index"
            :x1="tick.x1"
            :y1="tick.y1"
            :x2="tick.x2"
            :y2="tick.y2"
            :stroke="tick.color"
            :stroke-opacity="tick.active ? 0.95 : 0.32"
            stroke-linecap="round"
            :stroke-width="tick.major ? 2.8 : 1.4"
          />

          <path
            :d="activeArcPath"
            fill="none"
            stroke="url(#confidence-trace)"
            stroke-linecap="round"
            stroke-width="5.5"
            filter="url(#confidence-blur)"
          />

          <g :transform="needleTransform">
            <line
              :x1="CENTER_X"
              :y1="CENTER_Y"
              :x2="CENTER_X"
              :y2="CENTER_Y - NEEDLE_LENGTH"
              :stroke="zoneMeta.needle"
              stroke-linecap="round"
              stroke-width="4.5"
            />
            <circle :cx="CENTER_X" :cy="CENTER_Y" r="8" fill="#e7edf7" />
            <circle :cx="CENTER_X" :cy="CENTER_Y" r="15" :fill="zoneMeta.hubGlow" fill-opacity="0.24" />
          </g>

          <text :x="CENTER_X" y="90" fill="rgba(255,255,255,0.58)" font-size="10" text-anchor="middle">
            自信度
          </text>
          <text :x="CENTER_X" y="120" fill="white" font-size="32" font-weight="700" text-anchor="middle">
            {{ roundedDisplayScore }}
          </text>
          <text :x="CENTER_X" y="138" fill="rgba(255,255,255,0.66)" font-size="10" text-anchor="middle">
            / 100
          </text>
        </svg>

        <div class="mt-1 flex justify-center">
          <div class="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-white/75">
            {{ snapshot.label }}
          </div>
        </div>
      </div>

      <div
        class="relative mt-3 grid grid-cols-[minmax(0,1.2fr)_minmax(0,0.9fr)_minmax(0,0.9fr)] items-center gap-2 rounded-[1.35rem] border border-white/8 bg-white/4 px-3 py-2.5"
      >
        <div class="min-w-0 flex items-center gap-2 text-[11px] text-white/45">
          <span class="h-2 w-2 rounded-full" :class="zoneMeta.dotClass"></span>
          <span class="truncate">{{ cueLabel }}</span>
        </div>
        <div class="min-w-0 text-center">
          <p class="text-[10px] text-white/35">录音时长</p>
          <p class="font-mono text-sm text-white/90">{{ formattedRecordingTime }}</p>
        </div>
        <div class="min-w-0 text-center">
          <p class="text-[10px] text-white/35">剩余时间</p>
          <p class="font-mono text-sm text-white/90">{{ paddedCountdown }}秒</p>
        </div>
      </div>

      <div class="mt-3 rounded-[1.4rem] border border-white/7 bg-black/18 px-3 py-3">
        <div class="flex items-center justify-between">
          <p class="text-[11px] font-semibold tracking-[0.16em] text-white/42">近 6 秒走势</p>
          <p class="text-xs text-white/62">{{ trendSummary }}</p>
        </div>
        <svg viewBox="0 0 180 40" class="mt-2 h-10 w-full">
          <path d="M 0 32 H 180" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="1" />
          <path
            :d="trendPath"
            fill="none"
            stroke="url(#confidence-trace)"
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="3.2"
          />
        </svg>
      </div>

      <div class="mt-3 grid grid-cols-3 gap-2">
        <div class="rounded-[1.2rem] border border-white/8 bg-white/5 px-3 py-2.5">
          <p class="text-[10px] text-white/38">连续输出</p>
          <p class="mt-1 text-lg font-semibold text-white">{{ metricSpeech }}</p>
        </div>
        <div class="rounded-[1.2rem] border border-white/8 bg-white/5 px-3 py-2.5">
          <p class="text-[10px] text-white/38">稳定度</p>
          <p class="mt-1 text-lg font-semibold text-white">{{ metricStability }}</p>
        </div>
        <div class="rounded-[1.2rem] border border-white/8 bg-white/5 px-3 py-2.5">
          <p class="text-[10px] text-white/38">停顿负载</p>
          <p class="mt-1 text-lg font-semibold text-white">{{ metricPause }}</p>
        </div>
      </div>
    </div>

    <div
      v-else
      class="relative flex items-center gap-3 overflow-hidden rounded-full border border-white/10 bg-black/45 px-4 py-3 text-white shadow-xl backdrop-blur-xl"
    >
      <div class="absolute inset-0 bg-linear-to-r from-white/6 via-transparent to-white/3"></div>
      <div class="relative flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/6">
        <svg viewBox="0 0 48 48" class="h-8 w-8">
          <path d="M 8 34 A 16 16 0 1 1 40 34" fill="none" stroke="rgba(255,255,255,0.18)" stroke-width="4" />
          <line x1="24" y1="33" x2="31" y2="18" stroke="rgba(255,255,255,0.9)" stroke-linecap="round" stroke-width="3" />
          <circle cx="24" cy="33" r="3" fill="#ffffff" />
        </svg>
      </div>
      <div class="relative">
        <p class="text-[11px] font-semibold tracking-[0.16em] text-white/42">实时自信度</p>
        <p class="mt-0.5 text-sm text-white/82">待命中</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { ConfidenceSnapshot } from "@/lib/useConfidenceMeter";

const MIN_SCORE = 5;
const MAX_SCORE = 98;
const START_ANGLE = 200;
const END_ANGLE = 340;
const SEGMENT_BREAKS = {
  red: 246,
  amber: 292,
};
const CENTER_X = 110;
const CENTER_Y = 116;
const RADIUS = 72;
const NEEDLE_LENGTH = 62;

const props = defineProps<{
  snapshot: ConfidenceSnapshot;
  recordingTime: number;
  answerCountdown: number;
}>();

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const polarToCartesian = (centerX: number, centerY: number, radius: number, angleDegrees: number) => {
  const angleRadians = (angleDegrees * Math.PI) / 180;
  return {
    x: centerX + radius * Math.cos(angleRadians),
    y: centerY + radius * Math.sin(angleRadians),
  };
};

const describeArc = (startAngle: number, endAngle: number, radius = RADIUS) => {
  const start = polarToCartesian(CENTER_X, CENTER_Y, radius, startAngle);
  const end = polarToCartesian(CENTER_X, CENTER_Y, radius, endAngle);
  const delta = ((endAngle - startAngle) % 360 + 360) % 360;
  const largeArcFlag = delta > 180 ? "1" : "0";

  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${end.x} ${end.y}`;
};

const scoreRatio = computed(() =>
  clamp((props.snapshot.displayScore - MIN_SCORE) / (MAX_SCORE - MIN_SCORE), 0, 1),
);

const roundedDisplayScore = computed(() => Math.round(props.snapshot.displayScore));

const needleAngle = computed(() => START_ANGLE + (END_ANGLE - START_ANGLE) * scoreRatio.value);

const needleTransform = computed(
  () => `rotate(${needleAngle.value - 270} ${CENTER_X} ${CENTER_Y})`,
);

const gaugeArcPath = computed(() => describeArc(START_ANGLE, END_ANGLE));

const segmentPaths = computed(() => ({
  red: describeArc(START_ANGLE, SEGMENT_BREAKS.red),
  amber: describeArc(SEGMENT_BREAKS.red, SEGMENT_BREAKS.amber),
  green: describeArc(SEGMENT_BREAKS.amber, END_ANGLE),
}));

const activeArcPath = computed(() => describeArc(START_ANGLE, needleAngle.value));

const zoneMeta = computed(() => {
  if (props.snapshot.zone === "red") {
    return {
      zoneText: "红区",
      shellClass:
        "border-red-400/22 bg-[radial-gradient(circle_at_top,_rgba(244,91,91,0.24),_rgba(6,10,18,0.96)_38%,_rgba(2,4,9,0.98)_100%)]",
      glowClass: "bg-[radial-gradient(circle_at_top,_rgba(255,111,111,0.28),_transparent_58%)]",
      pillClass: "border-red-300/22 bg-red-400/12 text-red-100/92",
      dotClass: "bg-red-300 shadow-[0_0_14px_rgba(248,113,113,0.7)]",
      needle: "#ffd6d6",
      hubGlow: "#ff7676",
    };
  }

  if (props.snapshot.zone === "green") {
    return {
      zoneText: "绿区",
      shellClass:
        "border-lime-300/20 bg-[radial-gradient(circle_at_top,_rgba(150,248,107,0.2),_rgba(5,11,17,0.96)_42%,_rgba(2,4,9,0.98)_100%)]",
      glowClass: "bg-[radial-gradient(circle_at_top,_rgba(164,255,123,0.24),_transparent_58%)]",
      pillClass: "border-lime-200/18 bg-lime-300/12 text-lime-50/92",
      dotClass: "bg-lime-300 shadow-[0_0_14px_rgba(163,230,53,0.75)]",
      needle: "#f3ffe4",
      hubGlow: "#adff6a",
    };
  }

  return {
    zoneText: "黄区",
    shellClass:
      "border-amber-300/18 bg-[radial-gradient(circle_at_top,_rgba(247,188,75,0.24),_rgba(5,10,18,0.96)_40%,_rgba(2,4,9,0.98)_100%)]",
    glowClass: "bg-[radial-gradient(circle_at_top,_rgba(255,196,92,0.22),_transparent_58%)]",
    pillClass: "border-amber-200/18 bg-amber-300/10 text-amber-50/92",
    dotClass: "bg-amber-300 shadow-[0_0_14px_rgba(252,211,77,0.72)]",
    needle: "#fff2d3",
    hubGlow: "#ffcf63",
  };
});

const ticks = computed(() =>
  Array.from({ length: 19 }, (_, index) => {
    const progress = index / 18;
    const angle = START_ANGLE + (END_ANGLE - START_ANGLE) * progress;
    const outer = polarToCartesian(CENTER_X, CENTER_Y, RADIUS + 14, angle);
    const inner = polarToCartesian(
      CENTER_X,
      CENTER_Y,
      index % 3 === 0 ? RADIUS + 4 : RADIUS + 8,
      angle,
    );

    return {
      index,
      x1: outer.x,
      y1: outer.y,
      x2: inner.x,
      y2: inner.y,
      major: index % 3 === 0,
      active: progress <= scoreRatio.value,
      color:
        progress < 0.34
          ? "rgba(242,93,93,1)"
          : progress < 0.68
            ? "rgba(247,188,75,1)"
            : "rgba(147,249,104,1)",
    };
  }),
);

const trendPath = computed(() => {
  const points = props.snapshot.trend.map((score, index) => {
    const x = (index / Math.max(props.snapshot.trend.length - 1, 1)) * 180;
    const normalized = clamp((score - MIN_SCORE) / (MAX_SCORE - MIN_SCORE), 0, 1);
    const y = 32 - normalized * 24;
    return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
  });

  return points.join(" ");
});

const formattedRecordingTime = computed(() => {
  const mins = Math.floor(props.recordingTime / 60);
  const secs = props.recordingTime % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
});

const paddedCountdown = computed(() => props.answerCountdown.toString().padStart(2, "0"));

const cueLabel = computed(() => {
  if (!props.snapshot.active) {
    return "已冻结";
  }

  if (props.snapshot.cue === "paused") {
    return "检测到停顿";
  }

  if (props.snapshot.cue === "recovering") {
    return "正在回升";
  }

  if (props.snapshot.cue === "steady") {
    return "节奏稳定";
  }

  return "实时追踪";
});

const trendSummary = computed(() => {
  if (props.snapshot.zone === "green") {
    return "持续抬升";
  }

  if (props.snapshot.zone === "red") {
    return "节奏波动";
  }

  return "逐步稳定";
});

const metricSpeech = computed(() => `${Math.round(props.snapshot.metrics.speechRatio * 100)}%`);

const metricStability = computed(() => `${Math.round(props.snapshot.metrics.stability * 100)}%`);

const metricPause = computed(() => {
  const pauseLoad = props.snapshot.metrics.pauseLoad;

  if (pauseLoad < 0.34) {
    return "低";
  }

  if (pauseLoad < 0.67) {
    return "中";
  }

  return "高";
});
</script>

<style scoped>
.meter-grid {
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.06) 1px, transparent 1px);
  background-size: 18px 18px;
  mask-image: linear-gradient(to bottom, transparent, black 12%, black 88%, transparent);
}

.meter-alert {
  animation: meter-alert 1.45s ease-in-out infinite;
}

@keyframes meter-alert {
  0%,
  100% {
    box-shadow: 0 0 0 rgba(248, 113, 113, 0.08);
    opacity: 0.7;
  }
  50% {
    box-shadow: 0 0 48px rgba(248, 113, 113, 0.18);
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .meter-alert {
    animation: none;
  }
}
</style>
