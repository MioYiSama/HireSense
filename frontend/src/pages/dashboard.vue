<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from "vue";
import { useRouter } from "vue-router";
import {
  getUserInfo,
  getAccessToken,
  setInterviewId,
  setInitialReply,
  clearAll,
} from "@/utils/token";
import { authApi } from "@/lib/api";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import GrowthCurve from "@/components/GrowthCurve.vue";

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

// 面试记录相关
const interviews = ref<any[]>([]);
const isLoadingInterviews = ref(false);
const interviewsError = ref("");
const isRefreshing = ref(false);
const showRefreshAnimation = ref(false);

// 刷新面试数据
const refreshInterviews = async () => {
  // 开始刷新动画
  isRefreshing.value = true;
  showRefreshAnimation.value = true;

  try {
    await fetchInterviews();
    // 延迟一小段时间，让动画效果更明显
    await new Promise((resolve) => setTimeout(resolve, 500));
  } finally {
    // 结束刷新动画
    showRefreshAnimation.value = false;
    // 稍微延迟后恢复按钮状态，让用户有足够时间看到动画
    setTimeout(() => {
      isRefreshing.value = false;
    }, 300);
  }
};

// 个人成长数据
const growthData = computed(() => {
  const { completedInterviews, scores } = commonComputedData.value;

  return {
    totalInterviews: interviews.value.length,
    completedInterviews: completedInterviews.length,
    averageScore:
      scores.length > 0
        ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
        : 0,
    highestScore: scores.length > 0 ? Math.max(...scores) : 0,
    improvement:
      scores.length > 2
        ? Math.round(
            ((scores[scores.length - 1] - scores[0]) * 100) / scores[0],
          )
        : 0,
  };
});

// 能力成长曲线数据
const growthCurveData = computed(() => {
  // 过滤出有报告的面试
  const completedInterviews = interviews.value
    .filter((item) => item.report)
    .sort((a, b) => {
      // 按时间排序
      const timeA = new Date(a.created_at || 0).getTime();
      const timeB = new Date(b.created_at || 0).getTime();
      return timeA - timeB;
    });

  // 提取分数和时间
  const realData = completedInterviews.map((item) => ({
    score: item.report.score,
    date: new Date(item.created_at || 0),
  }));

  // 根据时间范围过滤数据
  const now = new Date();
  const days = parseInt(timeRange.value);
  const cutoffDate = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);

  const filteredData = realData.filter((item) => item.date >= cutoffDate);

  // 如果真实数据点较少，生成额外的模拟数据
  if (filteredData.length <= 1) {
    const mockData = [];
    const today = new Date();

    // 生成最近N天的模拟数据
    for (let i = days - 1; i >= 0; i -= Math.max(1, Math.floor(days / 5))) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);

      // 生成逐渐增长的分数
      const baseScore = 60;
      const growth = (days - 1 - i) * (25 / (days - 1));
      const score = Math.round(baseScore + growth);

      mockData.push({
        score,
        date,
      });
    }

    return mockData;
  }

  return filteredData;
});

// 通用计算数据，避免重复计算
const commonComputedData = computed(() => {
  const completedInterviews = interviews.value.filter((item) => item.report);
  const scores = completedInterviews.map((item) => item.report.score);

  return {
    completedInterviews,
    scores,
  };
});

// 时间范围选择
const timeRange = ref("30"); // 默认近30天

// 能力对比进度条数据
const abilityProgress = ref({
  communication: 0,
  problemSolving: 0,
  logicalThinking: 0,
  professionalSkills: 0,
});

// 目标进度值
const targetProgress = {
  communication: 75,
  problemSolving: 85,
  logicalThinking: 80,
  professionalSkills: 70,
};

// 分析面试报告中的薄弱点
const weakPoints = computed(() => {
  const { completedInterviews } = commonComputedData.value;
  if (completedInterviews.length === 0) {
    return ["专业技能需要加强", "沟通表达不够流畅", "项目经验描述不够详细"];
  }

  // 获取最新的面试报告
  const latestInterview = completedInterviews[completedInterviews.length - 1];
  const report = latestInterview.report;

  if (!report) {
    return ["专业技能需要加强", "沟通表达不够流畅", "项目经验描述不够详细"];
  }

  const weakAreas: string[] = [];

  // 分析通用能力
  if (report.general) {
    Object.entries(report.general).forEach(([name, score]) => {
      const numScore = Number(score);
      if (numScore < 70) {
        switch (name) {
          case "communication":
            weakAreas.push("沟通表达能力需要加强");
            break;
          case "problemSolving":
            weakAreas.push("问题解决能力需要提升");
            break;
          case "logicalThinking":
            weakAreas.push("逻辑思维能力需要加强");
            break;
          default:
            weakAreas.push(`${name}能力需要加强`);
        }
      }
    });
  }

  // 分析专业能力
  if (report.specific) {
    Object.entries(report.specific).forEach(([name, score]) => {
      const numScore = Number(score);
      if (numScore < 70) {
        weakAreas.push(`${name}技能需要加强`);
      }
    });
  }

  // 如果没有找到薄弱点，返回默认值
  if (weakAreas.length === 0) {
    return ["专业技能需要加强", "沟通表达不够流畅", "项目经验描述不够详细"];
  }

  return weakAreas.slice(0, 3); // 最多返回3个薄弱点
});

// 生成针对性的改进建议
const improvementSuggestions = computed(() => {
  const weak = weakPoints.value;
  const suggestions: string[] = [];

  if (weak.some((item) => item.includes("沟通表达"))) {
    suggestions.push("多练习面试表达，录制自己的回答并分析改进");
  }

  if (weak.some((item) => item.includes("问题解决"))) {
    suggestions.push("多练习算法题和系统设计问题");
  }

  if (weak.some((item) => item.includes("逻辑思维"))) {
    suggestions.push("练习结构化思考和表达能力");
  }

  if (weak.some((item) => item.includes("专业技能"))) {
    suggestions.push("针对岗位要求系统学习相关技术栈");
  }

  if (weak.some((item) => item.includes("项目经验"))) {
    suggestions.push("准备项目案例的详细描述，突出自己的贡献");
  }

  // 补充默认建议
  while (suggestions.length < 3) {
    const defaultSuggestions = [
      "参加模拟面试训练",
      "准备常见面试问题的答案",
      "学习行业最新技术趋势",
    ];
    defaultSuggestions.forEach((suggestion) => {
      if (!suggestions.includes(suggestion) && suggestions.length < 3) {
        suggestions.push(suggestion);
      }
    });
    break;
  }

  return suggestions;
});

// 生成学习资源建议
const learningResources = computed(() => {
  const weak = weakPoints.value;
  const resources: string[] = [];

  if (weak.some((item) => item.includes("算法"))) {
    resources.push("LeetCode 算法题");
  }

  if (weak.some((item) => item.includes("系统设计"))) {
    resources.push("系统设计面试指南");
  }

  if (weak.some((item) => item.includes("前端"))) {
    resources.push("前端面试常见问题");
  }

  if (weak.some((item) => item.includes("后端"))) {
    resources.push("后端技术面试题集");
  }

  // 补充默认资源
  while (resources.length < 3) {
    const defaultResources = [
      "技术博客和社区",
      "行业会议和讲座",
      "在线课程平台",
    ];
    defaultResources.forEach((resource) => {
      if (!resources.includes(resource) && resources.length < 3) {
        resources.push(resource);
      }
    });
    break;
  }

  return resources;
});

// 时间格式化函数
const formatInterviewTime = (timestamp: any): string => {
  try {
    // 确保时间戳是数字类型
    const ts =
      typeof timestamp === "string" ? parseInt(timestamp, 10) : timestamp;
    if (isNaN(ts)) {
      return "时间未知";
    }
    return new Date(ts).toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch (error) {
    return "时间未知";
  }
};

// 公司名字列表
const companyNames = [
  "字节跳动",
  "阿里巴巴",
  "腾讯",
  "美团",
  "百度",
  "京东",
  "拼多多",
  "小红书",
  "网易",
  "新浪",
  "搜狐",
  "快手",
  "B站",
  "滴滴",
  "高德",
  "携程",
  "小米",
  "华为",
  "OPPO",
  "vivo",
  "魅族",
  "一加",
  "荣耀",
  "联想",
  "IBM",
  "微软",
  "谷歌",
  "亚马逊",
  "苹果",
  "脸书",
  "特斯拉",
  "英特尔",
];

// 为面试生成随机公司名字
const getRandomCompanyName = (id: string): string => {
  // 使用ID作为种子，确保同一个面试总是显示相同的公司名字
  let seed = 0;
  for (let i = 0; i < id.length; i++) {
    seed += id.charCodeAt(i);
  }
  const index = Math.abs(seed) % companyNames.length;
  return companyNames[index] || "未知公司";
};

// 获取面试记录
const fetchInterviews = async () => {
  isLoadingInterviews.value = true;
  interviewsError.value = "";

  try {
    const token = getAccessToken();

    if (!token) {
      interviewsError.value = "请先登录";
      isLoadingInterviews.value = false;
      return;
    }

    const url = "http://127.0.0.1:8080/api/user/interviews";
    const options = {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    };

    const response = await fetch(url, options);

    if (!response.ok) {
      throw new Error("请求失败");
    }

    const data = await response.json();

    if (data.success) {
      interviews.value = data.data || [];
    } else {
      interviewsError.value = data.message || "获取面试记录失败";
    }
  } catch (error) {
    console.error("获取面试记录失败:", error);
    interviewsError.value = "网络错误，请稍后重试";
  } finally {
    isLoadingInterviews.value = false;
  }
};

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
      // 存储AI面试官的初始回复
      if (data.data.reply) {
        setInitialReply(data.data.reply);
      }
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
  // 从localStorage获取用户信息
  const userInfo = getUserInfo();
  if (userInfo && userInfo.name) {
    name.value = userInfo.name;
  }

  // 获取面试记录
  fetchInterviews();

  document.addEventListener("click", handleClickOutside);

  // 启动能力对比进度条动画
  const animateProgress = () => {
    const duration = 1500;
    const startTime = performance.now();

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      const easeOutQuart = 1 - Math.pow(1 - progress, 4);

      abilityProgress.value = {
        communication: targetProgress.communication * easeOutQuart,
        problemSolving: targetProgress.problemSolving * easeOutQuart,
        logicalThinking: targetProgress.logicalThinking * easeOutQuart,
        professionalSkills: targetProgress.professionalSkills * easeOutQuart,
      };

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  };

  setTimeout(animateProgress, 300);
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
      class="fixed top-0 left-0 right-0 navbar bg-gray-900/95 backdrop-blur-sm border-b border-gray-700/50 shadow-lg z-50 transition-all duration-300"
    >
      <div class="flex-1">
        <button
          @click="goToHome"
          class="flex items-center gap-3 transition-all duration-300 hover:scale-105 hover:opacity-90 cursor-pointer"
        >
          <div class="flex items-center gap-2">
            <img
              src="/favicon.png"
              alt="HireSense"
              class="h-8 w-8 rounded-md object-contain"
            />
            <span class="text-xl font-bold text-white tracking-tight"
              >Hire Sense</span
            >
          </div>
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
        class="fixed left-0 top-16 bottom-0 w-72 bg-gray-900/60 backdrop-blur-md border-r border-white/5 overflow-hidden flex flex-col z-40 transition-all duration-300"
      >
        <div class="p-4 border-b border-white/5">
          <div class="flex items-center justify-between">
            <h2 class="font-semibold text-white">历史面试记录</h2>
            <span
              class="text-xs text-slate-400 bg-gray-800/50 px-2 py-1 rounded-full"
              >{{ interviews.length }}次</span
            >
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-3 space-y-2">
          <!-- 加载状态 -->
          <div
            v-if="isLoadingInterviews || isRefreshing"
            class="flex justify-center items-center py-12"
          >
            <div class="flex flex-col items-center">
              <svg
                class="w-8 h-8 text-blue-400 animate-spin"
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
              <span class="text-sm text-gray-400 mt-2">加载中...</span>
            </div>
          </div>

          <!-- 错误信息 -->
          <div
            v-else-if="interviewsError"
            class="p-4 rounded-xl bg-red-500/20 border border-red-500/40 text-red-400"
          >
            <div class="flex items-center gap-2">
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
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
              <span>{{ interviewsError }}</span>
            </div>
            <button
              @click="fetchInterviews"
              class="mt-2 text-sm text-blue-400 hover:underline"
            >
              重试
            </button>
          </div>

          <!-- 空状态 -->
          <div
            v-else-if="interviews.length === 0"
            class="flex flex-col items-center justify-center py-12 text-center"
          >
            <svg
              class="w-12 h-12 text-gray-600 mb-4"
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
            <h3 class="text-lg font-medium text-gray-400 mb-1">暂无面试记录</h3>
            <p class="text-sm text-gray-500 mb-4">开始您的第一次AI面试吧</p>
            <button
              @click="startNewInterview"
              class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm transition-colors"
            >
              开始新面试
            </button>
          </div>

          <!-- 面试记录列表 -->
          <div
            v-else
            :class="[
              'space-y-2',
              showRefreshAnimation
                ? 'opacity-50 scale-95'
                : 'opacity-100 scale-100',
            ]"
            :style="{
              transition: showRefreshAnimation
                ? 'all 0.3s ease-out'
                : 'all 0.5s ease-in',
            }"
          >
            <!-- 面试记录项 -->
            <div
              v-for="interview in interviews"
              :key="interview.id"
              @click="
                interview.report &&
                router.push(`/interview/${interview.id}/report`)
              "
              :class="[
                'p-4 rounded-xl border-l-2 cursor-pointer group transition-all duration-200',
                interview.report
                  ? 'border-transparent hover:border-blue-500/50 hover:bg-gray-800/30'
                  : 'border-gray-700/30 opacity-70 cursor-not-allowed',
              ]"
            >
              <div class="flex items-start justify-between mb-2">
                <span
                  class="text-xs text-blue-400 bg-blue-500/10 px-2 py-1 rounded-lg"
                  >{{
                    interview.report
                      ? interview.report.specific
                        ? "前端开发工程师"
                        : "后端开发工程师"
                      : "面试"
                  }}</span
                >
                <span class="text-xs text-slate-500">{{
                  formatInterviewTime(interview.created_at)
                }}</span>
              </div>
              <h3
                class="font-medium text-white text-sm mb-1 group-hover:text-blue-300 transition-colors"
              >
                {{ getRandomCompanyName(interview.id) }} -
                {{ interview.status === "stopped" ? "已结束" : "进行中" }}
              </h3>
              <p class="text-xs text-slate-400">
                {{ interview.report ? "已生成报告" : "待生成报告" }}
              </p>
              <div class="flex items-center gap-2 mt-3">
                <div class="flex items-center gap-1">
                  <svg
                    v-if="interview.report"
                    class="w-3 h-3 text-yellow-400"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
                    />
                  </svg>
                  <svg
                    v-else
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
                  <span class="text-xs text-slate-300">{{
                    interview.report ? interview.report.score + "分" : "进行中"
                  }}</span>
                </div>
                <span class="text-xs text-slate-500">|</span>
                <span
                  class="text-xs"
                  :class="
                    interview.report ? 'text-green-400' : 'text-yellow-400'
                  "
                >
                  {{ interview.report ? "已生成报告" : "待生成报告" }}
                </span>
              </div>
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

      <!-- 右侧个人成长展示区域 -->
      <div class="flex-1 ml-72 mt-16 p-8 space-y-8">
        <!-- 顶部概览区 -->
        <section class="space-y-6">
          <div class="animate-fade-in-up">
            <h1
              class="text-3xl font-bold bg-linear-to-r from-blue-300 via-purple-400 to-pink-500 bg-clip-text text-transparent mb-4 drop-shadow-lg"
            >
              你好，{{ name }}，欢迎回来！
            </h1>
            <div
              class="inline-block border border-blue-400/30 rounded-lg px-4 py-2 bg-blue-900/20 backdrop-blur-sm bubble-dialog"
            >
              <p
                class="text-lg text-transparent font-medium bg-linear-to-r from-blue-400 to-purple-400 bg-clip-text animate-typewriter"
              >
                解锁你的面试成长数据
              </p>
            </div>
          </div>

          <!-- 数据卡片 -->
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-semibold text-white">个人成长数据</h2>
            <button
              @click="refreshInterviews"
              :class="[
                'flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-300',
                isRefreshing
                  ? 'bg-gray-700/50 text-gray-400 cursor-not-allowed'
                  : 'bg-gray-800/70 text-gray-300 hover:bg-gray-700/70 hover:text-white',
              ]"
              :disabled="isRefreshing"
            >
              <svg
                v-if="!isRefreshing"
                class="w-4 h-4"
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
              <span>{{ isRefreshing ? "刷新中..." : "刷新数据" }}</span>
            </button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <!-- 总面试次数 -->
            <div
              :class="[
                'bg-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 shadow-lg hover:shadow-blue-500/10 transition-all duration-500 hover:border-blue-500/30 group animate-fade-in-up animate-delay-100 card-hover',
                showRefreshAnimation
                  ? 'opacity-50 scale-95'
                  : 'opacity-100 scale-100',
              ]"
              :style="{
                transition: showRefreshAnimation
                  ? 'all 0.3s ease-out'
                  : 'all 0.5s ease-in',
              }"
            >
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-gray-400 text-sm font-medium">总面试次数</h3>
                <div
                  class="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center group-hover:bg-blue-500/30 transition-all duration-300 group-hover:scale-110"
                >
                  <svg
                    class="w-5 h-5 text-blue-400 group-hover:rotate-12 transition-transform duration-300"
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
              </div>
              <div class="text-3xl font-bold text-white">
                {{ growthData.totalInterviews }}
              </div>
              <p class="text-xs text-gray-500 mt-1">次面试</p>
            </div>

            <!-- 已完成面试 -->
            <div
              :class="[
                'bg-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 shadow-lg hover:shadow-green-500/10 transition-all duration-500 hover:border-green-500/30 group animate-fade-in-up animate-delay-200 card-hover',
                showRefreshAnimation
                  ? 'opacity-50 scale-95'
                  : 'opacity-100 scale-100',
              ]"
              :style="{
                transition: showRefreshAnimation
                  ? 'all 0.3s ease-out'
                  : 'all 0.5s ease-in',
              }"
            >
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-gray-400 text-sm font-medium">已完成面试</h3>
                <div
                  class="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center group-hover:bg-green-500/30 transition-all duration-300 group-hover:scale-110"
                >
                  <svg
                    class="w-5 h-5 text-green-400 group-hover:rotate-12 transition-transform duration-300"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
              </div>
              <div class="text-3xl font-bold text-white">
                {{ growthData.completedInterviews }}
              </div>
              <p class="text-xs text-gray-500 mt-1">份报告</p>
            </div>

            <!-- 平均得分 -->
            <div
              :class="[
                'bg-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 shadow-lg hover:shadow-yellow-500/10 transition-all duration-500 hover:border-yellow-500/30 group animate-fade-in-up animate-delay-300 card-hover',
                showRefreshAnimation
                  ? 'opacity-50 scale-95'
                  : 'opacity-100 scale-100',
              ]"
              :style="{
                transition: showRefreshAnimation
                  ? 'all 0.3s ease-out'
                  : 'all 0.5s ease-in',
              }"
            >
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-gray-400 text-sm font-medium">平均得分</h3>
                <div
                  class="w-10 h-10 rounded-full bg-yellow-500/20 flex items-center justify-center group-hover:bg-yellow-500/30 transition-all duration-300 group-hover:scale-110"
                >
                  <svg
                    class="w-5 h-5 text-yellow-400 group-hover:rotate-12 transition-transform duration-300"
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
              </div>
              <div class="text-3xl font-bold text-white">
                {{ growthData.averageScore }}
              </div>
              <p class="text-xs text-gray-500 mt-1">分</p>
            </div>

            <!-- 成长趋势 -->
            <div
              :class="[
                'bg-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 shadow-lg hover:shadow-purple-500/10 transition-all duration-500 hover:border-purple-500/30 group animate-fade-in-up animate-delay-400 card-hover',
                showRefreshAnimation
                  ? 'opacity-50 scale-95'
                  : 'opacity-100 scale-100',
              ]"
              :style="{
                transition: showRefreshAnimation
                  ? 'all 0.3s ease-out'
                  : 'all 0.5s ease-in',
              }"
            >
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-gray-400 text-sm font-medium">成长趋势</h3>
                <div
                  class="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center group-hover:bg-purple-500/30 transition-all duration-300 group-hover:scale-110"
                >
                  <svg
                    class="w-5 h-5 text-purple-400 group-hover:rotate-12 transition-transform duration-300"
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
                </div>
              </div>
              <div
                class="text-3xl font-bold"
                :class="
                  growthData.improvement >= 0
                    ? 'text-green-400'
                    : 'text-red-400'
                "
              >
                {{ growthData.improvement >= 0 ? "+" : ""
                }}{{ growthData.improvement }}%
              </div>
              <p class="text-xs text-gray-500 mt-1">相比首次面试</p>
            </div>
          </div>
        </section>

        <!-- 能力分析区 -->
        <section class="space-y-6 animate-fade-in-up">
          <h2 class="text-xl font-semibold text-white">能力分析</h2>

          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- 能力成长曲线 -->
            <GrowthCurve
              :data="growthCurveData"
              v-model:timeRange="timeRange"
              title="能力成长曲线"
              class="animate-fade-in-up animate-delay-100"
            />

            <!-- 能力对比图 -->
            <div
              class="bg-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 shadow-lg hover:shadow-green-500/10 transition-all duration-500 card-hover animate-fade-in-up animate-delay-200"
            >
              <h3 class="text-lg font-medium text-white mb-4">能力对比</h3>
              <div class="space-y-4">
                <!-- 沟通表达 -->
                <div>
                  <div class="flex justify-between mb-1">
                    <span class="text-sm text-gray-400">沟通表达</span>
                    <span class="text-sm text-white"
                      >{{ Math.round(abilityProgress.communication) }}%</span
                    >
                  </div>
                  <div class="w-full bg-gray-700/50 rounded-full h-2">
                    <div
                      class="bg-blue-500 h-2 rounded-full transition-all duration-1000 ease-out"
                      :style="{ width: abilityProgress.communication + '%' }"
                    ></div>
                  </div>
                </div>

                <!-- 问题解决 -->
                <div>
                  <div class="flex justify-between mb-1">
                    <span class="text-sm text-gray-400">问题解决</span>
                    <span class="text-sm text-white"
                      >{{ Math.round(abilityProgress.problemSolving) }}%</span
                    >
                  </div>
                  <div class="w-full bg-gray-700/50 rounded-full h-2">
                    <div
                      class="bg-green-500 h-2 rounded-full transition-all duration-1000 ease-out"
                      :style="{ width: abilityProgress.problemSolving + '%' }"
                    ></div>
                  </div>
                </div>

                <!-- 逻辑思维 -->
                <div>
                  <div class="flex justify-between mb-1">
                    <span class="text-sm text-gray-400">逻辑思维</span>
                    <span class="text-sm text-white"
                      >{{ Math.round(abilityProgress.logicalThinking) }}%</span
                    >
                  </div>
                  <div class="w-full bg-gray-700/50 rounded-full h-2">
                    <div
                      class="bg-yellow-500 h-2 rounded-full transition-all duration-1000 ease-out"
                      :style="{ width: abilityProgress.logicalThinking + '%' }"
                    ></div>
                  </div>
                </div>

                <!-- 专业技能 -->
                <div>
                  <div class="flex justify-between mb-1">
                    <span class="text-sm text-gray-400">专业技能</span>
                    <span class="text-sm text-white"
                      >{{
                        Math.round(abilityProgress.professionalSkills)
                      }}%</span
                    >
                  </div>
                  <div class="w-full bg-gray-700/50 rounded-full h-2">
                    <div
                      class="bg-purple-500 h-2 rounded-full transition-all duration-1000 ease-out"
                      :style="{
                        width: abilityProgress.professionalSkills + '%',
                      }"
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 提升建议区 -->
        <section class="space-y-6 animate-fade-in-up">
          <h2 class="text-xl font-semibold text-white">提升建议</h2>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <!-- 薄弱环节 -->
            <div
              class="bg-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 shadow-lg hover:shadow-red-500/10 transition-all duration-500 card-hover animate-fade-in-up animate-delay-100"
            >
              <div class="flex items-center gap-3 mb-4">
                <div
                  class="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center"
                >
                  <svg
                    class="w-5 h-5 text-red-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
                    />
                  </svg>
                </div>
                <h3 class="text-lg font-medium text-white">薄弱环节</h3>
              </div>
              <ul class="space-y-2 text-sm text-gray-300">
                <li
                  v-for="(point, index) in weakPoints"
                  :key="index"
                  class="flex items-center gap-2"
                >
                  <span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>
                  {{ point }}
                </li>
              </ul>
            </div>

            <!-- 改进建议 -->
            <div
              class="bg-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 shadow-lg hover:shadow-blue-500/10 transition-all duration-500 card-hover animate-fade-in-up animate-delay-200"
            >
              <div class="flex items-center gap-3 mb-4">
                <div
                  class="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center"
                >
                  <svg
                    class="w-5 h-5 text-blue-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <h3 class="text-lg font-medium text-white">改进建议</h3>
              </div>
              <ul class="space-y-2 text-sm text-gray-300">
                <li
                  v-for="(suggestion, index) in improvementSuggestions"
                  :key="index"
                  class="flex items-center gap-2"
                >
                  <span class="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
                  {{ suggestion }}
                </li>
              </ul>
            </div>

            <!-- 学习资源 -->
            <div
              class="bg-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 shadow-lg hover:shadow-green-500/10 transition-all duration-500 card-hover animate-fade-in-up animate-delay-300"
            >
              <div class="flex items-center gap-3 mb-4">
                <div
                  class="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center"
                >
                  <svg
                    class="w-5 h-5 text-green-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                    />
                  </svg>
                </div>
                <h3 class="text-lg font-medium text-white">学习资源</h3>
              </div>
              <ul class="space-y-2 text-sm text-gray-300">
                <li
                  v-for="(resource, index) in learningResources"
                  :key="index"
                  class="flex items-center gap-2 hover:text-blue-400 cursor-pointer transition-colors"
                >
                  <span class="w-1.5 h-1.5 rounded-full bg-green-400"></span>
                  {{ resource }}
                </li>
              </ul>
            </div>
          </div>
        </section>
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
