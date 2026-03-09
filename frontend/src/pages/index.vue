<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import LucideLogIn from "~icons/lucide/log-in";
import LucideUserPlus from "~icons/lucide/user-plus";
import LucideBrain from "~icons/lucide/brain";
import LucideBarChart3 from "~icons/lucide/bar-chart-3";
import LucideMessageSquare from "~icons/lucide/message-square";
import LucideUserCheck from "~icons/lucide/user-check";
import LucideSchool from "~icons/lucide/school";
import LucideBriefcase from "~icons/lucide/briefcase";
import LucideUsers from "~icons/lucide/users";
import Projector from "../components/Projector.vue";

const router = useRouter();
const scrolled = ref(false);
const activeSection = ref("hero");

onMounted(() => {
  window.addEventListener("scroll", handleScroll);
  initAnimations();
});

onUnmounted(() => {
  window.removeEventListener("scroll", handleScroll);
});

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
  const style = document.createElement("style");
  style.textContent = `
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
  `;
  document.head.appendChild(style);
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
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white">
    <!-- 导航栏 -->
    <nav
      :class="[
        'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
        scrolled
          ? 'bg-gray-900/95 backdrop-blur-sm shadow-lg'
          : 'bg-transparent',
      ]"
    >
      <div class="container mx-auto px-6 py-4">
        <div class="flex items-center justify-between">
          <!-- Logo -->
          <div class="flex items-center">
            <img
              src="/logo-long.png"
              alt="HireSense Logo"
              class="h-8 rounded-lg cursor-pointer hover:opacity-80 transition-opacity"
              @click="scrollToSection('hero')"
            />
          </div>

          <!-- 导航链接 -->
          <div class="hidden md:flex items-center space-x-6 ml-auto mr-8">
            <button
              @click="scrollToSection('features')"
              :class="[
                'relative px-4 py-2 rounded-lg transition-all duration-300',
                activeSection === 'features'
                  ? 'text-white bg-blue-500/20 font-medium'
                  : 'text-gray-300 hover:text-white hover:bg-gray-800/50',
              ]"
            >
              核心功能
            </button>
            <button
              @click="scrollToSection('advantages')"
              :class="[
                'relative px-4 py-2 rounded-lg transition-all duration-300',
                activeSection === 'advantages'
                  ? 'text-white bg-blue-500/20 font-medium'
                  : 'text-gray-300 hover:text-white hover:bg-gray-800/50',
              ]"
            >
              产品优势
            </button>
            <button
              @click="scrollToSection('cases')"
              :class="[
                'relative px-4 py-2 rounded-lg transition-all duration-300',
                activeSection === 'cases'
                  ? 'text-white bg-blue-500/20 font-medium'
                  : 'text-gray-300 hover:text-white hover:bg-gray-800/50',
              ]"
            >
              场景案例
            </button>
          </div>

          <!-- 登录注册按钮 -->
          <div class="flex items-center space-x-4">
            <button
              @click="goToSignin"
              class="btn btn-sm btn-ghost text-gray-300 hover:text-white"
            >
              <LucideLogIn class="w-4 h-4 mr-2" />
              登录
            </button>
            <button @click="goToSignup" class="btn btn-sm btn-primary">
              <LucideUserPlus class="w-4 h-4 mr-2" />
              注册
            </button>
          </div>
        </div>
      </div>
    </nav>

    <!-- Hero 区 -->
    <section id="hero" class="relative min-h-screen flex items-center">
      <!-- 背景 -->
      <div
        class="absolute inset-0 bg-gradient-to-br from-gray-900 via-blue-950 to-gray-900"
      ></div>
      <div
        class="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(59,130,246,0.15),transparent_70%)]"
      ></div>

      <div class="container mx-auto px-6 py-24 relative z-10">
        <div class="flex flex-col md:flex-row items-center">
          <!-- 左侧文字 -->
          <div class="md:w-1/2 mb-12 md:mb-0">
            <h1
              class="text-6xl md:text-7xl font-bold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500"
            >
              HireSense
            </h1>
            <h2 class="text-3xl font-semibold mb-6 text-blue-300">知聘</h2>
            <p class="text-xl text-gray-300 mb-8 max-w-lg">
              AI驱动的模拟面试与能力提升平台，为您提供真实的面试体验和个性化的反馈，助力您在求职道路上脱颖而出。
            </p>
            <div class="flex flex-col sm:flex-row gap-4">
              <button @click="goToSignup" class="btn btn-lg btn-primary">
                Get Started
              </button>
              <button
                @click="scrollToSection('features')"
                class="btn btn-lg btn-ghost text-gray-300 hover:text-white border border-gray-700"
              >
                了解更多
              </button>
            </div>
          </div>

          <!-- 右侧投影仪轮播图 -->
          <div class="md:w-1/2 relative pl-4">
            <Projector />
          </div>
        </div>
      </div>

      <!-- 箭头引导 -->
      <div
        class="absolute bottom-12 left-1/2 -translate-x-1/2 flex justify-center animate-bounce"
      >
        <div
          class="w-10 h-10 rounded-full bg-gray-800/50 border border-gray-700 flex items-center justify-center cursor-pointer hover:bg-gray-700/50 transition-all duration-300 animate-pulse-slow"
          @click="scrollToSection('features')"
        >
          <svg
            class="w-6 h-6 text-blue-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 14l-7 7m0 0l-7-7m7 7V3"
            />
          </svg>
        </div>
      </div>
    </section>

    <!-- 核心功能区 -->
    <section id="features" class="py-20 bg-gray-900">
      <div class="container mx-auto px-6">
        <div class="text-center mb-16 animate-on-scroll">
          <h2 class="text-4xl font-bold mb-4">核心功能</h2>
          <p class="text-xl text-gray-400 max-w-3xl mx-auto">
            我们的平台提供全面的智能面试解决方案，帮助您提升面试技巧和竞争力
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          <!-- 功能模块 1 -->
          <div
            class="bg-gray-800/50 rounded-xl p-6 border border-gray-700 animate-on-scroll card-hover"
          >
            <div
              class="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center mb-4"
            >
              <LucideBrain class="w-6 h-6 text-blue-400" />
            </div>
            <h3 class="text-xl font-semibold mb-3">AI智能面试官</h3>
            <p class="text-gray-400">
              基于大语言模型的智能面试官，能够模拟真实面试场景，进行多轮对话和智能追问
            </p>
          </div>

          <!-- 功能模块 2 -->
          <div
            class="bg-gray-800/50 rounded-xl p-6 border border-gray-700 animate-on-scroll card-hover"
          >
            <div
              class="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center mb-4"
            >
              <LucideBarChart3 class="w-6 h-6 text-blue-400" />
            </div>
            <h3 class="text-xl font-semibold mb-3">实时智能评估</h3>
            <p class="text-gray-400">
              多维度评估面试表现，包括技术知识、表达能力、逻辑思维等，生成详细的评估报告
            </p>
          </div>

          <!-- 功能模块 3 -->
          <div
            class="bg-gray-800/50 rounded-xl p-6 border border-gray-700 animate-on-scroll card-hover"
          >
            <div
              class="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center mb-4"
            >
              <LucideMessageSquare class="w-6 h-6 text-blue-400" />
            </div>
            <h3 class="text-xl font-semibold mb-3">多模态交互</h3>
            <p class="text-gray-400">
              支持语音和文本输入，实现自然流畅的对话，模拟真实面试环境
            </p>
          </div>

          <!-- 功能模块 4 -->
          <div
            class="bg-gray-800/50 rounded-xl p-6 border border-gray-700 animate-on-scroll card-hover"
          >
            <div
              class="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center mb-4"
            >
              <LucideUserCheck class="w-6 h-6 text-blue-400" />
            </div>
            <h3 class="text-xl font-semibold mb-3">个性化提升</h3>
            <p class="text-gray-400">
              根据面试表现分析能力短板，智能推荐学习资源和改进建议，形成个性化提升路径
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- 产品优势区 -->
    <section id="advantages" class="py-20 bg-gray-900/80">
      <div class="container mx-auto px-6">
        <div class="text-center mb-16 animate-on-scroll">
          <h2 class="text-4xl font-bold mb-4">产品优势</h2>
          <p class="text-xl text-gray-400 max-w-3xl mx-auto">
            相比传统面试准备方式，我们的平台具有显著优势
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          <!-- 优势卡片 1 -->
          <div
            class="bg-gray-800/50 rounded-xl p-6 border border-gray-700 animate-on-scroll card-hover"
          >
            <h3 class="text-xl font-semibold mb-3 text-blue-400">AI智能提问</h3>
            <p class="text-gray-400">
              基于岗位需求和个人背景，生成针对性问题，模拟真实面试场景
            </p>
          </div>

          <!-- 优势卡片 2 -->
          <div
            class="bg-gray-800/50 rounded-xl p-6 border border-gray-700 animate-on-scroll card-hover"
          >
            <h3 class="text-xl font-semibold mb-3 text-blue-400">实时评分</h3>
            <p class="text-gray-400">
              面试过程中实时评估表现，提供即时反馈，帮助快速调整状态
            </p>
          </div>

          <!-- 优势卡片 3 -->
          <div
            class="bg-gray-800/50 rounded-xl p-6 border border-gray-700 animate-on-scroll card-hover"
          >
            <h3 class="text-xl font-semibold mb-3 text-blue-400">多语言支持</h3>
            <p class="text-gray-400">
              支持多种语言面试，帮助您准备国际化岗位的面试挑战
            </p>
          </div>

          <!-- 优势卡片 4 -->
          <div
            class="bg-gray-800/50 rounded-xl p-6 border border-gray-700 animate-on-scroll card-hover"
          >
            <h3 class="text-xl font-semibold mb-3 text-blue-400">数据可视化</h3>
            <p class="text-gray-400">
              通过图表直观展示面试表现，清晰了解自身优势和不足
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- 场景案例区 -->
    <section id="cases" class="py-20 bg-gray-900">
      <div class="container mx-auto px-6">
        <div class="text-center mb-16 animate-on-scroll">
          <h2 class="text-4xl font-bold mb-4">场景案例</h2>
          <p class="text-xl text-gray-400 max-w-3xl mx-auto">
            我们的平台适用于多种面试场景，满足不同用户的需求
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
          <!-- 场景案例 1 -->
          <div
            class="bg-gray-800/50 rounded-xl overflow-hidden border border-gray-700 animate-on-scroll card-hover"
          >
            <div class="h-48 bg-gray-700/50 flex items-center justify-center">
              <LucideSchool class="w-16 h-16 text-blue-400" />
            </div>
            <div class="p-6">
              <h3 class="text-xl font-semibold mb-3">企业校招</h3>
              <p class="text-gray-400 mb-4">
                帮助应届毕业生准备校招面试，熟悉企业招聘流程和常见问题
              </p>
              <button class="btn btn-sm btn-primary">了解更多</button>
            </div>
          </div>

          <!-- 场景案例 2 -->
          <div
            class="bg-gray-800/50 rounded-xl overflow-hidden border border-gray-700 animate-on-scroll card-hover"
          >
            <div class="h-48 bg-gray-700/50 flex items-center justify-center">
              <LucideBriefcase class="w-16 h-16 text-blue-400" />
            </div>
            <div class="p-6">
              <h3 class="text-xl font-semibold mb-3">社招跳槽</h3>
              <p class="text-gray-400 mb-4">
                为有工作经验的求职者提供针对性面试准备，提升跳槽成功率
              </p>
              <button class="btn btn-sm btn-primary">了解更多</button>
            </div>
          </div>

          <!-- 场景案例 3 -->
          <div
            class="bg-gray-800/50 rounded-xl overflow-hidden border border-gray-700 animate-on-scroll card-hover"
          >
            <div class="h-48 bg-gray-700/50 flex items-center justify-center">
              <LucideUsers class="w-16 h-16 text-blue-400" />
            </div>
            <div class="p-6">
              <h3 class="text-xl font-semibold mb-3">面试官培训</h3>
              <p class="text-gray-400 mb-4">
                帮助企业HR和面试官提升面试技巧，提高招聘效率和质量
              </p>
              <button class="btn btn-sm btn-primary">了解更多</button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 页脚 -->
    <footer class="py-12 bg-gray-950 border-t border-gray-800">
      <div class="container mx-auto px-6">
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
