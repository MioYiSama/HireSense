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

    <div ref="chartRef" class="h-64 w-full overflow-hidden rounded-lg"></div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { graphic, init, use, type ECharts, type EChartsOption, type SetOptionOpts } from "echarts/core";
import { LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

use([LineChart, GridComponent, TooltipComponent, CanvasRenderer]);

const debounce = <T extends (...args: any[]) => void>(
  func: T,
  wait: number,
): ((...args: Parameters<T>) => void) => {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return (...args: Parameters<T>) => {
    if (timeout !== null) {
      clearTimeout(timeout);
    }

    timeout = setTimeout(() => {
      func(...args);
    }, wait);
  };
};

interface GrowthData {
  score: number;
  date: Date;
}

const props = defineProps<{
  data: GrowthData[];
  timeRange: string;
  title: string;
}>();

const emit = defineEmits<{
  (e: "update:timeRange", value: string): void;
}>();

const localTimeRange = ref(props.timeRange);
const chartRef = ref<HTMLDivElement | null>(null);

let chartInstance: ECharts | null = null;
let resizeObserver: ResizeObserver | null = null;
let isUnmounted = false;

const formatDateLabel = (date: Date) => {
  return `${date.getMonth() + 1}/${date.getDate()}`;
};

const filteredData = computed(() => {
  const parsedDays = Number.parseInt(props.timeRange, 10);
  const days = Number.isFinite(parsedDays) ? parsedDays : 30;
  const cutoffDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000);

  return props.data
    .map((item) => {
      const date = item.date instanceof Date ? item.date : new Date(item.date);
      return {
        date,
        score: Number(item.score),
      };
    })
    .filter((item) => Number.isFinite(item.score) && item.date >= cutoffDate)
    .sort((left, right) => left.date.getTime() - right.date.getTime());
});

const xAxisLabels = computed(() => {
  return filteredData.value.map((item) => formatDateLabel(item.date));
});

const scoreValues = computed(() => {
  return filteredData.value.map((item) => item.score);
});

const yAxisRange = computed(() => {
  if (scoreValues.value.length === 0) {
    return { min: 0, max: 10 };
  }

  const minScore = Math.min(...scoreValues.value);
  const maxScore = Math.max(...scoreValues.value);

  if (minScore === maxScore) {
    const padding = Math.max(Math.abs(minScore) * 0.15, 1);
    return {
      min: Number(Math.max(0, minScore - padding).toFixed(1)),
      max: Number((maxScore + padding).toFixed(1)),
    };
  }

  const padding = Math.max((maxScore - minScore) * 0.2, 0.5);
  return {
    min: Number(Math.max(0, minScore - padding).toFixed(1)),
    max: Number((maxScore + padding).toFixed(1)),
  };
});

const createChartOption = (): EChartsOption => {
  return {
    animationDuration: 500,
    animationDurationUpdate: 300,
    grid: {
      left: 8,
      right: 8,
      top: 16,
      bottom: 32,
      containLabel: true,
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(15, 23, 42, 0.92)",
      borderColor: "rgba(148, 163, 184, 0.2)",
      borderWidth: 1,
      textStyle: {
        color: "#e2e8f0",
        fontSize: 12,
      },
      axisPointer: {
        type: "line",
        lineStyle: {
          color: "rgba(6, 182, 212, 0.35)",
          width: 1,
        },
      },
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: xAxisLabels.value,
      axisLine: {
        show: false,
      },
      axisTick: {
        show: false,
      },
      axisLabel: {
        color: "rgba(148, 163, 184, 0.85)",
        fontSize: 12,
        margin: 16,
        hideOverlap: true,
      },
    },
    yAxis: {
      type: "value",
      min: yAxisRange.value.min,
      max: yAxisRange.value.max,
      splitNumber: 4,
      axisLine: {
        show: false,
      },
      axisTick: {
        show: false,
      },
      axisLabel: {
        show: false,
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: "rgba(255,255,255,0.05)",
        },
      },
    },
    series: [
      {
        name: "得分",
        type: "line",
        data: scoreValues.value,
        smooth: 0.35,
        clip: true,
        showSymbol: true,
        symbol: "circle",
        symbolSize: 8,
        lineStyle: {
          width: 3,
          color: new graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: "#06b6d4" },
            { offset: 1, color: "#a855f7" },
          ]),
        },
        areaStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(6, 182, 212, 0.28)" },
            { offset: 1, color: "rgba(6, 182, 212, 0)" },
          ]),
        },
        itemStyle: {
          color: "#8b5cf6",
          borderColor: "#0f172a",
          borderWidth: 2,
        },
        emphasis: {
          scale: true,
          itemStyle: {
            color: "#06b6d4",
          },
        },
      },
    ],
  };
};

const renderChart = () => {
  if (!chartRef.value) {
    return;
  }

  if (!chartRef.value || isUnmounted) {
    return;
  }

  if (!chartInstance) {
    chartInstance = init(chartRef.value);
  }

  const updateOptions: SetOptionOpts = {
    notMerge: true,
    lazyUpdate: true,
  };

  chartInstance.setOption(createChartOption(), updateOptions);
  chartInstance.resize();
};

const handleTimeRangeChange = () => {
  debouncedEmitTimeRange(localTimeRange.value);
};

const debouncedEmitTimeRange = debounce((value: string) => {
  emit("update:timeRange", value);
}, 300);

watch(
  () => props.timeRange,
  (newValue) => {
    localTimeRange.value = newValue;
  },
);

watch(
  [filteredData, () => props.title],
  async () => {
    await nextTick();
    await renderChart();
  },
  { deep: true },
);

onMounted(async () => {
  isUnmounted = false;
  await nextTick();
  renderChart();

  if (chartRef.value && typeof ResizeObserver !== "undefined") {
    resizeObserver = new ResizeObserver(() => {
      chartInstance?.resize();
    });
    resizeObserver.observe(chartRef.value);
  }
});

onBeforeUnmount(() => {
  isUnmounted = true;
  resizeObserver?.disconnect();
  resizeObserver = null;

  chartInstance?.dispose();
  chartInstance = null;
});
</script>

<style scoped>
.card-hover {
  transition: all 0.3s ease;
}

.card-hover:hover {
  transform: translateY(-2px);
}
</style>
