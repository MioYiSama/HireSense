<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import LucideLogIn from "~icons/lucide/log-in";
import LucideUserPlus from "~icons/lucide/user-plus";
import LucideBrain from "~icons/lucide/brain";
import LucideBarChart3 from "~icons/lucide/bar-chart-3";
import LucideSchool from "~icons/lucide/school";
import LucideBriefcase from "~icons/lucide/briefcase";
import LucideUsers from "~icons/lucide/users";
import LucideBot from "~icons/lucide/bot";
import LucideGauge from "~icons/lucide/gauge";
import LucideBarChart from "~icons/lucide/bar-chart";
import LucideArrowRight from "~icons/lucide/arrow-right";
import InteractiveTerminal from "../components/InteractiveTerminal.vue";

// 常量定义
const TYPING_DELAY = 50;
const TYPING_TEXT_SWITCH_DELAY = 2000;

const router = useRouter();
const scrolled = ref(false);
const activeSection = ref("hero");
const expandedCards = ref([false, false, false]);
const typingText = ref("");
let animationStyle: HTMLStyleElement | null = null;
let typingInterval: number | null = null;
const typingTexts: string[] = [
  "请解释 Vue 3 的响应式原理？",
  "如何设计一个高并发抢购系统？",
  "描述一下你遇到的最难的技术挑战？",
];
let currentTextIndex: number = 0;
let currentCharIndex: number = 0;

// 产品优势区域状态
const activeAdvantage = ref(0);
const advantageItems = [
  {
    id: "ai-question",
    title: "AI 智能提问",
    subtitle: "模拟真实面试场景",
    icon: LucideBot,
  },
  {
    id: "realtime-score",
    title: "面试评估复盘",
    subtitle: "及时反馈调整状态",
    icon: LucideGauge,
  },
  {
    id: "data-viz",
    title: "数据可视化",
    subtitle: "直观了解优劣势",
    icon: LucideBarChart,
  },
];

onMounted(() => {
  window.addEventListener("scroll", handleScroll);
  initAnimations();
  // 添加鼠标聚光灯效果
  document.addEventListener("mousemove", handleMouseMove);
});

onUnmounted(() => {
  window.removeEventListener("scroll", handleScroll);
  document.removeEventListener("mousemove", handleMouseMove);
  // 清理样式标签
  if (animationStyle && animationStyle.parentNode) {
    animationStyle.parentNode.removeChild(animationStyle);
  }
  // 清理打字机定时器
  if (typingInterval) {
    window.clearTimeout(typingInterval as number);
  }
});

const handleMouseMove = (e: MouseEvent) => {
  const spotlight = document.getElementById("cursor-spotlight");
  if (spotlight) {
    spotlight.style.background = `radial-gradient(circle 300px at ${e.clientX}px ${e.clientY}px, rgba(6, 182, 212, 0.15), transparent 80%)`;
  }
};

const handleScroll = () => {
  scrolled.value = window.scrollY > 50;
  updateActiveSection();
  checkScrollAnimations();
};

const updateActiveSection = () => {
  const sections = ["hero", "features", "advantages", "cases"];
  for (const section of sections) {
    const element = document.getElementById(section);
    if (element) {
      const rect = element.getBoundingClientRect();
      if (rect.top <= 100 && rect.bottom >= 100) {
        activeSection.value = section;
        break;
      }
    }
  }
};

const checkScrollAnimations = () => {
  const animatedElements = document.querySelectorAll(".animate-on-scroll");
  animatedElements.forEach((element) => {
    const rect = element.getBoundingClientRect();
    if (rect.top <= window.innerHeight - 100) {
      element.classList.add("animate-fade-in");
    }
  });
};

const initAnimations = () => {
  // 初始化动画类
  animationStyle = document.createElement("style");
  animationStyle.textContent = `
    .animate-on-scroll {
      opacity: 0;
      transform: translateY(20px);
      transition: opacity 0.5s ease, transform 0.5s ease;
    }
    .animate-fade-in {
      opacity: 1;
      transform: translateY(0);
    }
    .card-hover {
      transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .card-hover:hover {
      transform: translateY(-5px);
      box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.3);
    }
    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    .btn-primary:active {
      transform: translateY(0);
    }
    /* 鼠标聚光灯 */
    #cursor-spotlight {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 9999;
    }
    /* 浮动动画 */
    @keyframes float {
      0%,
      100% {
        transform: translateY(0px) rotateX(10deg) rotateY(-5deg);
      }
      50% {
        transform: translateY(-20px) rotateX(10deg) rotateY(-5deg);
      }
    }
    .float-animation {
      animation: float 6s ease-in-out infinite;
      transform-style: preserve-3d;
      perspective: 1000px;
    }
    /* 按钮光效 */
    .btn-shine {
      position: relative;
      overflow: hidden;
    }
    .btn-shine::after {
      content: "";
      position: absolute;
      top: -50%;
      left: -50%;
      width: 200%;
      height: 200%;
      background: linear-gradient(
        to right,
        transparent,
        rgba(255, 255, 255, 0.3),
        transparent
      );
      transform: rotate(45deg) translateX(-100%);
      transition: transform 0.6s;
    }
    .btn-shine:hover::after {
      transform: rotate(45deg) translateX(100%);
    }
    /* 渐变边框 */
    .border-gradient {
      position: relative;
      background: linear-gradient(
        120deg,
        rgba(59, 130, 246, 0.2),
        rgba(168, 85, 247, 0.2)
      );
      border-radius: 24px;
    }
    .border-gradient::before {
      content: "";
      position: absolute;
      inset: 0;
      border-radius: 24px;
      padding: 1px;
      background: linear-gradient(
        120deg,
        rgba(59, 130, 246, 0.5),
        rgba(168, 85, 247, 0.5)
      );
      -webkit-mask:
        linear-gradient(#fff 0 0) content-box,
        linear-gradient(#fff 0 0);
      mask:
        linear-gradient(#fff 0 0) content-box,
        linear-gradient(#fff 0 0);
      -webkit-mask-composite: xor;
      mask-composite: exclude;
      pointer-events: none;
      transform: translateZ(0);
    }
    /* 玻璃效果 */
    .glass {
      background: rgba(10, 10, 20, 0.7);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.1);
    }
    /* 卡片展开 */
    .card-expand-content {
      max-height: 0;
      overflow: hidden;
      transition:
        max-height 0.5s ease,
        padding 0.5s ease;
    }
    .card-expand-content.open {
      max-height: 500px;
      padding-top: 1rem;
    }
    /* 雷达图动画 */
    @keyframes radar-pulse {
      0%, 100% {
        opacity: 0.8;
      }
      50% {
        opacity: 1;
      }
    }
    .radar-animate {
      animation: radar-pulse 2s ease-in-out infinite;
    }
    /* 产品优势区域样式 */
    .hud-content {
      animation: content-fade-in 0.4s ease-out;
    }
    @keyframes content-fade-in {
      from {
        opacity: 0;
        transform: translateY(10px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
    /* 控制按钮激活状态 */
    .advantage-btn-active {
      background: rgba(6, 182, 212, 0.1) !important;
      border-color: rgba(6, 182, 212, 0.5) !important;
      box-shadow: 0 0 20px rgba(6, 182, 212, 0.15) !important;
    }
    /* HUD 屏幕光效 */
    .hud-screen-glow {
      box-shadow: 
        0 0 40px rgba(6, 182, 212, 0.1),
        inset 0 0 40px rgba(6, 182, 212, 0.02);
    }
    /* HUD 角落装饰 */
    .hud-corner {
      position: absolute;
      width: 16px;
      height: 16px;
      border-color: rgba(6, 182, 212, 0.5);
    }
    .hud-corner-tl {
      top: 0;
      left: 0;
      border-top: 2px solid;
      border-left: 2px solid;
      border-top-left-radius: 8px;
    }
    .hud-corner-tr {
      top: 0;
      right: 0;
      border-top: 2px solid;
      border-right: 2px solid;
      border-top-right-radius: 8px;
    }
    .hud-corner-bl {
      bottom: 0;
      left: 0;
      border-bottom: 2px solid;
      border-left: 2px solid;
      border-bottom-left-radius: 8px;
    }
    .hud-corner-br {
      bottom: 0;
      right: 0;
      border-bottom: 2px solid;
      border-right: 2px solid;
      border-bottom-right-radius: 8px;
    }
    /* 场景案例 3D 透视卡片效果 */
    .perspective-container {
      perspective: 1000px;
    }
    .case-card-3d {
      transform-style: preserve-3d !important;
      transition: transform 0.5s ease, box-shadow 0.5s ease !important;
    }
    .case-card-3d:hover {
      transform: rotateY(-5deg) rotateX(5deg) translateZ(20px) !important;
      box-shadow: -20px 20px 50px rgba(0, 0, 0, 0.5) !important;
    }
    /* 滚动指示器动画 */
    @keyframes scroll-indicator {
      0%, 100% {
        transform: translateY(0);
        opacity: 1;
      }
      50% {
        transform: translateY(8px);
        opacity: 0.5;
      }
    }
    .animate-scroll-indicator {
      animation: scroll-indicator 1.5s ease-in-out infinite;
    }
  `;
  document.head.appendChild(animationStyle);
};

const goToSignin = () => {
  router.push("/signin");
};

const goToSignup = () => {
  router.push("/signup");
};

const scrollToSection = (sectionId: string) => {
  const section = document.getElementById(sectionId);
  if (section) {
    section.scrollIntoView({ behavior: "smooth" });
  }
};

// 功能卡片展开/折叠
const toggleFeatureCard = (index: number) => {
  expandedCards.value[index] = !expandedCards.value[index];

  // 如果展开第一个卡片，启动打字机效果
  if (index === 0 && expandedCards.value[0]) {
    startTyping();
  } else if (index === 0 && !expandedCards.value[0]) {
    stopTyping();
  }
};

// 打字机效果
const startTyping = () => {
  typingText.value = "";
  currentTextIndex = 0;
  currentCharIndex = 0;
  typeNextChar();
};

const typeNextChar = () => {
  const currentText = typingTexts[currentTextIndex];

  if (!currentText) return;

  if (currentCharIndex < currentText.length) {
    typingText.value += currentText.charAt(currentCharIndex);
    currentCharIndex++;
    typingInterval = window.setTimeout(typeNextChar, TYPING_DELAY);
  } else {
    // 等待2秒后切换到下一个文本
    typingInterval = window.setTimeout(() => {
      typingText.value = "";
      currentCharIndex = 0;
      currentTextIndex = (currentTextIndex + 1) % typingTexts.length;
      typeNextChar();
    }, TYPING_TEXT_SWITCH_DELAY);
  }
};

const stopTyping = () => {
  if (typingInterval) {
    window.clearTimeout(typingInterval as number);
    typingInterval = null;
  }
};
</script>

<template>
  <div class="min-h-screen bg-[#020202] text-white">
    <!-- ========== 鼠标聚光灯 ========== -->
    <div id="cursor-spotlight"></div>

    <!-- ========== 导航栏 ========== -->
    <nav
      :class="[
        'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
        scrolled
          ? 'bg-gray-900/95 backdrop-blur-sm shadow-lg'
          : 'bg-transparent',
      ]"
    >
      <div class="container mx-auto px-6 py-4 max-w-7xl">
        <div class="flex items-center justify-between">
          <!-- Logo -->
          <div
            class="flex items-center gap-3 group cursor-pointer"
            @click="scrollToSection('hero')"
          >
            <img
              src="/favicon.png"
              alt="HireSense Logo"
              class="w-10 h-10 rounded-xl transition-transform group-hover:scale-110 duration-300"
            />
            <span class="text-2xl font-bold text-white">
              Hire<span
                class="bg-clip-text text-transparent bg-linear-to-r from-blue-400 to-purple-500"
                >Sense</span
              >
            </span>
          </div>

          <!-- 导航链接 -->
          <div
            class="hidden md:flex items-center gap-8 ml-auto mr-8 relative z-10"
          >
            <button
              @click="scrollToSection('features')"
              class="text-sm text-gray-400 hover:text-white transition-colors relative group"
              :class="activeSection === 'features' ? 'text-white' : ''"
            >
              核心功能
              <span
                :class="[
                  'absolute -bottom-1 left-0 h-0.5 bg-blue-400 transition-all duration-300',
                  activeSection === 'features'
                    ? 'w-full'
                    : 'w-0 group-hover:w-full',
                ]"
              ></span>
            </button>
            <button
              @click="scrollToSection('advantages')"
              class="text-sm text-gray-400 hover:text-white transition-colors relative group"
              :class="activeSection === 'advantages' ? 'text-white' : ''"
            >
              产品优势
              <span
                :class="[
                  'absolute -bottom-1 left-0 h-0.5 bg-blue-400 transition-all duration-300',
                  activeSection === 'advantages'
                    ? 'w-full'
                    : 'w-0 group-hover:w-full',
                ]"
              ></span>
            </button>
            <button
              @click="scrollToSection('cases')"
              class="text-sm text-gray-400 hover:text-white transition-colors relative group"
              :class="activeSection === 'cases' ? 'text-white' : ''"
            >
              场景案例
              <span
                :class="[
                  'absolute -bottom-1 left-0 h-0.5 bg-blue-400 transition-all duration-300',
                  activeSection === 'cases'
                    ? 'w-full'
                    : 'w-0 group-hover:w-full',
                ]"
              ></span>
            </button>
          </div>

          <!-- 登录注册按钮 -->
          <div class="flex items-center gap-4 relative z-10">
            <button
              @click="goToSignin"
              class="hidden sm:flex items-center gap-2 px-5 py-2 text-sm text-gray-300 hover:text-white transition-colors cursor-pointer"
            >
              <LucideLogIn class="w-4 h-4" />
              登录
            </button>
            <button
              @click="goToSignup"
              class="flex items-center gap-2 px-6 py-2.5 bg-white text-black text-sm font-semibold rounded-full hover:bg-gray-200 transition-colors btn-shine cursor-pointer"
            >
              <LucideUserPlus class="w-4 h-4" />
              免费注册
            </button>
          </div>
        </div>
      </div>
    </nav>

    <!-- ========== Hero 区域 ========== -->
    <section id="hero" class="relative min-h-screen flex items-center">
      <!-- 背景 -->
      <div class="absolute inset-0 bg-[#020202]"></div>
      <div
        class="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(59,130,246,0.1),transparent_70%)]"
      ></div>

      <!-- 背景装饰 -->
      <div class="fixed inset-0 pointer-events-none overflow-hidden">
        <div
          class="absolute top-0 left-1/4 w-[600px] h-[600px] bg-blue-500/10 rounded-full filter blur-[120px] animate-pulse-slow"
        ></div>
        <div
          class="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-purple-500/10 rounded-full filter blur-[120px] animate-pulse-slow"
          style="animation-delay: 2s"
        ></div>
      </div>

      <div class="container mx-auto px-6 py-24 relative z-10 max-w-7xl">
        <div class="flex flex-col md:flex-row items-center gap-12">
          <!-- 左侧文字 -->
          <div class="md:w-1/2 mb-12 md:mb-0">
            <div
              class="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-white/10 bg-white/5 mb-6"
            >
              <span
                class="w-2 h-2 rounded-full bg-green-400 animate-pulse"
              ></span>
              <span class="text-xs text-gray-400">AI 驱动的模拟面试平台</span>
            </div>
            <h1 class="text-5xl md:text-7xl font-bold leading-tight mb-6">
              <span class="text-white">重新定义</span><br />
              <span
                class="bg-clip-text text-transparent bg-linear-to-r from-blue-400 to-purple-500"
                >智能面试</span
              >
            </h1>
            <p class="text-lg text-gray-400 mb-8 max-w-xl">
              HireSense知聘
              利用先进的大模型技术，为求职者提供精准、高效的智能面试模拟，让每一次面试都成为成功的机会。
            </p>
            <div class="flex flex-col sm:flex-row gap-4">
              <button
                @click="goToSignup"
                class="px-8 py-4 bg-linear-to-r from-blue-500 to-purple-500 text-white font-semibold rounded-full hover:opacity-90 transition-opacity btn-shine flex items-center justify-center gap-2 cursor-pointer"
              >
                <span>立即开始</span>
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M17 8l4 4m0 0l-4 4m4-4H3"
                  />
                </svg>
              </button>
              <button
                @click="scrollToSection('features')"
                class="px-8 py-4 border border-white/20 text-white font-medium rounded-full hover:bg-white/5 transition-colors flex items-center justify-center gap-2 cursor-pointer"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
                <span>了解更多</span>
              </button>
            </div>
          </div>

          <!-- 右侧展示区  -->
          <div
            class="md:w-1/2 relative h-[500px] flex items-center justify-center"
          >
            <div
              class="absolute inset-0 flex items-center justify-center pointer-events-none"
            >
              <div
                class="w-80 h-80 bg-blue-500/20 rounded-full filter blur-[80px]"
              ></div>
            </div>
            <InteractiveTerminal />
          </div>
        </div>
      </div>

      <!-- ========== 滚动提示 ========== -->
      <div
        class="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-3"
      >
        <span class="text-xs text-gray-500 tracking-widest uppercase"
          >Scroll to explore</span
        >
        <div
          class="w-10 h-16 rounded-full border-2 border-gray-600 flex items-start justify-center p-2 group hover:border-cyan-500/50 transition-colors duration-300"
        >
          <div
            class="w-1.5 h-3 bg-gray-500 rounded-full group-hover:bg-cyan-400 transition-colors duration-300 animate-scroll-indicator"
          ></div>
        </div>
      </div>
    </section>

    <!-- ========== 核心功能区 ========== -->
    <section id="features" class="py-20 bg-gray-900">
      <div class="container mx-auto px-6 max-w-7xl">
        <div class="text-center mb-16 animate-on-scroll">
          <h2 class="text-4xl font-bold mb-4">
            <span
              class="bg-clip-text text-transparent bg-linear-to-r from-blue-400 to-purple-500"
              >核心功能</span
            >
          </h2>
          <p class="text-xl text-gray-400 max-w-3xl mx-auto">
            全方位智能面试解决方案，覆盖招聘全流程
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <!-- 功能卡片 1 - 可展开 -->
          <div
            class="border-gradient p-8 rounded-3xl bg-gray-900/50 group cursor-pointer animate-on-scroll"
            @click="toggleFeatureCard(0)"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-4">
                <div
                  class="w-14 h-14 rounded-2xl bg-linear-to-br from-blue-500/20 to-blue-500/5 flex items-center justify-center group-hover:scale-110 transition-transform"
                >
                  <LucideBrain class="w-7 h-7 text-blue-400" />
                </div>
                <h3 class="text-xl font-semibold text-white">AI 智能发问</h3>
              </div>
              <svg
                :class="[
                  'w-5 h-5 text-gray-500 group-hover:text-white transition-all duration-300',
                  expandedCards[0] ? 'rotate-180' : '',
                ]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </div>
            <p class="text-gray-400 text-sm leading-relaxed mt-4">
              基于岗位 JD 自动生成针对性问题，支持深度追问。
            </p>
            <div
              :class="['card-expand-content', expandedCards[0] ? 'open' : '']"
            >
              <div class="pt-4 border-t border-white/5 mt-4">
                <p class="text-xs text-gray-500 mb-2">实时演示：</p>
                <div
                  class="font-mono text-xs text-green-400 bg-black/30 p-3 rounded-lg"
                >
                  <span>{{ typingText }}</span
                  ><span class="animate-pulse">|</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 功能卡片 2 - 可展开 -->
          <div
            class="border-gradient p-8 rounded-3xl bg-gray-900/50 group cursor-pointer animate-on-scroll"
            @click="toggleFeatureCard(1)"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-4">
                <div
                  class="w-14 h-14 rounded-2xl bg-linear-to-br from-purple-500/20 to-purple-500/5 flex items-center justify-center group-hover:scale-110 transition-transform"
                >
                  <LucideBarChart3 class="w-7 h-7 text-purple-400" />
                </div>
                <h3 class="text-xl font-semibold text-white">多维能力画像</h3>
              </div>
              <svg
                :class="[
                  'w-5 h-5 text-gray-500 group-hover:text-white transition-all duration-300',
                  expandedCards[1] ? 'rotate-180' : '',
                ]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </div>
            <p class="text-gray-400 text-sm leading-relaxed mt-4">
              自动生成雷达图能力分析，涵盖 12 个维度。
            </p>
            <div
              :class="['card-expand-content', expandedCards[1] ? 'open' : '']"
            >
              <div
                class="pt-4 border-t border-white/5 mt-4 flex justify-center"
              >
                <svg width="120" height="100" viewBox="0 0 120 100">
                  <polygon
                    points="60,10 100,35 100,75 60,90 20,75 20,35"
                    fill="none"
                    stroke="rgba(255,255,255,0.1)"
                    stroke-width="1"
                  />
                  <polygon
                    class="radar-animate"
                    points="60,20 85,40 90,70 60,80 30,65 35,40"
                    fill="rgba(168,85,247,0.2)"
                    stroke="#a855f7"
                    stroke-width="2"
                  />
                </svg>
              </div>
            </div>
          </div>

          <!-- 功能卡片 3 - 可展开 -->
          <div
            class="border-gradient p-8 rounded-3xl bg-gray-900/50 group cursor-pointer animate-on-scroll"
            @click="toggleFeatureCard(2)"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-4">
                <div
                  class="w-14 h-14 rounded-2xl bg-linear-to-br from-blue-500/20 to-blue-500/5 flex items-center justify-center group-hover:scale-110 transition-transform"
                >
                  <svg
                    class="w-7 h-7 text-blue-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                </div>
                <h3 class="text-xl font-semibold text-white">简历智能解析</h3>
              </div>
              <svg
                :class="[
                  'w-5 h-5 text-gray-500 group-hover:text-white transition-all duration-300',
                  expandedCards[2] ? 'rotate-180' : '',
                ]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </div>
            <p class="text-gray-400 text-sm leading-relaxed mt-4">
              一键解析简历关键信息，自动提取技能标签。
            </p>
            <div
              :class="['card-expand-content', expandedCards[2] ? 'open' : '']"
            >
              <div class="pt-4 border-t border-white/5 mt-4">
                <div class="flex gap-2 flex-wrap">
                  <span
                    class="px-2 py-1 rounded bg-blue-500/20 text-blue-400 text-xs"
                    >Vue.js</span
                  >
                  <span
                    class="px-2 py-1 rounded bg-green-500/20 text-green-400 text-xs"
                    >Node.js</span
                  >
                  <span
                    class="px-2 py-1 rounded bg-purple-500/20 text-purple-400 text-xs"
                    >AI</span
                  >
                  <span
                    class="px-2 py-1 rounded bg-orange-500/20 text-orange-400 text-xs"
                    >3年经验</span
                  >
                </div>
              </div>
            </div>
          </div>

          <!-- 其他卡片保持简洁 -->
          <div
            class="border-gradient p-8 rounded-3xl bg-gray-900/50 group animate-on-scroll"
          >
            <div
              class="w-14 h-14 rounded-2xl bg-linear-to-br from-green-500/20 to-green-500/5 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform"
            >
              <svg
                class="w-7 h-7 text-green-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <h3 class="text-xl font-semibold text-white mb-3">实时反馈报告</h3>
            <p class="text-gray-400 text-sm leading-relaxed">
              面试结束即时生成详细报告，包含改进建议。
            </p>
          </div>

          <div
            class="border-gradient p-8 rounded-3xl bg-gray-900/50 group animate-on-scroll"
          >
            <div
              class="w-14 h-14 rounded-2xl bg-linear-to-br from-orange-500/20 to-orange-500/5 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform"
            >
              <svg
                class="w-7 h-7 text-orange-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
                />
              </svg>
            </div>
            <h3 class="text-xl font-semibold text-white mb-3">面试官定制</h3>
            <p class="text-gray-400 text-sm leading-relaxed">
              支持选择不同风格的 AI 面试官，满足不同需求。
            </p>
          </div>

          <div
            class="border-gradient p-8 rounded-3xl bg-gray-900/50 group animate-on-scroll"
          >
            <div
              class="w-14 h-14 rounded-2xl bg-linear-to-br from-pink-500/20 to-pink-500/5 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform"
            >
              <svg
                class="w-7 h-7 text-pink-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h3 class="text-xl font-semibold text-white mb-3">历史记录追溯</h3>
            <p class="text-gray-400 text-sm leading-relaxed">
              完整保存每次面试记录，支持回放复盘。
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- ========== 产品优势区  ========== -->
    <section id="advantages" class="py-20 bg-gray-900 relative overflow-hidden">
      <!-- 背景渐变装饰 -->
      <div
        class="absolute top-0 right-0 w-[500px] h-[500px] bg-purple-500/5 rounded-full filter blur-[120px] pointer-events-none"
      ></div>
      <div
        class="absolute bottom-0 left-0 w-[400px] h-[400px] bg-blue-500/5 rounded-full filter blur-[120px] pointer-events-none"
      ></div>

      <div class="container mx-auto px-6 max-w-7xl relative z-10">
        <div class="text-center mb-16 animate-on-scroll">
          <h2 class="text-4xl font-bold mb-4">
            <span
              class="bg-clip-text text-transparent bg-linear-to-r from-blue-400 to-purple-500"
              >产品优势</span
            >
          </h2>
          <p class="text-xl text-gray-400 max-w-3xl mx-auto">
            相比传统面试准备方式，HireSense 提供革命性的体验
          </p>
        </div>

        <div class="grid lg:grid-cols-12 gap-8 items-center">
          <!-- 左侧控制面板 -->
          <div class="lg:col-span-4 space-y-4">
            <div
              v-for="(item, index) in advantageItems"
              :key="item.id"
              :class="[
                'border-gradient p-6 rounded-3xl bg-gray-900/50 cursor-pointer transition-all duration-300 group',
                activeAdvantage === index ? 'advantage-btn-active' : '',
              ]"
              @click="activeAdvantage = index"
            >
              <div class="flex items-center gap-4">
                <div
                  :class="[
                    'w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-300 group-hover:scale-110',
                    activeAdvantage === index
                      ? 'bg-cyan-500/20'
                      : 'bg-linear-to-br from-blue-500/20 to-blue-500/5',
                  ]"
                >
                  <component
                    :is="item.icon"
                    :class="[
                      'w-7 h-7 transition-colors duration-300',
                      activeAdvantage === index
                        ? 'text-cyan-400'
                        : 'text-blue-400',
                    ]"
                  />
                </div>
                <div>
                  <h3
                    :class="[
                      'text-xl font-semibold transition-colors duration-300',
                      activeAdvantage === index
                        ? 'text-cyan-300'
                        : 'text-white',
                    ]"
                  >
                    {{ item.title }}
                  </h3>
                  <p class="text-sm text-gray-400 mt-1">{{ item.subtitle }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 右侧 HUD 展示屏 -->
          <div class="lg:col-span-8">
            <div
              class="border-gradient p-8 rounded-3xl bg-gray-900/50 min-h-[400px] relative overflow-hidden hud-screen-glow"
            >
              <!-- HUD 角落装饰 -->
              <div class="hud-corner hud-corner-tl"></div>
              <div class="hud-corner hud-corner-tr"></div>
              <div class="hud-corner hud-corner-bl"></div>
              <div class="hud-corner hud-corner-br"></div>

              <!-- 内容区域 1: AI 提问 -->
              <div
                v-show="activeAdvantage === 0"
                class="hud-content flex flex-col h-full justify-center"
              >
                <p class="text-xs text-blue-400 mb-2 tracking-widest uppercase">
                  System Analysis // Mode_01
                </p>
                <h3 class="text-2xl font-bold text-white mb-6">
                  基于背景生成定制问题
                </h3>
                <div class="space-y-4">
                  <div class="flex items-start gap-3">
                    <div
                      class="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center shrink-0 mt-1"
                    >
                      <LucideBot class="w-4 h-4 text-white" />
                    </div>
                    <div class="glass p-4 rounded-xl rounded-tl-none flex-1">
                      <p class="text-gray-300 text-sm">
                        看到你的简历里有微服务重构经验，能具体聊聊服务拆分的粒度是如何权衡的吗？
                      </p>
                    </div>
                  </div>
                  <div class="flex items-start gap-3 justify-end">
                    <div
                      class="bg-white/5 p-4 rounded-xl rounded-tr-none flex-1 max-w-md border border-white/10"
                    >
                      <p class="text-gray-300 text-sm">
                        我们主要依据业务边界和团队规模...
                      </p>
                      <span
                        class="inline-block w-0.5 h-4 bg-blue-400 ml-1 animate-pulse"
                      ></span>
                    </div>
                    <div
                      class="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center shrink-0 mt-1"
                    >
                      <span class="text-xs text-white">U</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 内容区域 2: 实时评分 -->
              <div
                v-show="activeAdvantage === 1"
                class="hud-content flex flex-col h-full justify-center items-center"
              >
                <p
                  class="text-xs text-purple-400 mb-2 tracking-widest uppercase"
                >
                  Real-time Feedback // Mode_02
                </p>
                <h3 class="text-2xl font-bold text-white mb-8 text-center">
                  面试之后快速评估
                </h3>
                <div class="flex items-center gap-12">
                  <div class="relative w-40 h-40">
                    <svg
                      class="w-full h-full transform -rotate-90"
                      viewBox="0 0 100 100"
                    >
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        stroke="rgba(255,255,255,0.1)"
                        stroke-width="8"
                        fill="none"
                      />
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        stroke="url(#scoreGrad)"
                        stroke-width="8"
                        fill="none"
                        stroke-dasharray="251.2"
                        stroke-dashoffset="50"
                        stroke-linecap="round"
                      />
                      <defs>
                        <linearGradient
                          id="scoreGrad"
                          x1="0%"
                          y1="0%"
                          x2="100%"
                          y2="0%"
                        >
                          <stop offset="0%" stop-color="#a855f7" />
                          <stop offset="100%" stop-color="#06b6d4" />
                        </linearGradient>
                      </defs>
                    </svg>
                    <div
                      class="absolute inset-0 flex flex-col items-center justify-center"
                    >
                      <span class="text-4xl font-bold text-white">85</span>
                      <span class="text-xs text-gray-400">当前得分</span>
                    </div>
                  </div>
                  <div class="space-y-4 w-48">
                    <div>
                      <div class="flex justify-between text-sm mb-1">
                        <span class="text-gray-400">逻辑性</span>
                        <span class="text-white">92</span>
                      </div>
                      <div class="h-2 bg-white/10 rounded-full overflow-hidden">
                        <div
                          class="h-full bg-blue-400 rounded-full transition-all duration-1000"
                          style="width: 92%"
                        ></div>
                      </div>
                    </div>
                    <div>
                      <div class="flex justify-between text-sm mb-1">
                        <span class="text-gray-400">深度</span>
                        <span class="text-white">88</span>
                      </div>
                      <div class="h-2 bg-white/10 rounded-full overflow-hidden">
                        <div
                          class="h-full bg-purple-400 rounded-full transition-all duration-1000"
                          style="width: 88%"
                        ></div>
                      </div>
                    </div>
                    <div>
                      <div class="flex justify-between text-sm mb-1">
                        <span class="text-gray-400">表达</span>
                        <span class="text-white">75</span>
                      </div>
                      <div class="h-2 bg-white/10 rounded-full overflow-hidden">
                        <div
                          class="h-full bg-blue-500 rounded-full transition-all duration-1000"
                          style="width: 75%"
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 内容区域 3: 数据可视化 -->
              <div
                v-show="activeAdvantage === 2"
                class="hud-content flex flex-col h-full justify-center items-center"
              >
                <p class="text-xs text-blue-400 mb-2 tracking-widest uppercase">
                  Data Visualization // Mode_03
                </p>
                <h3 class="text-2xl font-bold text-white mb-8 text-center">
                  能力维度一目了然
                </h3>
                <div class="relative w-64 h-64">
                  <svg width="100%" height="100%" viewBox="0 0 300 300">
                    <!-- 背景网格 -->
                    <polygon
                      points="150,30 270,90 270,210 150,270 30,210 30,90"
                      fill="none"
                      stroke="rgba(255,255,255,0.05)"
                      stroke-width="1"
                    />
                    <polygon
                      points="150,60 240,105 240,195 150,240 60,195 60,105"
                      fill="none"
                      stroke="rgba(255,255,255,0.05)"
                      stroke-width="1"
                    />
                    <polygon
                      points="150,90 210,120 210,180 150,210 90,180 90,120"
                      fill="none"
                      stroke="rgba(255,255,255,0.05)"
                      stroke-width="1"
                    />
                    <!-- 数据区域 -->
                    <polygon
                      points="150,40 260,95 250,200 150,250 50,190 60,100"
                      fill="rgba(6,182,212,0.2)"
                      stroke="#06b6d4"
                      stroke-width="2"
                    />
                    <!-- 顶点 -->
                    <circle cx="150" cy="40" r="4" fill="#06b6d4" />
                    <circle cx="260" cy="95" r="4" fill="#06b6d4" />
                    <circle cx="250" cy="200" r="4" fill="#a855f7" />
                    <circle cx="150" cy="250" r="4" fill="#a855f7" />
                    <circle cx="50" cy="190" r="4" fill="#3b82f6" />
                    <circle cx="60" cy="100" r="4" fill="#3b82f6" />
                  </svg>
                  <!-- 标签 -->
                  <div
                    class="absolute top-0 left-1/2 -translate-x-1/2 text-xs text-gray-400"
                  >
                    技术深度
                  </div>
                  <div class="absolute top-1/4 right-0 text-xs text-gray-400">
                    沟通能力
                  </div>
                  <div
                    class="absolute bottom-1/4 right-0 text-xs text-gray-400"
                  >
                    系统设计
                  </div>
                  <div
                    class="absolute bottom-0 left-1/2 -translate-x-1/2 text-xs text-gray-400"
                  >
                    业务思维
                  </div>
                  <div class="absolute bottom-1/4 left-0 text-xs text-gray-400">
                    工程能力
                  </div>
                  <div class="absolute top-1/4 left-0 text-xs text-gray-400">
                    学习能力
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ========== 场景案例区  ========== -->
    <section id="cases" class="py-20 bg-gray-900 relative overflow-hidden">
      <!-- 背景渐变装饰 -->
      <div
        class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-cyan-500/5 rounded-full filter blur-[150px] pointer-events-none"
      ></div>

      <div class="container mx-auto px-6 max-w-7xl relative z-10">
        <div class="text-center mb-16 animate-on-scroll">
          <h2 class="text-4xl font-bold mb-4">
            <span
              class="bg-clip-text text-transparent bg-linear-to-r from-blue-400 to-purple-500"
              >场景案例</span
            >
          </h2>
          <p class="text-xl text-gray-400 max-w-3xl mx-auto">
            适用于多种面试场景，满足不同用户的需求
          </p>
        </div>

        <div
          class="perspective-container grid grid-cols-1 md:grid-cols-3 gap-8"
        >
          <!-- 场景案例 1 -->
          <div
            class="case-card-3d border-gradient p-8 rounded-3xl bg-gray-900/80 relative overflow-hidden group cursor-pointer animate-on-scroll"
          >
            <div
              class="absolute top-0 right-0 w-32 h-32 bg-cyan-500/10 rounded-full filter blur-2xl transform translate-x-10 -translate-y-10 group-hover:bg-cyan-500/20 transition-colors duration-500"
            ></div>
            <div class="relative z-10">
              <div
                class="w-16 h-16 rounded-2xl bg-linear-to-br from-cyan-500/20 to-transparent flex items-center justify-center mb-6 border border-cyan-500/20 group-hover:scale-110 transition-transform duration-300"
              >
                <LucideSchool class="w-8 h-8 text-cyan-400" />
              </div>
              <h3 class="text-xl font-semibold text-white mb-3">企业校招</h3>
              <p class="text-gray-400 text-sm leading-relaxed mb-6">
                帮助应届毕业生准备校招面试，熟悉企业招聘流程和常见问题，提升求职竞争力。
              </p>
              <div
                class="flex items-center gap-2 text-cyan-400 text-sm font-medium group-hover:translate-x-2 transition-transform duration-300"
              >
                <span>开始准备</span>
                <LucideArrowRight class="w-4 h-4" />
              </div>
            </div>
          </div>

          <!-- 场景案例 2 -->
          <div
            class="case-card-3d border-gradient p-8 rounded-3xl bg-gray-900/80 relative overflow-hidden group cursor-pointer animate-on-scroll"
          >
            <div
              class="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-full filter blur-2xl transform translate-x-10 -translate-y-10 group-hover:bg-purple-500/20 transition-colors duration-500"
            ></div>
            <div class="relative z-10">
              <div
                class="w-16 h-16 rounded-2xl bg-linear-to-br from-purple-500/20 to-transparent flex items-center justify-center mb-6 border border-purple-500/20 group-hover:scale-110 transition-transform duration-300"
              >
                <LucideBriefcase class="w-8 h-8 text-purple-400" />
              </div>
              <h3 class="text-xl font-semibold text-white mb-3">
                实习面试准备
              </h3>
              <p class="text-gray-400 text-sm leading-relaxed mb-6">
                为大学生提供实习面试模拟，提前熟悉面试流程，增加实习机会，为职业生涯打好基础。
              </p>
              <div
                class="flex items-center gap-2 text-purple-400 text-sm font-medium group-hover:translate-x-2 transition-transform duration-300"
              >
                <span>开始准备</span>
                <LucideArrowRight class="w-4 h-4" />
              </div>
            </div>
          </div>

          <!-- 场景案例 3 -->
          <div
            class="case-card-3d border-gradient p-8 rounded-3xl bg-gray-900/80 relative overflow-hidden group cursor-pointer animate-on-scroll"
          >
            <div
              class="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full filter blur-2xl transform translate-x-10 -translate-y-10 group-hover:bg-blue-500/20 transition-colors duration-500"
            ></div>
            <div class="relative z-10">
              <div
                class="w-16 h-16 rounded-2xl bg-linear-to-br from-blue-500/20 to-transparent flex items-center justify-center mb-6 border border-blue-500/20 group-hover:scale-110 transition-transform duration-300"
              >
                <LucideUsers class="w-8 h-8 text-blue-400" />
              </div>
              <h3 class="text-xl font-semibold text-white mb-3">面试官培训</h3>
              <p class="text-gray-400 text-sm leading-relaxed mb-6">
                帮助企业HR和面试官提升面试技巧，提高招聘效率和质量，打造专业招聘团队。
              </p>
              <div
                class="flex items-center gap-2 text-blue-400 text-sm font-medium group-hover:translate-x-2 transition-transform duration-300"
              >
                <span>开始准备</span>
                <LucideArrowRight class="w-4 h-4" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ========== CTA 区域 ========== -->
    <section class="py-24 relative overflow-hidden">
      <!-- 动态背景 -->
      <div
        class="absolute inset-0 bg-linear-to-b from-gray-900 via-gray-900/95 to-gray-900"
      ></div>
      <div
        class="absolute top-0 left-1/4 w-[400px] h-[400px] bg-cyan-500/10 rounded-full filter blur-[100px] animate-pulse"
      ></div>
      <div
        class="absolute bottom-0 right-1/4 w-[300px] h-[300px] bg-purple-500/10 rounded-full filter blur-[100px] animate-pulse"
        style="animation-delay: 1s"
      ></div>

      <div class="container mx-auto px-6 max-w-5xl relative z-10">
        <div
          class="border-gradient rounded-3xl p-12 md:p-16 relative overflow-hidden"
        >
          <!-- 内部渐变背景 -->
          <div
            class="absolute inset-0 bg-linear-to-br from-cyan-500/5 via-transparent to-purple-500/5"
          ></div>

          <!-- 装饰线条 -->
          <div
            class="absolute top-0 left-0 right-0 h-px bg-linear-to-r from-transparent via-cyan-500/50 to-transparent"
          ></div>
          <div
            class="absolute bottom-0 left-0 right-0 h-px bg-linear-to-r from-transparent via-purple-500/50 to-transparent"
          ></div>

          <div class="relative text-center">
            <!-- 标签 -->
            <div
              class="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 mb-8"
            >
              <span
                class="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"
              ></span>
              <span class="text-sm text-cyan-300">限时免费体验</span>
            </div>

            <h2
              class="text-3xl md:text-5xl font-bold text-white mb-6 leading-tight"
            >
              准备好开启你的
              <span
                class="bg-clip-text text-transparent bg-linear-to-r from-cyan-400 to-purple-500"
                >面试之旅</span
              >
              了吗？
            </h2>

            <p class="text-gray-400 mb-10 max-w-2xl mx-auto text-lg">
              立即体验 HireSense，让 AI 成为你的专属面试教练。<br />
              免费试用，即刻开始。
            </p>

            <div class="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                @click="goToSignup"
                class="group px-10 py-4 bg-white text-gray-900 font-semibold rounded-full hover:bg-gray-100 transition-all duration-300 btn-shine flex items-center justify-center gap-2 cursor-pointer"
              >
                <span>免费开始使用</span>
                <LucideArrowRight
                  class="w-4 h-4 group-hover:translate-x-1 transition-transform"
                />
              </button>
              <button
                class="px-10 py-4 border border-white/20 text-white font-medium rounded-full hover:bg-white/5 hover:border-white/40 transition-all duration-300 flex items-center justify-center gap-2 cursor-pointer"
              >
                <svg
                  class="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span>观看演示</span>
              </button>
            </div>

            <!-- 信任标识 -->
            <div class="mt-12 pt-8 border-t border-white/10">
              <p class="text-gray-500 text-sm mb-4">
                已有 10,000+ 用户选择 HireSense
              </p>
              <div class="flex items-center justify-center gap-1">
                <template v-for="i in 5" :key="i">
                  <svg
                    class="w-5 h-5 text-yellow-400"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
                    />
                  </svg>
                </template>
                <span class="ml-2 text-gray-400 text-sm">4.9/5.0 用户好评</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 页脚 -->
    <footer class="py-12 bg-gray-800 border-t border-gray-700">
      <div class="container mx-auto px-6 max-w-7xl">
        <div class="flex flex-col md:flex-row justify-between items-center">
          <div class="mb-6 md:mb-0">
            <img src="/logo-long.png" alt="HireSense Logo" class="h-8" />
          </div>
          <div class="flex space-x-8">
            <a href="#" class="text-gray-400 hover:text-white transition-colors"
              >关于我们</a
            >
            <a href="#" class="text-gray-400 hover:text-white transition-colors"
              >服务条款</a
            >
            <a href="#" class="text-gray-400 hover:text-white transition-colors"
              >隐私政策</a
            >
            <a href="#" class="text-gray-400 hover:text-white transition-colors"
              >联系我们</a
            >
          </div>
        </div>
        <div
          class="mt-8 pt-8 border-t border-gray-800 text-center text-gray-500"
        >
          <p>&copy; 2026 HireSense. 保留所有权利。</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
@keyframes pulse-slow {
  0%,
  100% {
    opacity: 0.7;
  }
  50% {
    opacity: 1;
  }
}

.animate-pulse-slow {
  animation: pulse-slow 2s ease-in-out infinite;
}
</style>
