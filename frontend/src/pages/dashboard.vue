<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import {
  getUserInfo,
  getAccessToken,
  setInterviewId,
  clearAll,
} from "@/utils/token";
import { authApi } from "@/lib/api";
import ConfirmDialog from "@/components/ConfirmDialog.vue";

const router = useRouter();
const showDropdown = ref(false);
let hideTimeout: number | null = null;

const name = ref("奶龙");
const showLogoutDialog = ref(false);
const saveMessage = ref("");
const saveSuccess = ref(false);
let messageTimeout: number | null = null;

// 通用错误消息处理函数
const showMessage = (message: string, isSuccess: boolean = false) => {
  if (messageTimeout) {
    clearTimeout(messageTimeout);
  }
  saveMessage.value = message;
  saveSuccess.value = isSuccess;
  messageTimeout = window.setTimeout(() => {
    saveMessage.value = "";
    messageTimeout = null;
  }, 3000);
};

// 从localStorage获取用户信息
onMounted(() => {
  const userInfo = getUserInfo();
  if (userInfo && userInfo.name) {
    name.value = userInfo.name;
  }
});

const handleLogout = () => {
  // 显示确认对话框
  showLogoutDialog.value = true;
};

const confirmLogout = async () => {
  showLogoutDialog.value = false;

  // 清除之前的定时器
  if (messageTimeout) {
    clearTimeout(messageTimeout);
    messageTimeout = null;
  }

  try {
    // 调用退出登录 API
    const response = await authApi.apiAuthSignoutPost();
    const data = response.data;

    if (data.success) {
      console.log("退出登录成功:", data.message);
      // 清除所有用户信息
      clearAll();
      // 跳转到登录页面
      router.push("/signin");
    } else {
      console.error("退出登录失败:", data.message);
      showMessage(data.message || "退出登录失败");
    }
  } catch (err: any) {
    console.error("退出登录错误:", err);
    showMessage(err.response?.data?.message || "网络错误，请稍后重试");
  }
};

const cancelLogout = () => {
  showLogoutDialog.value = false;
};

const goToHome = () => {
  router.push("/");
};

const goToProfile = () => {
  // 跳转到个人中心页面
  router.push("/profile");
};

const isLoading = ref(false);
const errorMessage = ref("");

const startNewInterview = async () => {
  // 显示加载状态
  isLoading.value = true;
  errorMessage.value = "";

  try {
    // 从localStorage获取token
    const token = getAccessToken();

    if (!token) {
      errorMessage.value = "请先登录";
      isLoading.value = false;
      setTimeout(() => {
        errorMessage.value = "";
      }, 3000);
      return;
    }

    // 发送开始面试请求
    const url = "http://127.0.0.1:8080/api/interview/start";
    const options = {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    };

    const response = await fetch(url, options);

    if (!response.ok) {
      throw new Error("请求失败");
    }

    const data = await response.json();

    if (data.success && data.data && data.data.id) {
      // 存储面试ID到localStorage
      setInterviewId(data.data.id);
      // 请求成功，跳转到面试页面
      router.push("/interview");
    } else {
      errorMessage.value = data.message || "启动面试失败";
      setTimeout(() => {
        errorMessage.value = "";
      }, 3000);
    }
  } catch (error) {
    console.error("启动面试失败:", error);
    errorMessage.value = "网络错误，请稍后重试";
    setTimeout(() => {
      errorMessage.value = "";
    }, 3000);
  } finally {
    // 隐藏加载状态
    isLoading.value = false;
  }
};

const showMenu = () => {
  // 清除定时器
  if (hideTimeout) {
    clearTimeout(hideTimeout);
    hideTimeout = null;
  }
  showDropdown.value = true;
};

const hideMenu = () => {
  hideTimeout = window.setTimeout(() => {
    showDropdown.value = false;
  }, 200);
};

const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement;
  if (!target.closest(".user-menu")) {
    showDropdown.value = false;
    if (hideTimeout) {
      clearTimeout(hideTimeout);
      hideTimeout = null;
    }
  }
};

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside);
  if (hideTimeout) {
    clearTimeout(hideTimeout);
  }
  if (messageTimeout) {
    clearTimeout(messageTimeout);
  }
});
</script>

<template>
  <div
    class="min-h-screen bg-linear-to-br from-gray-900 via-gray-800 to-gray-900 relative overflow-hidden"
  >
    <!-- 背景 -->
    <div
      class="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl"
    ></div>
    <div
      class="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl"
    ></div>

    <!-- 导航栏 -->
    <div
      class="navbar bg-gray-900/60 backdrop-blur-md border-b border-gray-700/50 shadow-lg relative z-10"
    >
      <div class="flex-1">
        <button
          @click="goToHome"
          class="flex items-center gap-2 transition-all duration-300 hover:scale-105 hover:opacity-90 cursor-pointer"
        >
          <img src="/logo-long.png" alt="HireSense" class="h-6 rounded-md" />
        </button>
      </div>
      <div class="flex-none">
        <!-- 用户菜单 -->
        <div
          class="user-menu relative"
          @mouseenter="showMenu"
          @mouseleave="hideMenu"
        >
          <button
            class="flex items-center justify-center w-10 h-10 rounded-full bg-gray-800/50 hover:bg-gray-700/50 border border-gray-600 transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/10 cursor-pointer"
          >
            <div
              class="w-8 h-8 rounded-full bg-linear-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-medium"
            >
              {{ name?.[0] || "用" }}
            </div>
          </button>

          <!-- 下拉菜单 -->
          <div
            v-if="showDropdown"
            class="absolute right-0 mt-1 w-48 bg-gray-900/95 backdrop-blur-md border border-gray-700/50 rounded-xl shadow-2xl shadow-blue-500/10 py-2 z-50 transition-all duration-300 transform origin-top-right"
            @mouseenter="showMenu"
            @mouseleave="hideMenu"
          >
            <button
              @click="goToProfile"
              class="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700/50 hover:text-white transition-all duration-200 flex items-center gap-2 rounded-lg hover:translate-x-1"
            >
              <svg
                class="w-4 h-4 transition-transform duration-200 hover:scale-110"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                />
              </svg>
              个人中心
            </button>
            <button
              @click="handleLogout"
              class="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700/50 hover:text-white transition-all duration-200 flex items-center gap-2 rounded-lg hover:translate-x-1"
            >
              <svg
                class="w-4 h-4 transition-transform duration-200 hover:scale-110"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                />
              </svg>
              退出登录
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="flex">
      <!-- 左侧历史面试记录侧边栏 -->
      <aside
        id="sidebar"
        class="fixed left-0 top-20 bottom-0 w-72 bg-gray-900/60 backdrop-blur-md border-r border-white/5 overflow-hidden flex flex-col z-40 transition-all duration-300"
      >
        <div class="p-4 border-b border-white/5">
          <div class="flex items-center justify-between mb-3">
            <h2 class="font-semibold text-white">历史面试记录</h2>
            <span
              class="text-xs text-slate-400 bg-gray-800/50 px-2 py-1 rounded-full"
              >12次</span
            >
          </div>
          <div class="relative">
            <input
              type="text"
              placeholder="搜索面试记录..."
              class="w-full bg-gray-800/50 border border-white/5 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 transition-colors"
            />
            <svg
              class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-3 space-y-2">
          <!-- 面试记录项 -->
          <div
            class="p-4 rounded-xl border-l-2 border-transparent cursor-pointer group hover:border-blue-500/50 hover:bg-gray-800/30 transition-all duration-200"
          >
            <div class="flex items-start justify-between mb-2">
              <span
                class="text-xs text-blue-400 bg-blue-500/10 px-2 py-1 rounded-lg"
                >前端开发工程师</span
              >
              <span class="text-xs text-slate-500">今天 14:30</span>
            </div>
            <h3
              class="font-medium text-white text-sm mb-1 group-hover:text-blue-300 transition-colors"
            >
              字节跳动 - 一面
            </h3>
            <p class="text-xs text-slate-400">技术面试 + 算法题</p>
            <div class="flex items-center gap-2 mt-3">
              <div class="flex items-center gap-1">
                <svg
                  class="w-3 h-3 text-yellow-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
                  />
                </svg>
                <span class="text-xs text-slate-300">85分</span>
              </div>
              <span class="text-xs text-slate-500">|</span>
              <span class="text-xs text-green-400">已生成报告</span>
            </div>
          </div>

          <div
            class="p-4 rounded-xl border-l-2 border-transparent cursor-pointer group hover:border-blue-500/50 hover:bg-gray-800/30 transition-all duration-200"
          >
            <div class="flex items-start justify-between mb-2">
              <span
                class="text-xs text-blue-400 bg-blue-500/10 px-2 py-1 rounded-lg"
                >全栈开发工程师</span
              >
              <span class="text-xs text-slate-500">昨天 10:00</span>
            </div>
            <h3
              class="font-medium text-white text-sm mb-1 group-hover:text-blue-300 transition-colors"
            >
              阿里巴巴 - 二面
            </h3>
            <p class="text-xs text-slate-400">系统设计 + 深度追问</p>
            <div class="flex items-center gap-2 mt-3">
              <div class="flex items-center gap-1">
                <svg
                  class="w-3 h-3 text-yellow-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
                  />
                </svg>
                <span class="text-xs text-slate-300">92分</span>
              </div>
              <span class="text-xs text-slate-500">|</span>
              <span class="text-xs text-green-400">已生成报告</span>
            </div>
          </div>

          <div
            class="p-4 rounded-xl border-l-2 border-transparent cursor-pointer group hover:border-blue-500/50 hover:bg-gray-800/30 transition-all duration-200"
          >
            <div class="flex items-start justify-between mb-2">
              <span
                class="text-xs text-yellow-400 bg-yellow-500/10 px-2 py-1 rounded-lg"
                >前端开发实习生</span
              >
              <span class="text-xs text-slate-500">今天 16:00</span>
            </div>
            <h3
              class="font-medium text-white text-sm mb-1 group-hover:text-blue-300 transition-colors"
            >
              腾讯 - 群面模拟
            </h3>
            <p class="text-xs text-slate-400">无领导小组讨论</p>
            <div class="flex items-center gap-2 mt-3">
              <div class="flex items-center gap-1">
                <svg
                  class="w-3 h-3 text-yellow-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fill-rule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z"
                    clip-rule="evenodd"
                  />
                </svg>
                <span class="text-xs text-slate-300">进行中</span>
              </div>
              <span class="text-xs text-slate-500">|</span>
              <span class="text-xs text-yellow-400">待生成报告</span>
            </div>
          </div>

          <div
            class="p-4 rounded-xl border-l-2 border-transparent cursor-pointer group hover:border-blue-500/50 hover:bg-gray-800/30 transition-all duration-200"
          >
            <div class="flex items-start justify-between mb-2">
              <span
                class="text-xs text-blue-400 bg-blue-500/10 px-2 py-1 rounded-lg"
                >前端开发工程师</span
              >
              <span class="text-xs text-slate-500">5天前</span>
            </div>
            <h3
              class="font-medium text-white text-sm mb-1 group-hover:text-blue-300 transition-colors"
            >
              美团 - HR面
            </h3>
            <p class="text-xs text-slate-400">行为面试 + 薪资谈判</p>
            <div class="flex items-center gap-2 mt-3">
              <div class="flex items-center gap-1">
                <svg
                  class="w-3 h-3 text-yellow-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
                  />
                </svg>
                <span class="text-xs text-slate-300">78分</span>
              </div>
              <span class="text-xs text-slate-500">|</span>
              <span class="text-xs text-green-400">已生成报告</span>
            </div>
          </div>

          <div
            class="p-4 rounded-xl border-l-2 border-transparent cursor-pointer group hover:border-blue-500/50 hover:bg-gray-800/30 transition-all duration-200"
          >
            <div class="flex items-start justify-between mb-2">
              <span
                class="text-xs text-blue-400 bg-blue-500/10 px-2 py-1 rounded-lg"
                >前端开发工程师</span
              >
              <span class="text-xs text-slate-500">1周前</span>
            </div>
            <h3
              class="font-medium text-white text-sm mb-1 group-hover:text-blue-300 transition-colors"
            >
              百度 - 技术面
            </h3>
            <p class="text-xs text-slate-400">Vue.js + React.js</p>
            <div class="flex items-center gap-2 mt-3">
              <div class="flex items-center gap-1">
                <svg
                  class="w-3 h-3 text-yellow-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
                  />
                </svg>
                <span class="text-xs text-slate-300">88分</span>
              </div>
              <span class="text-xs text-slate-500">|</span>
              <span class="text-xs text-green-400">已生成报告</span>
            </div>
          </div>

          <div
            class="p-4 rounded-xl border-l-2 border-transparent cursor-pointer group hover:border-blue-500/50 hover:bg-gray-800/30 transition-all duration-200"
          >
            <div class="flex items-start justify-between mb-2">
              <span
                class="text-xs text-green-400 bg-green-500/10 px-2 py-1 rounded-lg"
                >后端开发工程师</span
              >
              <span class="text-xs text-slate-500">2周前</span>
            </div>
            <h3
              class="font-medium text-white text-sm mb-1 group-hover:text-blue-300 transition-colors"
            >
              京东 - 技术面
            </h3>
            <p class="text-xs text-slate-400">Java + Spring Boot</p>
            <div class="flex items-center gap-2 mt-3">
              <div class="flex items-center gap-1">
                <svg
                  class="w-3 h-3 text-yellow-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
                  />
                </svg>
                <span class="text-xs text-slate-300">95分</span>
              </div>
              <span class="text-xs text-slate-500">|</span>
              <span class="text-xs text-green-400">已生成报告</span>
            </div>
          </div>

          <div
            class="p-4 rounded-xl border-l-2 border-transparent cursor-pointer group hover:border-blue-500/50 hover:bg-gray-800/30 transition-all duration-200"
          >
            <div class="flex items-start justify-between mb-2">
              <span
                class="text-xs text-blue-400 bg-blue-500/10 px-2 py-1 rounded-lg"
                >前端开发工程师</span
              >
              <span class="text-xs text-slate-500">3周前</span>
            </div>
            <h3
              class="font-medium text-white text-sm mb-1 group-hover:text-blue-300 transition-colors"
            >
              小红书 - 技术面
            </h3>
            <p class="text-xs text-slate-400">小程序开发 + 性能优化</p>
            <div class="flex items-center gap-2 mt-3">
              <div class="flex items-center gap-1">
                <svg
                  class="w-3 h-3 text-yellow-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
                  />
                </svg>
                <span class="text-xs text-slate-300">82分</span>
              </div>
              <span class="text-xs text-slate-500">|</span>
              <span class="text-xs text-green-400">已生成报告</span>
            </div>
          </div>

          <div
            class="p-4 rounded-xl border-l-2 border-transparent cursor-pointer group hover:border-blue-500/50 hover:bg-gray-800/30 transition-all duration-200"
          >
            <div class="flex items-start justify-between mb-2">
              <span
                class="text-xs text-green-400 bg-green-500/10 px-2 py-1 rounded-lg"
                >后端开发工程师</span
              >
              <span class="text-xs text-slate-500">1个月前</span>
            </div>
            <h3
              class="font-medium text-white text-sm mb-1 group-hover:text-blue-300 transition-colors"
            >
              拼多多 - 技术面
            </h3>
            <p class="text-xs text-slate-400">数据库设计 + 高并发</p>
            <div class="flex items-center gap-2 mt-3">
              <div class="flex items-center gap-1">
                <svg
                  class="w-3 h-3 text-yellow-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
                  />
                </svg>
                <span class="text-xs text-slate-300">90分</span>
              </div>
              <span class="text-xs text-slate-500">|</span>
              <span class="text-xs text-green-400">已生成报告</span>
            </div>
          </div>

          <div
            class="p-4 rounded-xl border-l-2 border-transparent cursor-pointer group hover:border-blue-500/50 hover:bg-gray-800/30 transition-all duration-200"
          >
            <div class="flex items-start justify-between mb-2">
              <span
                class="text-xs text-blue-400 bg-blue-500/10 px-2 py-1 rounded-lg"
                >前端开发工程师</span
              >
              <span class="text-xs text-slate-500">1个月前</span>
            </div>
            <h3
              class="font-medium text-white text-sm mb-1 group-hover:text-blue-300 transition-colors"
            >
              字节跳动 - 技术面
            </h3>
            <p class="text-xs text-slate-400">TypeScript + 工程化</p>
            <div class="flex items-center gap-2 mt-3">
              <div class="flex items-center gap-1">
                <svg
                  class="w-3 h-3 text-yellow-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
                  />
                </svg>
                <span class="text-xs text-slate-300">96分</span>
              </div>
              <span class="text-xs text-slate-500">|</span>
              <span class="text-xs text-green-400">已生成报告</span>
            </div>
          </div>

          <div
            class="p-4 rounded-xl border-l-2 border-transparent cursor-pointer group hover:border-blue-500/50 hover:bg-gray-800/30 transition-all duration-200"
          >
            <div class="flex items-start justify-between mb-2">
              <span
                class="text-xs text-green-400 bg-green-500/10 px-2 py-1 rounded-lg"
                >后端开发工程师</span
              >
              <span class="text-xs text-slate-500">2个月前</span>
            </div>
            <h3
              class="font-medium text-white text-sm mb-1 group-hover:text-blue-300 transition-colors"
            >
              华为 - 技术面
            </h3>
            <p class="text-xs text-slate-400">微服务 + 分布式系统</p>
            <div class="flex items-center gap-2 mt-3">
              <div class="flex items-center gap-1">
                <svg
                  class="w-3 h-3 text-yellow-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
                  />
                </svg>
                <span class="text-xs text-slate-300">87分</span>
              </div>
              <span class="text-xs text-slate-500">|</span>
              <span class="text-xs text-green-400">已生成报告</span>
            </div>
          </div>
        </div>

        <!-- 开始新面试按钮 -->
        <div class="p-4 border-t border-white/5">
          <!-- 错误消息 -->
          <div
            v-if="errorMessage"
            class="mb-3 px-4 py-2 rounded-lg bg-red-500/20 border border-red-500/40 text-red-400 text-sm"
          >
            {{ errorMessage }}
          </div>

          <button
            @click="startNewInterview"
            :disabled="isLoading"
            class="w-full py-3 rounded-xl bg-linear-to-r from-blue-500 to-blue-600 hover:from-blue-400 hover:to-blue-500 text-white font-medium transition-all shadow-lg hover:shadow-blue-500/25 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg
              v-if="!isLoading"
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 4v16m8-8H4"
              />
            </svg>
            <svg
              v-else
              class="w-4 h-4 animate-spin"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            <span>{{ isLoading ? "启动中..." : "开始新面试" }}</span>
          </button>
        </div>
      </aside>

      <!-- 右侧留白区域 -->
      <div class="flex-1 ml-72 p-8">
        <div class="h-full flex items-center justify-center">
          <div class="text-center">
            <svg
              class="w-16 h-16 text-gray-700 mx-auto mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="1.5"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <h3 class="text-xl font-semibold text-gray-400">
              选择一个面试记录查看详情
            </h3>
            <p class="text-gray-500 mt-2">
              从左侧列表中选择一个面试记录以查看详细信息
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- 退出登录确认对话框 -->
    <ConfirmDialog
      :show="showLogoutDialog"
      title="确认退出登录"
      message="确定要退出登录吗？"
      confirm-text="确认退出"
      cancel-text="取消"
      @confirm="confirmLogout"
      @cancel="cancelLogout"
    />

    <!-- 错误消息提示 -->
    <div
      v-if="saveMessage"
      :class="[
        'fixed top-20 left-1/2 transform -translate-x-1/2 p-4 rounded-lg shadow-lg z-50 transition-all duration-300 max-w-md w-full mx-4',
        saveSuccess
          ? 'bg-green-500/20 border border-green-500/50 text-green-400'
          : 'bg-red-500/20 border border-red-500/50 text-red-400',
      ]"
    >
      {{ saveMessage }}
    </div>
  </div>
</template>
