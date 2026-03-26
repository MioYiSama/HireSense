<script setup lang="ts">
import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import type { Profile, ProfileJobEnum } from "@/api";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import {
  generateResumeAnalysis,
  getApiErrorMessage,
  queryKeys,
  signOut,
  updateProfile,
  useProfileQuery,
  useResumeAnalysisQuery,
} from "@/lib/api";
import { formatResumeAnalysisTime } from "@/lib/resumeAnalysis";
import { clearAll, getUserInfo } from "@/utils/token";

const router = useRouter();
const queryClient = useQueryClient();
const showDropdown = ref(false);
let hideTimeout: number | null = null;

const interviewerStyles = [
  { value: "default", label: "默认" },
  { value: "professional", label: "专业严肃" },
  { value: "friendly", label: "亲和温和" },
  { value: "challenging", label: "挑战性" },
  { value: "custom", label: "自定义" },
] as const;

type InterviewerStyle = (typeof interviewerStyles)[number]["value"];

const storedUserInfo = getUserInfo();
const name = ref(storedUserInfo?.name || "奶龙");
const job = ref<ProfileJobEnum>((storedUserInfo?.job as ProfileJobEnum | undefined) || "frontend");
const resumeFile = ref<File | null>(null);
const resumeFileName = ref("");
const resumeText = ref("");
const parseLoading = ref(false);
const parseError = ref("");
const personalization = ref<{ interviewerStyle: InterviewerStyle }>({
  interviewerStyle: "default",
});
let messageTimeout: number | null = null;
let fileParserPromise: Promise<typeof import("@/utils/fileParser")> | null = null;

const customStyle = ref("");
const saveMessage = ref("");
const saveSuccess = ref(false);
const showLogoutDialog = ref(false);

const profileQuery = useProfileQuery();
const resumeAnalysisQuery = useResumeAnalysisQuery();
const logoutMutation = useMutation({
  mutationFn: signOut,
});
const saveProfileMutation = useMutation({
  mutationFn: updateProfile,
  onSuccess: (profile) => {
    queryClient.setQueryData(queryKeys.profile(), profile);
  },
});
const generateResumeAnalysisMutation = useMutation({
  mutationFn: generateResumeAnalysis,
  onSuccess: (analysis) => {
    queryClient.setQueryData(queryKeys.resumeAnalysis(), analysis);
  },
});

const profileLoading = computed(() => profileQuery.isFetching.value);
const loading = computed(() => saveProfileMutation.isPending.value);
const analysisLoading = computed(() => generateResumeAnalysisMutation.isPending.value);
const hasResumeAnalysis = computed(() => Boolean(resumeAnalysisQuery.data.value));
const resumeAnalysisUpdatedAt = computed(() => {
  const generatedAt = resumeAnalysisQuery.data.value?.generated_at;
  if (!generatedAt) {
    return "";
  }

  return formatResumeAnalysisTime(generatedAt);
});

// 错误消息处理函数
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

const loadFileParser = async () => {
  if (!fileParserPromise) {
    fileParserPromise = import("@/utils/fileParser");
  }

  return fileParserPromise;
};

const isInterviewerStyle = (value: string): value is InterviewerStyle => {
  return interviewerStyles.some((style) => style.value === value);
};

const applyPersonalization = (value?: string) => {
  const savedPersonalization = value?.trim() || "";

  if (!savedPersonalization) {
    personalization.value.interviewerStyle = "default";
    customStyle.value = "";
    return;
  }

  if (isInterviewerStyle(savedPersonalization)) {
    personalization.value.interviewerStyle = savedPersonalization;
    customStyle.value = "";
    return;
  }

  personalization.value.interviewerStyle = "custom";
  customStyle.value = savedPersonalization;
};

const buildPersonalization = () => {
  if (personalization.value.interviewerStyle === "custom") {
    return customStyle.value.trim();
  }

  return personalization.value.interviewerStyle;
};

const buildProfilePayload = (): Profile => {
  return {
    name: name.value.trim(),
    job: job.value,
    resume: resumeText.value.trim(),
    personalization: buildPersonalization(),
  };
};

const applyProfile = (profile: Profile) => {
  name.value = profile.name;
  job.value = profile.job;
  resumeFile.value = null;
  resumeFileName.value = profile.resume ? "已保存的简历内容" : "";
  resumeText.value = profile.resume ?? "";
  parseError.value = "";
  applyPersonalization(profile.personalization);
};

applyPersonalization(storedUserInfo?.personalization);
if (storedUserInfo?.resume) {
  resumeFileName.value = "已保存的简历内容";
  resumeText.value = storedUserInfo.resume;
}

watch(
  () => profileQuery.data.value,
  (profile) => {
    if (profile) {
      applyProfile(profile);
    }
  },
  { immediate: true },
);

watch(
  () => profileQuery.error.value,
  (error) => {
    if (error) {
      console.error("获取档案错误:", error);
      showMessage(getApiErrorMessage(error, "获取最新档案失败，请稍后重试"));
    }
  },
);

const handleLogout = async () => {
  showLogoutDialog.value = true;
};

const confirmLogout = async () => {
  showLogoutDialog.value = false;

  if (messageTimeout) {
    clearTimeout(messageTimeout);
    messageTimeout = null;
  }

  try {
    await logoutMutation.mutateAsync();
    clearAll();
    queryClient.clear();
    router.push("/signin");
  } catch (logoutError) {
    console.error("退出登录错误:", logoutError);
    showMessage(getApiErrorMessage(logoutError, "网络错误，请稍后重试"));
  }
};

const cancelLogout = () => {
  showLogoutDialog.value = false;
};

const goToDashboard = () => {
  router.push("/dashboard");
};

const goToProfile = () => {
  router.push("/profile");
};

const showMenu = () => {
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

const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    const file = target.files[0];
    if (file) {
      resumeFile.value = file;
      resumeFileName.value = file.name;
      parseError.value = "";
      parseLoading.value = true;

      console.log("上传的文件:", file);

      try {
        const { parseFile } = await loadFileParser();
        const result = await parseFile(file);

        if (result.success) {
          resumeText.value = result.text;
          console.log("文件解析成功，文本长度:", result.text.length);
        } else {
          parseError.value = result.error || "文件解析失败";
          console.error("文件解析失败:", result.error);
        }
      } catch (error) {
        parseError.value = "文件解析过程中发生错误";
        console.error("文件解析异常:", error);
      } finally {
        parseLoading.value = false;
      }
    }
  }
};

const handleRemoveFile = () => {
  resumeFile.value = null;
  resumeFileName.value = "";
  resumeText.value = "";
  parseError.value = "";
  console.log("移除文件");
};

const persistProfile = async () => {
  const nextProfile = buildProfilePayload();
  const previousProfile = profileQuery.data.value;
  const shouldResetResumeAnalysis =
    (previousProfile?.job ?? "") !== nextProfile.job ||
    (previousProfile?.resume ?? "") !== nextProfile.resume;

  const savedProfile = await saveProfileMutation.mutateAsync(nextProfile);

  if (shouldResetResumeAnalysis) {
    queryClient.setQueryData(queryKeys.resumeAnalysis(), null);
  }

  return savedProfile;
};

const handleSave = async () => {
  if (messageTimeout) {
    clearTimeout(messageTimeout);
    messageTimeout = null;
  }

  if (!name.value || !job.value) {
    showMessage("请填写姓名和期望职位");
    return;
  }

  saveMessage.value = "";

  try {
    await persistProfile();
    showMessage("档案更新成功", true);
  } catch (saveError) {
    console.error("更新档案错误:", saveError);
    showMessage(getApiErrorMessage(saveError, "网络错误，请稍后重试"));
  }
};

const goToResumeAnalysis = () => {
  router.push("/resume-analysis");
};

const handleAnalyzeResume = async () => {
  if (messageTimeout) {
    clearTimeout(messageTimeout);
    messageTimeout = null;
  }

  if (!name.value || !job.value) {
    showMessage("请填写姓名和期望职位");
    return;
  }

  if (!resumeText.value.trim()) {
    showMessage("请先上传或粘贴简历内容");
    return;
  }

  saveMessage.value = "";

  try {
    await persistProfile();
    const analysis = await generateResumeAnalysisMutation.mutateAsync();
    queryClient.setQueryData(queryKeys.resumeAnalysis(), analysis);
    router.push("/resume-analysis");
  } catch (error) {
    console.error("生成简历分析错误:", error);
    showMessage(getApiErrorMessage(error, "生成简历分析失败，请稍后重试"));
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
    class="relative min-h-screen overflow-hidden bg-linear-to-br from-gray-900 via-gray-800 to-gray-900"
  >
    <!-- 背景 -->
    <div class="absolute top-0 left-1/4 h-96 w-96 rounded-full bg-blue-500/10 blur-3xl"></div>
    <div class="absolute right-1/4 bottom-0 h-96 w-96 rounded-full bg-purple-500/10 blur-3xl"></div>

    <!-- 导航栏 -->
    <div
      class="navbar relative z-10 border-b border-gray-700/50 bg-gray-900/60 shadow-lg backdrop-blur-md"
    >
      <div class="flex-1">
        <button
          @click="goToDashboard"
          class="group relative flex cursor-pointer items-center gap-2 overflow-hidden rounded-lg border border-gray-700/50 bg-gray-800/50 px-4 py-2 text-sm text-gray-300 transition-all duration-300 hover:bg-gray-700/50 hover:text-white hover:shadow-lg hover:shadow-blue-500/10"
        >
          <!-- 正常状态：返回按钮 -->
          <div
            class="flex items-center gap-2 transition-all duration-300 group-hover:translate-x-[-150%]"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            <span>返回面试中心</span>
          </div>

          <!-- 悬停状态：Logo -->
          <div
            class="absolute top-0 left-0 flex h-full items-center gap-2 px-4 opacity-0 transition-all duration-300 group-hover:translate-x-0 group-hover:opacity-100"
          >
            <img src="/favicon.png" alt="HireSense" class="h-6 w-6 rounded-md object-contain" />
            <span class="text-sm font-bold tracking-tight text-white">Hire Sense</span>
          </div>
        </button>
      </div>
      <div class="flex-none">
        <!-- 用户菜单 -->
        <div class="user-menu relative" @mouseenter="showMenu" @mouseleave="hideMenu">
          <button
            class="flex h-10 w-10 cursor-pointer items-center justify-center rounded-full border border-gray-600 bg-gray-800/50 transition-all duration-300 hover:bg-gray-700/50 hover:shadow-lg hover:shadow-blue-500/10"
          >
            <div
              class="flex h-8 w-8 items-center justify-center rounded-full bg-linear-to-br from-blue-500 to-purple-600 font-medium text-white"
            >
              {{ name?.[0] || "用" }}
            </div>
          </button>

          <!-- 下拉菜单 -->
          <div
            v-if="showDropdown"
            class="absolute right-0 z-50 mt-1 w-48 origin-top-right transform rounded-xl border border-gray-700/50 bg-gray-900/95 py-2 shadow-2xl shadow-blue-500/10 backdrop-blur-md transition-all duration-300"
            @mouseenter="showMenu"
            @mouseleave="hideMenu"
          >
            <button
              @click="goToProfile"
              class="flex w-full items-center gap-2 rounded-lg px-4 py-2 text-left text-sm text-gray-300 transition-all duration-200 hover:translate-x-1 hover:bg-gray-700/50 hover:text-white"
            >
              <svg
                class="h-4 w-4 transition-transform duration-200 hover:scale-110"
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
              class="flex w-full items-center gap-2 rounded-lg px-4 py-2 text-left text-sm text-gray-300 transition-all duration-200 hover:translate-x-1 hover:bg-gray-700/50 hover:text-white"
            >
              <svg
                class="h-4 w-4 transition-transform duration-200 hover:scale-110"
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

    <!-- 主内容 -->
    <div class="relative z-10 container mx-auto p-8">
      <h1 class="mb-8 text-3xl font-bold text-white">个人中心</h1>

      <div class="mx-auto max-w-4xl space-y-6">
        <!-- 基本信息 -->
        <div
          v-if="profileLoading"
          class="rounded-xl border border-blue-500/20 bg-blue-500/10 px-4 py-3 text-sm text-blue-200"
        >
          正在同步后端最新档案...
        </div>

        <div
          class="rounded-2xl border border-gray-700/50 bg-gray-900/60 p-6 shadow-2xl shadow-blue-500/10 backdrop-blur-md"
        >
          <h2 class="mb-6 flex items-center gap-2 text-xl font-semibold text-white">
            <svg
              class="h-5 w-5 text-blue-400"
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
            基本信息
          </h2>

          <div class="grid grid-cols-1 gap-6 md:grid-cols-2">
            <div class="form-control">
              <label class="label mb-2">
                <span class="label-text font-medium text-gray-300"
                  >姓名 <span class="text-red-400">*</span></span
                >
              </label>
              <input
                v-model="name"
                type="text"
                placeholder="请输入姓名"
                class="input input-bordered min-h-14 w-full rounded-lg border-gray-600 bg-gray-800/50 px-4 py-3 text-white placeholder-gray-400 transition-all duration-300 hover:border-gray-500 focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
              />
            </div>

            <div class="form-control">
              <label class="label mb-2">
                <span class="label-text font-medium text-gray-300"
                  >期望职位 <span class="text-red-400">*</span></span
                >
              </label>
              <select
                v-model="job"
                class="select select-bordered min-h-14 w-full rounded-lg border-gray-600 bg-gray-800/50 px-4 py-3 text-white transition-all duration-300 hover:border-gray-500 focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
              >
                <option value="frontend">前端开发</option>
                <option value="backend">后端开发</option>
              </select>
            </div>
          </div>
        </div>

        <!-- 简历内容 -->
        <div
          class="rounded-2xl border border-gray-700/50 bg-gray-900/60 p-6 shadow-2xl shadow-blue-500/10 backdrop-blur-md"
        >
          <h2 class="mb-6 flex items-center gap-2 text-xl font-semibold text-white">
            <svg
              class="h-5 w-5 text-blue-400"
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
            简历内容
          </h2>

          <!-- 文件上传 -->
          <div>
            <label class="label mb-2">
              <span class="label-text font-medium text-gray-300">上传简历</span>
            </label>

            <!-- 解析错误提示 -->
            <div
              v-if="parseError"
              class="mb-4 rounded-lg border border-red-500/30 bg-red-500/20 p-3"
            >
              <p class="text-sm text-red-400">{{ parseError }}</p>
            </div>

            <!-- 解析加载状态 -->
            <div
              v-if="parseLoading"
              class="mb-4 rounded-lg border border-blue-500/30 bg-blue-500/20 p-4"
            >
              <div class="flex items-center gap-3">
                <svg
                  class="h-5 w-5 animate-spin text-blue-400"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    class="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="4"
                  ></circle>
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                <p class="text-sm text-blue-400">正在解析文件...</p>
              </div>
            </div>

            <!-- 未上传时的提示 -->
            <div
              v-if="!resumeFileName"
              class="rounded-lg border-2 border-dashed border-gray-600 p-8 text-center transition-colors duration-300 hover:border-blue-400"
            >
              <input
                type="file"
                accept=".doc,.docx,.txt"
                class="hidden"
                id="resume-upload"
                @change="handleFileUpload"
                :disabled="parseLoading"
              />
              <label
                for="resume-upload"
                class="flex cursor-pointer flex-col items-center justify-center gap-3"
                :class="{ 'cursor-not-allowed opacity-50': parseLoading }"
              >
                <svg
                  class="h-12 w-12 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                  />
                </svg>
                <div>
                  <p class="text-gray-400">上传简历文件，或直接在下方粘贴简历正文</p>
                  <p class="mt-1 text-xs text-gray-500">支持 Word（.docx）、TXT 格式</p>
                </div>
              </label>
            </div>

            <!-- 已上传时的文件信息 -->
            <div
              v-else
              class="flex items-center justify-between rounded-lg border border-gray-600 bg-gray-800/50 p-4"
            >
              <div class="flex items-center gap-3">
                <svg
                  class="h-6 w-6 text-blue-400"
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
                <div>
                  <p class="font-medium text-gray-300">{{ resumeFileName }}</p>
                  <p class="text-xs text-gray-500">
                    {{ resumeFile?.size ? (resumeFile.size / 1024).toFixed(1) + " KB" : "" }}
                    <span v-if="resumeText" class="ml-2 text-green-400">
                      ✓ 已解析 ({{ resumeText.length }} 字符)
                    </span>
                  </p>
                </div>
              </div>
              <button
                @click="handleRemoveFile"
                :disabled="parseLoading"
                class="text-red-400 transition-colors duration-200 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            </div>

            <div class="mt-5">
              <div class="mb-2 flex items-center justify-between gap-3">
                <h3 class="text-sm font-medium text-gray-300">简历正文</h3>
                <span class="text-xs text-gray-500"> {{ resumeText.trim().length }} 字符 </span>
              </div>
              <textarea
                v-model="resumeText"
                placeholder="支持直接粘贴简历内容。点击“分析简历”时会自动保存当前草稿。"
                class="textarea textarea-bordered min-h-72 w-full resize-y rounded-xl border-gray-600 bg-gray-800/50 px-4 py-4 leading-7 text-white placeholder-gray-400 transition-all duration-300 hover:border-gray-500 focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400"
              ></textarea>
            </div>

            <div
              class="mt-6 rounded-2xl border border-cyan-400/18 bg-linear-to-r from-cyan-500/10 via-slate-900/20 to-rose-500/10 p-5"
            >
              <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <p class="text-sm font-semibold text-white">简历分析工作台</p>
                  <p class="mt-2 text-sm leading-7 text-slate-300">
                    点击“分析简历”后，系统会先保存你当前填写的姓名、岗位和简历，再生成独立的彩色高亮版简历。
                  </p>
                  <p v-if="hasResumeAnalysis" class="mt-2 text-xs text-cyan-200/80">
                    上次分析时间：{{ resumeAnalysisUpdatedAt }}
                  </p>
                </div>

                <div class="flex flex-col gap-3 sm:flex-row">
                  <button
                    @click="handleAnalyzeResume"
                    :disabled="loading || profileLoading || parseLoading || analysisLoading"
                    class="btn rounded-full border-none bg-linear-to-r from-amber-300 via-yellow-200 to-rose-300 px-6 py-3 text-slate-950 shadow-lg shadow-amber-500/20 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-rose-500/25 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {{ analysisLoading ? "分析中..." : loading ? "保存中..." : "分析简历" }}
                  </button>
                  <button
                    @click="goToResumeAnalysis"
                    :disabled="!hasResumeAnalysis"
                    class="btn rounded-full border border-white/12 bg-white/6 px-6 py-3 text-white transition-all duration-300 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    查看上次分析
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- AI 面试官倾向设置 -->
        <div
          class="rounded-2xl border border-gray-700/50 bg-gray-900/60 p-6 shadow-2xl shadow-blue-500/10 backdrop-blur-md"
        >
          <h2 class="mb-6 flex items-center gap-2 text-xl font-semibold text-white">
            <svg
              class="h-5 w-5 text-blue-400"
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
            AI 面试官倾向设置
          </h2>

          <div class="space-y-6">
            <div class="form-control">
              <label class="label mb-2">
                <span class="label-text font-medium text-gray-300">面试官风格</span>
              </label>
              <div class="grid grid-cols-2 gap-3 md:grid-cols-3">
                <button
                  v-for="style in interviewerStyles"
                  :key="style.value"
                  @click="personalization.interviewerStyle = style.value"
                  :class="[
                    'rounded-lg border px-4 py-3 text-sm transition-all duration-300',
                    personalization.interviewerStyle === style.value
                      ? 'border-blue-500 bg-blue-500/20 text-blue-400'
                      : 'border-gray-600 bg-gray-800/50 text-gray-300 hover:border-gray-500',
                  ]"
                >
                  {{ style.label }}
                </button>
              </div>

              <div v-if="personalization.interviewerStyle === 'custom'" class="mt-4">
                <label class="label mb-2">
                  <span class="label-text font-medium text-gray-300">自定义风格描述</span>
                </label>
                <textarea
                  v-model="customStyle"
                  placeholder="请描述您希望的面试官风格，例如：更注重实战能力、喜欢追问技术细节等..."
                  class="textarea textarea-bordered h-32 w-full resize-none rounded-lg border-gray-600 bg-gray-800/50 px-4 py-3 text-white placeholder-gray-400 transition-all duration-300 hover:border-gray-500 focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
                ></textarea>
              </div>
            </div>
          </div>
        </div>

        <!-- 保存按钮和消息 -->
        <div class="space-y-4">
          <!-- 保存按钮 -->
          <div class="flex items-center justify-between">
            <button
              @click="handleLogout"
              class="btn transform rounded-lg border-none bg-linear-to-r from-red-500 to-red-600 px-8 py-3 text-white shadow-lg shadow-red-500/20 transition-all duration-300 hover:-translate-y-0.5 hover:from-red-600 hover:to-red-700 hover:shadow-xl hover:shadow-red-500/30"
            >
              退出登录
            </button>
            <button
              @click="handleSave"
              :disabled="loading || profileLoading || analysisLoading"
              class="btn flex transform items-center gap-2 rounded-lg border-none bg-linear-to-r from-blue-500 to-blue-600 px-8 py-3 text-white shadow-lg shadow-blue-500/20 transition-all duration-300 hover:-translate-y-0.5 hover:from-blue-600 hover:to-blue-700 hover:shadow-xl hover:shadow-blue-500/30 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <svg
                v-if="loading"
                class="h-5 w-5 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                ></circle>
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              {{
                loading
                  ? "保存中..."
                  : analysisLoading
                    ? "分析中..."
                    : profileLoading
                      ? "同步中..."
                      : "保存设置"
              }}
            </button>
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
        'fixed top-20 left-1/2 z-50 mx-4 w-full max-w-md -translate-x-1/2 transform rounded-lg p-4 shadow-lg transition-all duration-300',
        saveSuccess
          ? 'border border-green-500/50 bg-green-500/20 text-green-400'
          : 'border border-red-500/50 bg-red-500/20 text-red-400',
      ]"
    >
      {{ saveMessage }}
    </div>
  </div>
</template>
