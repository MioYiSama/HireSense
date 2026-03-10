<!-- 投影仪组件 -->
<script setup lang="ts">
import Carousel from "./Carousel.vue";

const slides = [
  {
    icon: "brain",
    title: "AI智能面试官",
    description: "模拟真实面试场景，智能追问与互动",
    gradient: "from-blue-500/20 to-purple-500/20",
  },
  {
    icon: "mic",
    title: "语音交互",
    description: "支持语音输入，自然流畅的对话体验",
    gradient: "from-purple-500/20 to-pink-500/20",
  },
  {
    icon: "code",
    title: "在线编程",
    description: "实时编写代码，AI智能评估代码质量",
    gradient: "from-green-500/20 to-blue-500/20",
  },
  {
    icon: "trending-up",
    title: "能力提升",
    description: "个性化学习路径，持续提升面试能力",
    gradient: "from-orange-500/20 to-red-500/20",
  },
];
</script>

<template>
  <div class="relative w-full">
    <!-- 投影仪 -->
    <div class="absolute -left-3 lg:-left-5 top-1/2 -translate-y-1/2 z-30">
      <div class="relative">
        <div
          class="relative w-16 h-24 bg-gradient-to-b from-gray-700 via-gray-800 to-gray-900 rounded-lg shadow-2xl border border-gray-600 flex flex-col items-center justify-center"
        >
          <div class="absolute top-2 left-1/2 -translate-x-1/2 flex space-x-1">
            <div class="w-1 h-2 bg-gray-500 rounded-full"></div>
            <div class="w-1 h-2 bg-gray-500 rounded-full"></div>
            <div class="w-1 h-2 bg-gray-500 rounded-full"></div>
          </div>

          <div
            class="text-xs text-gray-300 mb-2 font-bold tracking-wider drop-shadow-sm"
          >
            HIRE
          </div>

          <div class="relative mb-2">
            <div
              class="w-9 h-9 rounded-full bg-gradient-to-br from-gray-600 to-gray-700 border-2 border-gray-500 shadow-inner"
            ></div>
            <div
              class="absolute inset-0.5 w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 via-blue-500 to-blue-700 shadow-lg shadow-blue-500/50 animate-pulse border border-blue-300/50"
            ></div>
            <div
              class="absolute top-1 left-1 w-2 h-2 rounded-full bg-white/30 blur-[1px]"
            ></div>
          </div>

          <div class="flex space-x-2 mb-1">
            <div
              class="w-2 h-2 rounded-full bg-gray-500 hover:bg-gray-400 transition-colors cursor-pointer"
            ></div>
            <div
              class="w-2 h-2 rounded-full bg-gray-500 hover:bg-gray-400 transition-colors cursor-pointer"
            ></div>
          </div>

          <div
            class="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse shadow-lg shadow-green-400/50"
          ></div>

          <div
            class="absolute right-0 top-1/2 -translate-y-1/2 flex flex-col space-y-1"
          >
            <div class="w-1 h-1.5 bg-gray-500 rounded-r"></div>
            <div class="w-1 h-1.5 bg-gray-500 rounded-r"></div>
            <div class="w-1 h-1.5 bg-gray-500 rounded-r"></div>
          </div>
        </div>

        <div
          class="w-4 h-8 bg-gradient-to-b from-gray-700 to-gray-800 mx-auto rounded-b-lg shadow-md"
        ></div>

        <div
          class="w-12 h-2.5 bg-gradient-to-b from-gray-800 to-gray-900 rounded-full mx-auto shadow-lg border border-gray-600"
        ></div>
      </div>
    </div>

    <!-- 投影光束 -->
    <div
      class="absolute left-10 lg:left-5 top-1/2 -translate-y-1/2 w-44 lg:w-52 h-24 z-20 pointer-events-none animate-pulse-slow"
    >
      <div
        class="absolute inset-0 animate-wave"
        style="clip-path: polygon(0 35%, 100% 0%, 100% 100%, 0 65%)"
      >
        <div
          class="absolute inset-0 bg-gradient-to-r from-cyan-400/50 via-blue-400/25 to-blue-400/5 blur-sm"
        ></div>
      </div>
      <div
        class="absolute left-0 top-1/2 -translate-y-1/2 w-40 h-12 bg-gradient-to-r from-blue-400/20 via-blue-400/10 to-transparent blur-xl animate-wave"
      ></div>
      <div
        class="absolute left-6 top-1/2 -translate-y-1/2 w-1.5 h-1.5 bg-cyan-300 rounded-full blur-sm animate-pulse"
      ></div>
      <div
        class="absolute left-14 top-1/3 w-1 h-1 bg-blue-300 rounded-full blur-sm animate-pulse"
        style="animation-delay: 0.2s"
      ></div>
      <div
        class="absolute left-24 bottom-1/3 w-1.2 h-1.2 bg-cyan-200 rounded-full blur-sm animate-pulse"
        style="animation-delay: 0.4s"
      ></div>
      <div
        class="absolute left-32 top-1/3 w-0.8 h-0.8 bg-blue-200 rounded-full blur-sm animate-pulse"
        style="animation-delay: 0.6s"
      ></div>
      <div
        class="absolute left-40 bottom-1/3 w-1 h-1 bg-cyan-100 rounded-full blur-sm animate-pulse"
        style="animation-delay: 0.8s"
      ></div>
    </div>

    <!-- 投影屏幕 -->
    <Carousel :slides="slides" />

    <!-- 环境光效 -->
    <div
      class="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl"
    ></div>
    <div
      class="absolute bottom-0 left-20 w-24 h-24 bg-purple-500/10 rounded-full blur-3xl"
    ></div>
  </div>
</template>

<style scoped>
@keyframes wave {
  0%,
  100% {
    transform: scaleY(1) scaleX(1);
    opacity: 0.8;
  }
  25% {
    transform: scaleY(1.05) scaleX(1.02);
    opacity: 0.9;
  }
  50% {
    transform: scaleY(0.98) scaleX(0.99);
    opacity: 0.85;
  }
  75% {
    transform: scaleY(1.03) scaleX(1.01);
    opacity: 0.9;
  }
}

@keyframes pulse-slow {
  0%,
  100% {
    opacity: 0.7;
  }
  50% {
    opacity: 0.9;
  }
}

.animate-wave {
  animation: wave 3s ease-in-out infinite;
}

.animate-pulse-slow {
  animation: pulse-slow 4s ease-in-out infinite;
}
</style>
