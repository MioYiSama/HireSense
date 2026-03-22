<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { useRouter } from "vue-router";
import {
  getUserInfo,
  getAccessToken,
  setInterviewId,
  setInitialReply,
  clearAll,
} from "@/utils/token";
import { getApiErrorMessage, signOut, startInterview, useInterviewsQuery } from "@/lib/api";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import GrowthCurve from "@/components/GrowthCurve.vue";

const router = useRouter();
const queryClient = useQueryClient();
const showDropdown = ref(false);
let hideTimeout: number | null = null;
let abilityAnimationFrame: number | null = null;

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
    await logoutMutation.mutateAsync();
    clearAll();
    queryClient.clear();
    router.push("/");
  } catch (logoutError) {
    console.error("退出登录错误:", logoutError);
    showMessage(getApiErrorMessage(logoutError, "网络错误，请稍后重试"));
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

const interviewsQuery = useInterviewsQuery();
const logoutMutation = useMutation({
  mutationFn: signOut,
});
const startInterviewMutation = useMutation({
  mutationFn: startInterview,
});

const isLoading = computed(() => startInterviewMutation.isPending.value);
const errorMessage = ref("");

// 面试记录相关
const interviews = computed(() => interviewsQuery.data.value ?? []);
const isLoadingInterviews = computed(() => interviewsQuery.isPending.value);
const interviewsError = computed(() => {
  if (!getAccessToken()) {
    return "请先登录";
  }

  if (interviewsQuery.error.value) {
    return getApiErrorMessage(interviewsQuery.error.value, "获取面试记录失败");
  }

  return "";
});
const isRefreshing = ref(false);
const showRefreshAnimation = ref(false);
const MIN_REPORTS_FOR_ANALYSIS = 3;

type AbilityProgressState = {
  communication: number;
  adaptability: number;
  logicalThinking: number;
  professionalSkills: number;
};

type AbilityInsight = {
  name: string;
  averageScore: number;
  sampleCount: number;
  source: "general" | "specific";
};

const createEmptyAbilityProgress = (): AbilityProgressState => ({
  communication: 0,
  adaptability: 0,
  logicalThinking: 0,
  professionalSkills: 0,
});

const getAverage = (values: number[]) => {
  if (values.length === 0) {
    return 0;
  }

  return values.reduce((total, value) => total + value, 0) / values.length;
};

const parseScore = (value: unknown) => {
  const score = Number(value);
  return Number.isFinite(score) ? score : null;
};

const pushScore = (bucket: number[], value: unknown) => {
  const score = parseScore(value);
  if (score !== null) {
    bucket.push(score);
  }
};

const rankReportTexts = (values: unknown[]) => {
  const buckets = new Map<string, { count: number; firstSeen: number }>();

  values.forEach((value, index) => {
    const text = String(value ?? "").trim();
    if (!text) {
      return;
    }

    const current = buckets.get(text);
    if (current) {
      current.count += 1;
      return;
    }

    buckets.set(text, { count: 1, firstSeen: index });
  });

  return [...buckets.entries()]
    .sort((left, right) => {
      if (right[1].count !== left[1].count) {
        return right[1].count - left[1].count;
      }

      return left[1].firstSeen - right[1].firstSeen;
    })
    .map(([text]) => text);
};

const FIXED_GUIDANCE_BY_ABILITY: Record<
  string,
  { weakPoint: string; suggestion: string; resource: string }
> = {
  沟通表达: {
    weakPoint: "沟通表达维度持续偏弱，回答还可以更精炼、更有结构。",
    suggestion: "用 STAR 结构重写项目经历，并通过录音复盘是否做到结论前置。",
    resource: "STAR 项目表达复盘清单",
  },
  逻辑思维: {
    weakPoint: "逻辑思维维度偏弱，分析问题时还需要更清晰的拆解路径。",
    suggestion: "练习按“结论-分析-方案-权衡”结构回答开放题，减少跳步表达。",
    resource: "结构化拆题练习题单",
  },
  应变能力: {
    weakPoint: "应变能力偏弱，面对追问和临场变化时稳定性不足。",
    suggestion: "补充高频追问场景演练，先澄清问题边界再给出取舍方案。",
    resource: "高频追问场景演练清单",
  },
  自信度: {
    weakPoint: "自信度维度偏弱，表达时容易犹豫或反复修正。",
    suggestion: "回答时先亮结论和依据，再展开细节，降低口头重复和迟疑。",
    resource: "高压面试表达训练卡",
  },
  学习能力: {
    weakPoint: "学习能力维度有待加强，缺少把新知识快速转成实践成果的证明。",
    suggestion: "准备 2 到 3 个“学习新技术并落地”的案例，突出学习路径和业务结果。",
    resource: "技术学习案例整理模板",
  },
  团队协同: {
    weakPoint: "团队协同维度偏弱，协作推进和冲突处理案例还不够扎实。",
    suggestion: "补充跨团队协作案例，明确角色分工、冲突处理和推进结果。",
    resource: "协作冲突复盘模板",
  },
  设计: {
    weakPoint: "设计维度评分偏低，系统化设计思路还不够完整。",
    suggestion: "围绕页面架构、组件抽象和交互方案准备成体系的设计说明。",
    resource: "前端架构设计复盘清单",
  },
  性能: {
    weakPoint: "性能维度评分偏低，性能瓶颈定位和优化手段需要继续强化。",
    suggestion: "梳理性能优化案例，回答时明确指标、瓶颈、方案和收益。",
    resource: "性能优化案例清单",
  },
  工程化: {
    weakPoint: "工程化维度评分偏低，流程规范和质量保障能力有待加强。",
    suggestion: "准备构建、测试、发布和规范治理的真实案例，强调提效结果。",
    resource: "前端工程化专题题单",
  },
  组件化: {
    weakPoint: "组件化维度评分偏低，复用设计和边界抽象还不够清晰。",
    suggestion: "复盘通用组件设计，重点准备接口边界、可扩展性和维护成本取舍。",
    resource: "组件设计问答清单",
  },
  数据流: {
    weakPoint: "数据流维度评分偏低，状态管理和复杂交互建模仍需加强。",
    suggestion: "整理复杂状态流转案例，讲清数据来源、更新机制和异常处理。",
    resource: "状态管理与数据流专题",
  },
  安全: {
    weakPoint: "安全维度评分偏低，常见安全风险及防护策略掌握不够扎实。",
    suggestion: "重点复习常见安全风险和防护方案，并准备项目里的安全实践案例。",
    resource: "应用安全高频问答清单",
  },
  分布式: {
    weakPoint: "分布式维度评分偏低，系统拆分和一致性设计仍需补强。",
    suggestion: "补充分布式场景案例，回答时说明拆分依据、容错和一致性方案。",
    resource: "分布式系统面试题单",
  },
  数据库: {
    weakPoint: "数据库维度评分偏低，建模、索引和事务取舍还不够扎实。",
    suggestion: "准备数据库优化案例，重点说明建模、索引策略和故障排查过程。",
    resource: "数据库优化复盘清单",
  },
  API: {
    weakPoint: "API 维度评分偏低，接口设计和稳定性治理能力还需加强。",
    suggestion: "复盘接口设计案例，明确版本管理、幂等、容错和监控策略。",
    resource: "API 设计与治理题单",
  },
  DevOps: {
    weakPoint: "DevOps 维度评分偏低，交付链路和运维协作经验还不够具体。",
    suggestion: "补充 CI/CD、发布回滚和监控告警的实战案例，突出质量闭环。",
    resource: "DevOps 实战问答清单",
  },
};

const getFixedGuidance = (name: string) => {
  return (
    FIXED_GUIDANCE_BY_ABILITY[name] ?? {
      weakPoint: `${name}维度评分偏低，需要继续补强相关知识和案例表达。`,
      suggestion: `围绕${name}补充核心概念、项目案例和常见追问练习。`,
      resource: `${name}专项复盘清单`,
    }
  );
};

// 刷新面试数据
const refreshInterviews = async () => {
  // 开始刷新动画
  isRefreshing.value = true;
  showRefreshAnimation.value = true;

  try {
    await fetchInterviews();
  } catch (error) {
    console.error("刷新面试记录失败:", error);
  } finally {
    // 结束刷新动画
    showRefreshAnimation.value = false;
    // 稍微延迟后恢复按钮状态，让用户有足够时间看到动画
    setTimeout(() => {
      isRefreshing.value = false;
    }, 100);
  }
};

// 个人成长数据
const growthData = computed(() => {
  const { completedInterviews, scores } = commonComputedData.value;
  const firstScore = scores[0];
  const lastScore = scores[scores.length - 1];
  const improvement =
    scores.length > 2 && firstScore !== undefined && firstScore > 0 && lastScore !== undefined
      ? Math.round(((lastScore - firstScore) * 100) / firstScore)
      : null;

  return {
    totalInterviews: interviews.value.length,
    completedInterviews: completedInterviews.length,
    averageScore:
      scores.length > 0 ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0,
    highestScore: scores.length > 0 ? Math.max(...scores) : 0,
    improvement,
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

  return filteredData;
});

// 通用计算数据，避免重复计算
const commonComputedData = computed(() => {
  const completedInterviews = interviews.value
    .filter((item) => item.report)
    .sort((a, b) => {
      const timeA = new Date(a.created_at || 0).getTime();
      const timeB = new Date(b.created_at || 0).getTime();
      return timeA - timeB;
    });
  const scores = completedInterviews
    .map((item) => parseScore(item.report?.score))
    .filter((score): score is number => score !== null);

  return {
    completedInterviews,
    scores,
  };
});

const hasEnoughReportsForAnalysis = computed(() => {
  return commonComputedData.value.completedInterviews.length > 2;
});

const hasEnoughGrowthCurveData = computed(() => {
  return growthCurveData.value.length > 2;
});

const growthCurveEmptyMessage = computed(() => {
  if (!hasEnoughReportsForAnalysis.value) {
    return `至少需要 ${MIN_REPORTS_FOR_ANALYSIS} 份已生成面试报告后才展示成长曲线，当前为 ${commonComputedData.value.completedInterviews.length} 份。`;
  }

  return `当前所选时间范围内仅有 ${growthCurveData.value.length} 份已生成面试报告，暂时无法展示可靠趋势。`;
});

// 时间范围选择
const timeRange = ref("30"); // 默认近30天

// 能力对比进度条数据
const abilityProgress = ref<AbilityProgressState>(createEmptyAbilityProgress());

const abilityTargetProgress = computed<AbilityProgressState>(() => {
  if (!hasEnoughReportsForAnalysis.value) {
    return createEmptyAbilityProgress();
  }

  const communicationScores: number[] = [];
  const adaptabilityScores: number[] = [];
  const logicalThinkingScores: number[] = [];
  const professionalSkillScores: number[] = [];

  commonComputedData.value.completedInterviews.forEach((item) => {
    const report = item.report;

    if (!report) {
      return;
    }

    pushScore(communicationScores, report.general?.["沟通表达"]);
    pushScore(adaptabilityScores, report.general?.["应变能力"]);
    pushScore(logicalThinkingScores, report.general?.["逻辑思维"]);
    Object.values(report.specific ?? {}).forEach((score) => {
      pushScore(professionalSkillScores, score);
    });
  });

  return {
    communication: Math.round(getAverage(communicationScores) * 10),
    adaptability: Math.round(getAverage(adaptabilityScores) * 10),
    logicalThinking: Math.round(getAverage(logicalThinkingScores) * 10),
    professionalSkills: Math.round(getAverage(professionalSkillScores) * 10),
  };
});

const abilityComparisonEmptyMessage = computed(() => {
  return `至少需要 ${MIN_REPORTS_FOR_ANALYSIS} 份已生成面试报告后才展示能力对比，当前为 ${commonComputedData.value.completedInterviews.length} 份。`;
});

const hasAdviceData = computed(() => {
  return commonComputedData.value.completedInterviews.length > 0;
});

const adviceEmptyMessage = "至少需要 1 份已生成面试报告后才展示提升建议。";

const historicalAbilityInsights = computed<AbilityInsight[]>(() => {
  const buckets = new Map<
    string,
    { total: number; count: number; source: "general" | "specific" }
  >();

  commonComputedData.value.completedInterviews.forEach((item) => {
    const report = item.report;
    if (!report) {
      return;
    }

    Object.entries(report.general ?? {}).forEach(([name, score]) => {
      const parsedScore = parseScore(score);
      if (parsedScore === null) {
        return;
      }

      const current = buckets.get(name) ?? { total: 0, count: 0, source: "general" as const };
      current.total += parsedScore;
      current.count += 1;
      current.source = "general";
      buckets.set(name, current);
    });

    Object.entries(report.specific ?? {}).forEach(([name, score]) => {
      const parsedScore = parseScore(score);
      if (parsedScore === null) {
        return;
      }

      const current = buckets.get(name) ?? { total: 0, count: 0, source: "specific" as const };
      current.total += parsedScore;
      current.count += 1;
      current.source = "specific";
      buckets.set(name, current);
    });
  });

  return [...buckets.entries()]
    .map(([name, bucket]) => ({
      name,
      averageScore: bucket.total / bucket.count,
      sampleCount: bucket.count,
      source: bucket.source,
    }))
    .sort((left, right) => {
      if (left.averageScore !== right.averageScore) {
        return left.averageScore - right.averageScore;
      }

      return left.name.localeCompare(right.name, "zh-CN");
    });
});

const focusAbilities = computed(() => {
  const lowerScoreAbilities = historicalAbilityInsights.value.filter(
    (item) => item.averageScore < 8.5,
  );
  return (
    lowerScoreAbilities.length > 0 ? lowerScoreAbilities : historicalAbilityInsights.value
  ).slice(0, 3);
});

const extractedWeakPoints = computed(() => {
  const shortcomings = commonComputedData.value.completedInterviews.flatMap((item) => {
    return item.report?.shortcomings ?? [];
  });

  return rankReportTexts(shortcomings);
});

const extractedResources = computed(() => {
  const resources = commonComputedData.value.completedInterviews.flatMap((item) => {
    return item.report?.resources ?? [];
  });

  return rankReportTexts(resources);
});

// 分析面试报告中的薄弱点
const weakPoints = computed(() => {
  if (!hasAdviceData.value) {
    return [];
  }

  if (extractedWeakPoints.value.length > 0) {
    return extractedWeakPoints.value.slice(0, 3);
  }

  if (focusAbilities.value.length === 0) {
    return [];
  }

  const lowScoreWeakPoints = focusAbilities.value
    .filter((item) => item.averageScore < 8.5)
    .map((item) => {
      if (item.averageScore < 7) {
        return getFixedGuidance(item.name).weakPoint;
      }

      return `${item.name}维度仍有提升空间，最近报告均分 ${item.averageScore.toFixed(1)} / 10。`;
    });

  if (lowScoreWeakPoints.length > 0) {
    return lowScoreWeakPoints.slice(0, 3);
  }

  return ["近几次历史报告未发现明确的薄弱环节"];
});

// 生成针对性的改进建议
const improvementSuggestions = computed(() => {
  if (!hasAdviceData.value || focusAbilities.value.length === 0) {
    return [];
  }

  return focusAbilities.value
    .map((item) => {
      if (item.averageScore >= 8.5) {
        return `当前${item.name}表现稳定，继续通过模拟面试和复盘保持答题质量。`;
      }

      return getFixedGuidance(item.name).suggestion;
    })
    .filter((suggestion, index, suggestions) => {
      return suggestions.indexOf(suggestion) === index;
    })
    .slice(0, 3);
});

// 生成学习资源建议
const learningResources = computed(() => {
  if (!hasAdviceData.value) {
    return [];
  }

  const resources = [...extractedResources.value];

  focusAbilities.value.forEach((item) => {
    const fixedResource = getFixedGuidance(item.name).resource;
    if (!resources.includes(fixedResource)) {
      resources.push(fixedResource);
    }
  });

  return resources.slice(0, 3);
});

// 时间格式化函数
const formatInterviewTime = (timestamp: any): string => {
  try {
    // 确保时间戳是数字类型
    const ts = typeof timestamp === "string" ? parseInt(timestamp, 10) : timestamp;
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
  "Meta",
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
  if (!getAccessToken()) {
    return;
  }

  await interviewsQuery.refetch();
};

const startNewInterview = async () => {
  // 显示加载状态
  errorMessage.value = "";

  try {
    // 从localStorage获取token
    const token = getAccessToken();

    if (!token) {
      errorMessage.value = "请先登录";
      setTimeout(() => {
        errorMessage.value = "";
      }, 3000);
      return;
    }

    const data = await startInterviewMutation.mutateAsync();

    if (data.id) {
      setInterviewId(data.id);
      if (data.reply) {
        setInitialReply(data.reply);
      }
      void fetchInterviews();
      router.push("/interview");
    }
  } catch (error) {
    console.error("启动面试失败:", error);
    errorMessage.value = getApiErrorMessage(error, "网络错误，请稍后重试");
    setTimeout(() => {
      errorMessage.value = "";
    }, 3000);
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

const animateAbilityProgress = (targetProgress: AbilityProgressState) => {
  if (abilityAnimationFrame) {
    cancelAnimationFrame(abilityAnimationFrame);
    abilityAnimationFrame = null;
  }

  const duration = 1500;
  const startTime = performance.now();

  const animate = (currentTime: number) => {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const easeOutQuart = 1 - Math.pow(1 - progress, 4);

    abilityProgress.value = {
      communication: targetProgress.communication * easeOutQuart,
      adaptability: targetProgress.adaptability * easeOutQuart,
      logicalThinking: targetProgress.logicalThinking * easeOutQuart,
      professionalSkills: targetProgress.professionalSkills * easeOutQuart,
    };

    if (progress < 1) {
      abilityAnimationFrame = requestAnimationFrame(animate);
      return;
    }

    abilityAnimationFrame = null;
  };

  abilityAnimationFrame = requestAnimationFrame(animate);
};

watch(
  abilityTargetProgress,
  (targetProgress) => {
    if (!hasEnoughReportsForAnalysis.value) {
      if (abilityAnimationFrame) {
        cancelAnimationFrame(abilityAnimationFrame);
        abilityAnimationFrame = null;
      }
      abilityProgress.value = createEmptyAbilityProgress();
      return;
    }

    animateAbilityProgress(targetProgress);
  },
  { immediate: true },
);

onMounted(() => {
  // 从localStorage获取用户信息
  const userInfo = getUserInfo();
  if (userInfo && userInfo.name) {
    name.value = userInfo.name;
  }

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
  if (abilityAnimationFrame) {
    cancelAnimationFrame(abilityAnimationFrame);
  }
});
</script>

<template>
  <div
    class="min-h-screen bg-linear-to-br from-gray-900 via-gray-800 to-gray-900 relative overflow-hidden"
  >
    <!-- 背景 -->
    <div class="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl"></div>
    <div class="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl"></div>

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
            <img src="/favicon.png" alt="HireSense" class="h-8 w-8 rounded-md object-contain" />
            <span class="text-xl font-bold text-white tracking-tight">Hire Sense</span>
          </div>
        </button>
      </div>
      <div class="flex-none">
        <!-- 用户菜单 -->
        <div class="user-menu relative" @mouseenter="showMenu" @mouseleave="hideMenu">
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
            <span class="text-xs text-slate-400 bg-gray-800/50 px-2 py-1 rounded-full"
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
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
              <span>{{ interviewsError }}</span>
            </div>
            <button @click="fetchInterviews" class="mt-2 text-sm text-blue-400 hover:underline">
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
              showRefreshAnimation ? 'opacity-50 scale-95' : 'opacity-100 scale-100',
            ]"
            :style="{
              transition: showRefreshAnimation ? 'all 0.3s ease-out' : 'all 0.5s ease-in',
            }"
          >
            <!-- 面试记录项 -->
            <div
              v-for="interview in interviews"
              :key="interview.id"
              @click="interview.report && router.push(`/interview/${interview.id}/report`)"
              :class="[
                'p-4 rounded-xl border-l-2 group transition-all duration-200',
                interview.report
                  ? 'border-transparent cursor-pointer hover:border-blue-500/50 hover:bg-gray-800/30'
                  : 'border-gray-700/30 opacity-70 cursor-not-allowed',
              ]"
            >
              <div class="flex items-start justify-between mb-2">
                <!-- <span class="text-xs text-blue-400 bg-blue-500/10 px-2 py-1 rounded-lg">{{
                  interview.report
                    ? interview.report.specific
                      ? "前端开发工程师"
                      : "后端开发工程师"
                    : "面试"
                }}</span> -->
                <span class="text-xs text-slate-500">{{
                  formatInterviewTime(interview.created_at)
                }}</span>
              </div>
              <h3
                class="font-medium text-white text-sm mb-1 group-hover:text-blue-300 transition-colors"
              >
                <strong>{{ getRandomCompanyName(interview.id) }}</strong
                >面试
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
                    interview.report
                      ? interview.report.score.toFixed(2) + "分"
                      : interview.status === "started"
                        ? "进行中"
                        : "已结束"
                  }}</span>
                </div>
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
                showRefreshAnimation ? 'opacity-50 scale-95' : 'opacity-100 scale-100',
              ]"
              :style="{
                transition: showRefreshAnimation ? 'all 0.3s ease-out' : 'all 0.5s ease-in',
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
                showRefreshAnimation ? 'opacity-50 scale-95' : 'opacity-100 scale-100',
              ]"
              :style="{
                transition: showRefreshAnimation ? 'all 0.3s ease-out' : 'all 0.5s ease-in',
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
                showRefreshAnimation ? 'opacity-50 scale-95' : 'opacity-100 scale-100',
              ]"
              :style="{
                transition: showRefreshAnimation ? 'all 0.3s ease-out' : 'all 0.5s ease-in',
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
                showRefreshAnimation ? 'opacity-50 scale-95' : 'opacity-100 scale-100',
              ]"
              :style="{
                transition: showRefreshAnimation ? 'all 0.3s ease-out' : 'all 0.5s ease-in',
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
                  growthData.improvement === null
                    ? 'text-slate-300'
                    : growthData.improvement >= 0
                      ? 'text-green-400'
                      : 'text-red-400'
                "
              >
                {{
                  growthData.improvement === null
                    ? "数据不足"
                    : `${growthData.improvement >= 0 ? "+" : ""}${growthData.improvement}%`
                }}
              </div>
              <p class="text-xs text-gray-500 mt-1">
                {{
                  growthData.improvement === null
                    ? `至少需要 ${MIN_REPORTS_FOR_ANALYSIS} 份已生成报告`
                    : "相比首次面试"
                }}
              </p>
            </div>
          </div>
        </section>

        <!-- 能力分析区 -->
        <section class="space-y-6 animate-fade-in-up">
          <h2 class="text-xl font-semibold text-white">能力分析</h2>

          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- 能力成长曲线 -->
            <GrowthCurve
              v-if="hasEnoughGrowthCurveData"
              :data="growthCurveData"
              v-model:timeRange="timeRange"
              title="能力成长曲线"
              class="animate-fade-in-up animate-delay-100"
            />
            <div
              v-else
              class="bg-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 shadow-lg transition-all duration-500 card-hover animate-fade-in-up animate-delay-100"
            >
              <div class="flex items-center justify-between mb-6">
                <h3 class="text-lg font-medium text-white">能力成长曲线</h3>
                <span class="text-xs text-slate-400">数据不足</span>
              </div>
              <div
                class="h-64 rounded-xl border border-dashed border-gray-700/60 bg-gray-900/30 px-6 flex flex-col items-center justify-center text-center"
              >
                <div
                  class="w-12 h-12 rounded-full bg-cyan-500/10 text-cyan-300 flex items-center justify-center mb-4"
                >
                  <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="1.8"
                      d="M3 17l6-6 4 4 7-8"
                    />
                  </svg>
                </div>
                <p class="text-sm font-medium text-white">暂时无法生成可靠成长曲线</p>
                <p class="text-xs text-slate-400 mt-2 max-w-sm">
                  {{ growthCurveEmptyMessage }}
                </p>
              </div>
            </div>

            <!-- 能力对比图 -->
            <div
              class="bg-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 shadow-lg hover:shadow-green-500/10 transition-all duration-500 card-hover animate-fade-in-up animate-delay-200"
            >
              <h3 class="text-lg font-medium text-white mb-4">能力对比</h3>
              <div v-if="hasEnoughReportsForAnalysis" class="space-y-4">
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
                    <span class="text-sm text-gray-400">应变能力</span>
                    <span class="text-sm text-white"
                      >{{ Math.round(abilityProgress.adaptability) }}%</span
                    >
                  </div>
                  <div class="w-full bg-gray-700/50 rounded-full h-2">
                    <div
                      class="bg-green-500 h-2 rounded-full transition-all duration-1000 ease-out"
                      :style="{ width: abilityProgress.adaptability + '%' }"
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
                      >{{ Math.round(abilityProgress.professionalSkills) }}%</span
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
              <div
                v-else
                class="h-64 rounded-xl border border-dashed border-gray-700/60 bg-gray-900/30 px-6 flex flex-col items-center justify-center text-center"
              >
                <div
                  class="w-12 h-12 rounded-full bg-green-500/10 text-green-300 flex items-center justify-center mb-4"
                >
                  <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="1.8"
                      d="M9 17v-6m3 6V7m3 10v-3m3 3V5M3 19h18"
                    />
                  </svg>
                </div>
                <p class="text-sm font-medium text-white">暂时无法生成可靠能力对比</p>
                <p class="text-xs text-slate-400 mt-2 max-w-sm">
                  {{ abilityComparisonEmptyMessage }}
                </p>
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
                <div class="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center">
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
              <ul v-if="weakPoints.length > 0" class="space-y-2 text-sm text-gray-300">
                <li
                  v-for="(point, index) in weakPoints"
                  :key="index"
                  class="flex items-center gap-2"
                >
                  <span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>
                  {{ point }}
                </li>
              </ul>
              <p v-else class="text-sm text-slate-400">
                {{ adviceEmptyMessage }}
              </p>
            </div>

            <!-- 改进建议 -->
            <div
              class="bg-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 shadow-lg hover:shadow-blue-500/10 transition-all duration-500 card-hover animate-fade-in-up animate-delay-200"
            >
              <div class="flex items-center gap-3 mb-4">
                <div class="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
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
              <ul v-if="improvementSuggestions.length > 0" class="space-y-2 text-sm text-gray-300">
                <li
                  v-for="(suggestion, index) in improvementSuggestions"
                  :key="index"
                  class="flex items-center gap-2"
                >
                  <span class="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
                  {{ suggestion }}
                </li>
              </ul>
              <p v-else class="text-sm text-slate-400">
                {{ adviceEmptyMessage }}
              </p>
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
              <ul v-if="learningResources.length > 0" class="space-y-2 text-sm text-gray-300">
                <li
                  v-for="(resource, index) in learningResources"
                  :key="index"
                  class="flex items-center gap-2"
                >
                  <span class="w-1.5 h-1.5 rounded-full bg-green-400"></span>
                  {{ resource }}
                </li>
              </ul>
              <p v-else class="text-sm text-slate-400">
                {{ adviceEmptyMessage }}
              </p>
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
