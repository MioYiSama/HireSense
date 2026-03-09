<!-- 轮播图组件 -->
<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";

interface Slide {
  icon: string;
  title: string;
  description: string;
  gradient: string;
}

const props = defineProps<{
  slides: Slide[];
}>();

const currentSlide = ref(0);
let slideInterval: number | null = null;

const nextSlide = () => {
  currentSlide.value = (currentSlide.value + 1) % props.slides.length;
};

const prevSlide = () => {
  currentSlide.value =
    (currentSlide.value - 1 + props.slides.length) % props.slides.length;
};

const goToSlide = (index: number) => {
  currentSlide.value = index;
};

const startAutoPlay = () => {
  slideInterval = window.setInterval(nextSlide, 3000);
};

const stopAutoPlay = () => {
  if (slideInterval) {
    clearInterval(slideInterval);
    slideInterval = null;
  }
};

onMounted(() => {
  startAutoPlay();
});

onUnmounted(() => {
  stopAutoPlay();
});
</script>

<template>
  <div
    class="relative ml-32"
    @mouseenter="stopAutoPlay"
    @mouseleave="startAutoPlay"
  >
    <div
      class="relative"
      style="perspective: 1200px; transform-style: preserve-3d"
    >
      <div
        class="relative bg-gray-900/40 backdrop-blur-md border-2 border-cyan-400/40 rounded-xl overflow-hidden shadow-2xl shadow-blue-500/20"
        style="transform: rotateY(-12deg) rotateX(3deg) skewX(-3deg)"
      >
        <div
          class="relative aspect-[4/3] overflow-hidden"
          style="clip-path: polygon(5% 0%, 100% 0%, 95% 100%, 0% 100%)"
        >
          <div
            v-for="(slide, index) in slides"
            :key="index"
            :class="[
              'absolute inset-0 transition-all duration-1000 ease-in-out',
              currentSlide === index
                ? 'opacity-100 scale-100'
                : 'opacity-0 scale-110',
            ]"
          >
            <div
              :class="[
                'w-full h-full flex flex-col items-center justify-center relative overflow-hidden',
                slide.gradient,
              ]"
              style="clip-path: polygon(5% 0%, 100% 0%, 95% 100%, 0% 100%)"
            >
              <div
                class="absolute inset-0 bg-gradient-to-br from-white/10 via-transparent to-transparent"
              ></div>
              <div
                class="absolute top-0 left-0 w-full h-full bg-[radial-gradient(ellipse_at_20%_20%,rgba(255,255,255,0.15),transparent_60%)]"
              ></div>
              <div
                class="absolute inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(255,255,255,0.03)_2px,rgba(255,255,255,0.03)_4px)] pointer-events-none"
              ></div>

              <svg
                v-if="slide.icon === 'brain'"
                class="w-14 h-14 text-cyan-300 mb-3 relative z-10 drop-shadow-[0_0_10px_rgba(103,232,249,0.5)]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
              <svg
                v-else-if="slide.icon === 'mic'"
                class="w-14 h-14 text-cyan-300 mb-3 relative z-10 drop-shadow-[0_0_10px_rgba(103,232,249,0.5)]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                />
              </svg>
              <svg
                v-else-if="slide.icon === 'code'"
                class="w-14 h-14 text-cyan-300 mb-3 relative z-10 drop-shadow-[0_0_10px_rgba(103,232,249,0.5)]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
                />
              </svg>
              <svg
                v-else-if="slide.icon === 'trending-up'"
                class="w-14 h-14 text-cyan-300 mb-3 relative z-10 drop-shadow-[0_0_10px_rgba(103,232,249,0.5)]"
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

              <h3
                class="text-lg font-bold text-white mb-2 relative z-10 drop-shadow-md"
              >
                {{ slide.title }}
              </h3>
              <p
                class="text-gray-200 text-center text-xs max-w-[200px] relative z-10 leading-relaxed"
              >
                {{ slide.description }}
              </p>
            </div>
          </div>
        </div>

        <div
          class="absolute inset-0 bg-gradient-to-br from-white/15 via-transparent to-transparent pointer-events-none"
          style="clip-path: polygon(5% 0%, 100% 0%, 95% 100%, 0% 100%)"
        ></div>

        <div
          class="absolute inset-0 border border-cyan-300/20 rounded-xl pointer-events-none"
          style="clip-path: polygon(5% 0%, 100% 0%, 95% 100%, 0% 100%)"
        ></div>
      </div>

      <div
        class="absolute -bottom-6 left-8 right-0 h-6 bg-black/40 blur-2xl rounded-full"
        style="transform: rotateY(-12deg) rotateX(3deg)"
      ></div>

      <div
        class="absolute top-0 -right-2 w-2 h-full bg-gray-800/60 rounded-r-lg"
        style="transform: rotateY(90deg) translateZ(-10px)"
      ></div>
    </div>

    <div
      class="flex items-center justify-center mt-6 space-x-4 transform -skew-x-6"
    >
      <button
        @click="prevSlide"
        class="w-8 h-8 rounded-full bg-gray-800/50 hover:bg-gray-700/50 border border-gray-600 flex items-center justify-center transition-all duration-300 hover:scale-110"
      >
        <svg
          class="w-4 h-4 text-blue-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 19l-7-7 7-7"
          />
        </svg>
      </button>

      <div class="flex space-x-2">
        <button
          v-for="(_, index) in slides"
          :key="index"
          @click="goToSlide(index)"
          :class="[
            'h-2 rounded-full transition-all duration-500',
            currentSlide === index
              ? 'bg-blue-400 w-6'
              : 'bg-gray-600 w-2 hover:bg-gray-500',
          ]"
        />
      </div>

      <button
        @click="nextSlide"
        class="w-8 h-8 rounded-full bg-gray-800/50 hover:bg-gray-700/50 border border-gray-600 flex items-center justify-center transition-all duration-300 hover:scale-110"
      >
        <svg
          class="w-4 h-4 text-blue-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 5l7 7-7 7"
          />
        </svg>
      </button>
    </div>
  </div>
</template>
