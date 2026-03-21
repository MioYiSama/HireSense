<template>
  <div
    class="bg-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 shadow-lg hover:shadow-blue-500/10 transition-all duration-500 card-hover"
  >
    <div class="flex items-center justify-between mb-6">
      <h3 class="text-lg font-medium text-white">{{ title }}</h3>
      <select
        v-model="localTimeRange"
        class="bg-white/5 border border-white/10 rounded-lg px-3 py-1 text-xs text-gray-400 focus:outline-none"
        @change="handleTimeRangeChange"
      >
        <option value="30">近30天</option>
        <option value="90">近90天</option>
      </select>
    </div>
    <!-- SVG 图表 -->
    <div class="relative h-64">
      <svg
        width="100%"
        height="100%"
        viewBox="0 0 600 200"
        preserveAspectRatio="none"
      >
        <!-- 网格线 -->
        <line x1="0" y1="50" x2="600" y2="50" stroke="rgba(255,255,255,0.05)" />
        <line
          x1="0"
          y1="100"
          x2="600"
          y2="100"
          stroke="rgba(255,255,255,0.05)"
        />
        <line
          x1="0"
          y1="150"
          x2="600"
          y2="150"
          stroke="rgba(255,255,255,0.05)"
        />
        <line
          x1="0"
          y1="200"
          x2="600"
          y2="200"
          stroke="rgba(255,255,255,0.05)"
        />

        <!-- 渐变定义 -->
        <defs>
          <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#06b6d4" />
            <stop offset="100%" stop-color="#a855f7" />
          </linearGradient>
          <linearGradient id="areaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="rgba(6, 182, 212, 0.3)" />
            <stop offset="100%" stop-color="rgba(6, 182, 212, 0)" />
          </linearGradient>
        </defs>

        <!-- 填充区域 -->
        <path :d="growthAreaPath" fill="url(#areaGradient)" />

        <!-- 曲线 -->
        <path
          class="chart-glow"
          :d="growthCurvePath"
          fill="none"
          stroke="url(#lineGradient)"
          stroke-width="3"
          stroke-linecap="round"
        />

        <!-- 数据点 -->
        <circle
          v-for="(point, index) in dataPoints"
          :key="index"
          :cx="point.x"
          :cy="point.y"
          r="4"
          :fill="
            index === 0 || index === dataPoints.length - 1
              ? '#06b6d4'
              : '#8b5cf6'
          "
          :class="{
            'drop-shadow-lg': index === 0 || index === dataPoints.length - 1,
          }"
        />
      </svg>
      <!-- X轴标签 -->
      <div
        class="absolute bottom-0 left-0 right-0 flex justify-between text-xs text-gray-500 px-2 transform translate-y-6"
      >
        <span v-for="(label, index) in xAxisLabels" :key="index">{{
          label
        }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

// 防抖函数
const debounce = <T extends (...args: any[]) => any>(func: T, wait: number): ((...args: Parameters<T>) => void) => {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => {
      func(...args);
    }, wait);
  };
};

interface GrowthData {
  score: number;
  date: Date;
}

// Props
const props = defineProps<{
  data: GrowthData[];
  timeRange: string;
  title: string;
}>();

// Emits
const emit = defineEmits<{
  (e: "update:timeRange", value: string): void;
}>();

// 本地时间范围
const localTimeRange = ref(props.timeRange);

// 防抖处理时间范围变化
const debouncedEmitTimeRange = debounce((value: string) => {
  emit("update:timeRange", value);
}, 300);

// 监听props变化
watch(
  () => props.timeRange,
  (newValue) => {
    localTimeRange.value = newValue;
  },
);

// 处理时间范围变化
const handleTimeRangeChange = () => {
  debouncedEmitTimeRange(localTimeRange.value);
};

// 图表配置常量
const CHART_CONFIG = {
  width: 600,
  height: 160,
  padding: 20,
} as const;

// 计算数据范围和有效点
const chartData = computed(() => {
  const data = filteredData.value;
  if (data.length === 0) {
    return {
      minScore: 0,
      maxScore: 0,
      scoreRange: 100,
      validPoints: [] as { x: number; y: number }[],
    };
  }

  const minScore = Math.min(...data.map((d) => d.score));
  const maxScore = Math.max(...data.map((d) => d.score));
  const scoreRange = maxScore - minScore || 100;

  const points = data.map((d, i) => {
    if (!d) {
      return { x: 0, y: 0 };
    }
    const ratio = data.length === 1 ? 0.5 : i / (data.length - 1);
    const x =
      CHART_CONFIG.padding +
      ratio * (CHART_CONFIG.width - CHART_CONFIG.padding * 2);
    const y =
      CHART_CONFIG.height -
      CHART_CONFIG.padding -
      ((d.score - minScore) / scoreRange) *
        (CHART_CONFIG.height - CHART_CONFIG.padding * 2);
    return { x, y };
  });

  const validPoints: { x: number; y: number }[] = points.filter(
    (p): p is { x: number; y: number } => p !== undefined,
  );

  return { minScore, maxScore, scoreRange, validPoints };
});

// 过滤后的数据
const filteredData = computed(() => {
  const now = new Date();
  const days = parseInt(props.timeRange);
  const cutoffDate = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);

  return props.data.filter((item) => item.date >= cutoffDate);
});

// 生成成长曲线SVG路径
const growthCurvePath = computed(() => {
  const { validPoints } = chartData.value;

  if (validPoints.length === 0) {
    return "M0,100";
  }

  if (validPoints.length === 1) {
    const firstPoint = validPoints[0];
    if (firstPoint) {
      const { x, y } = firstPoint;
      return `M${x},${y}`;
    }
    return "M0,100";
  }

  const firstPoint = validPoints[0];
  if (!firstPoint) {
    return "M0,100";
  }

  let path = `M${firstPoint.x},${firstPoint.y}`;

  if (validPoints.length >= 2) {
    const secondPoint = validPoints[1];
    if (secondPoint) {
      const midX = (firstPoint.x + secondPoint.x) / 2;
      path += ` Q${midX},${firstPoint.y} ${secondPoint.x},${secondPoint.y}`;
    }

    for (let i = 2; i < validPoints.length; i++) {
      const currentPoint = validPoints[i];
      if (currentPoint) {
        path += ` T${currentPoint.x},${currentPoint.y}`;
      }
    }
  }

  const lastPoint = validPoints[validPoints.length - 1];
  if (lastPoint) {
    path += ` L${lastPoint.x},${lastPoint.y}`;
  }

  return path;
});

// 生成填充区域路径
const growthAreaPath = computed(() => {
  const { validPoints } = chartData.value;

  if (validPoints.length === 0) {
    return "M0,100 V200 H0 Z";
  }

  if (validPoints.length === 1) {
    const firstPoint = validPoints[0];
    if (firstPoint) {
      const { x, y } = firstPoint;
      return `M${x},${y} L${x},${CHART_CONFIG.height - CHART_CONFIG.padding} L${CHART_CONFIG.padding},${CHART_CONFIG.height - CHART_CONFIG.padding} Z`;
    }
    return "M0,100 V200 H0 Z";
  }

  const firstPoint = validPoints[0];
  if (!firstPoint) {
    return "M0,100 V200 H0 Z";
  }

  let path = `M${firstPoint.x},${firstPoint.y}`;

  if (validPoints.length >= 2) {
    const secondPoint = validPoints[1];
    if (secondPoint) {
      const midX = (firstPoint.x + secondPoint.x) / 2;
      path += ` Q${midX},${firstPoint.y} ${secondPoint.x},${secondPoint.y}`;
    }

    for (let i = 2; i < validPoints.length; i++) {
      const currentPoint = validPoints[i];
      if (currentPoint) {
        path += ` T${currentPoint.x},${currentPoint.y}`;
      }
    }
  }

  const lastPoint = validPoints[validPoints.length - 1];
  if (lastPoint) {
    path += ` L${lastPoint.x},${lastPoint.y}`;
  }
  path += ` L${CHART_CONFIG.width - CHART_CONFIG.padding},${CHART_CONFIG.height - CHART_CONFIG.padding} L${CHART_CONFIG.padding},${CHART_CONFIG.height - CHART_CONFIG.padding} Z`;
  return path;
});

// 生成数据点
const dataPoints = computed(() => {
  const { validPoints } = chartData.value;
  return validPoints.map((point, index) => ({
    ...point,
    score: filteredData.value[index]?.score || 0,
  }));
});

// 生成X轴标签
const xAxisLabels = computed(() => {
  const data = filteredData.value;
  if (data.length === 0) {
    return [];
  }

  // 取5个均匀分布的点
  const labels = [];
  const step = Math.max(1, Math.floor((data.length - 1) / 4));

  for (let i = 0; i < data.length; i += step) {
    const currentData = data[i];
    if (!currentData || !currentData.date) {
      continue;
    }
    const date = currentData.date;
    labels.push(`${date.getMonth() + 1}/${date.getDate()}`);
  }

  // 确保最后一个标签是今天
  if (labels.length > 0) {
    labels[labels.length - 1] = "今天";
  }

  return labels;
});
</script>

<style scoped>
.chart-glow {
  filter: drop-shadow(0 0 8px rgba(6, 182, 212, 0.5));
}

.card-hover {
  transition: all 0.3s ease;
}

.card-hover:hover {
  transform: translateY(-2px);
}
</style>
