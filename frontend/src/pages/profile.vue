<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { getUserInfo, setUserInfo, clearAll } from "@/utils/token";
import { userApi, authApi } from "@/lib/api";
import type { Profile, ProfileJobEnum } from "@/api";
import ConfirmDialog from "@/components/ConfirmDialog.vue";

const router = useRouter();
const showDropdown = ref(false);
let hideTimeout: number | null = null;

const name = ref("奶龙");
const job = ref<ProfileJobEnum>("frontend");
const resumeFile = ref<File | null>(null);
const resumeFileName = ref("");
const personalization = ref({
  interviewerStyle: "default",
});

// 从localStorage获取用户信息
const userInfo = getUserInfo();
if (userInfo && userInfo.name) {
  name.value = userInfo.name;
}

const interviewerStyles = [
  { value: "default", label: "默认" },
  { value: "professional", label: "专业严肃" },
  { value: "friendly", label: "亲和温和" },
  { value: "challenging", label: "挑战性" },
  { value: "custom", label: "自定义" },
];

const customStyle = ref("");

const loading = ref(false);
const saveMessage = ref("");
const saveSuccess = ref(false);

const showLogoutDialog = ref(false);

const handleLogout = async () => {
  // 显示确认对话框
  showLogoutDialog.value = true;
};

const handleSignout = () => {
  // 退出登录
  clearAll();
  console.log("用户退出登录");
  router.push("/signin");
};

const confirmLogout = async () => {
  showLogoutDialog.value = false;

  try {
    // 调用注销 API
    const response = await authApi.apiAuthSignoutPost();
    const data = response.data;

    if (data.success) {
      console.log("注销成功:", data.message);
      // 清除所有用户信息
      clearAll();
      // 跳转到登录页面
      router.push("/signin");
    } else {
      console.error("注销失败:", data.message);
      // 显示错误提示
      saveMessage.value = data.message || "注销失败";
      saveSuccess.value = false;
    }
  } catch (err: any) {
    console.error("注销错误:", err);
    // 显示错误提示
    saveMessage.value = err.response?.data?.message || "网络错误，请稍后重试";
    saveSuccess.value = false;
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

const showMenu = () => {
  // 清除之前的定时器
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

const handleFileUpload = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    const file = target.files[0];
    if (file) {
      resumeFile.value = file;
      resumeFileName.value = file.name;
      console.log("上传的文件:", file);
    }
  }
};

const handleRemoveFile = () => {
  resumeFile.value = null;
  resumeFileName.value = "";
  console.log("移除文件");
};

const handleSave = async () => {
  // 表单验证
  if (!name.value || !job.value) {
    saveMessage.value = "请填写姓名和期望职位";
    saveSuccess.value = false;
    return;
  }

  loading.value = true;
  saveMessage.value = "";

  try {
    // 构建请求体
    const profile: Profile = {
      name: name.value,
      job: job.value,
      // resume 字段暂时不传，因为 API 需要结构化简历文本，而我们只有文件上传
      //personalization: personalization.value,
    };

    // 发送 PUT 请求
    const response = await userApi.apiUserProfilePut(profile);
    const data = response.data;

    if (data.success) {
      saveMessage.value = data.message || "档案更新成功";
      saveSuccess.value = true;
      console.log("档案更新成功:", data);
      // 更新localStorage中的用户信息
      setUserInfo({ ...getUserInfo(), name: name.value, job: job.value });
    } else {
      saveMessage.value = data.message || "档案更新失败";
      saveSuccess.value = false;
    }
  } catch (err: any) {
    console.error("更新档案错误:", err);
    saveMessage.value = err.response?.data?.message || "网络错误，请稍后重试";
    saveSuccess.value = false;
  } finally {
    loading.value = false;
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
});
</script>

<template>
  <div
    class="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 relative overflow-hidden"
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
              class="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-medium"
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
              class="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-800/50 transition-colors duration-200 flex items-center gap-2"
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
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                />
              </svg>
              个人中心
            </button>
            <button
              @click="handleSignout"
              class="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-800/50 transition-colors duration-200 flex items-center gap-2"
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
    <div class="container mx-auto p-8 relative z-10">
      <h1 class="text-3xl font-bold mb-8 text-white">个人中心</h1>

      <div class="max-w-4xl mx-auto space-y-6">
        <!-- 基本信息 -->
        <div
          class="bg-gray-900/60 backdrop-blur-md border border-gray-700/50 rounded-2xl shadow-2xl shadow-blue-500/10 p-6"
        >
          <h2
            class="text-xl font-semibold mb-6 text-white flex items-center gap-2"
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
                d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
              />
            </svg>
            基本信息
          </h2>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="form-control">
              <label class="label mb-2">
                <span class="label-text text-gray-300 font-medium"
                  >姓名 <span class="text-red-400">*</span></span
                >
              </label>
              <input
                v-model="name"
                type="text"
                placeholder="请输入姓名"
                class="input input-bordered bg-gray-800/50 border-gray-600 text-white placeholder-gray-400 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 w-full px-4 py-3 rounded-lg transition-all duration-300 hover:border-gray-500 min-h-[3.5rem]"
              />
            </div>

            <div class="form-control">
              <label class="label mb-2">
                <span class="label-text text-gray-300 font-medium"
                  >期望职位 <span class="text-red-400">*</span></span
                >
              </label>
              <select
                v-model="job"
                class="select select-bordered bg-gray-800/50 border-gray-600 text-white focus:border-blue-400 focus:ring-1 focus:ring-blue-400 w-full px-4 py-3 rounded-lg transition-all duration-300 hover:border-gray-500 min-h-[3.5rem]"
              >
                <option value="frontend">前端开发</option>
                <option value="backend">后端开发</option>
              </select>
            </div>
          </div>
        </div>

        <!-- 简历内容 -->
        <div
          class="bg-gray-900/60 backdrop-blur-md border border-gray-700/50 rounded-2xl shadow-2xl shadow-blue-500/10 p-6"
        >
          <h2
            class="text-xl font-semibold mb-6 text-white flex items-center gap-2"
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
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            简历内容
          </h2>

          <!-- 文件上传 -->
          <div>
            <label class="label mb-2">
              <span class="label-text text-gray-300 font-medium">上传简历</span>
            </label>

            <!-- 未上传时的提示 -->
            <div
              v-if="!resumeFileName"
              class="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center hover:border-blue-400 transition-colors duration-300"
            >
              <input
                type="file"
                accept=".pdf,.doc,.docx,.txt"
                class="hidden"
                id="resume-upload"
                @change="handleFileUpload"
              />
              <label
                for="resume-upload"
                class="cursor-pointer flex flex-col items-center justify-center gap-3"
              >
                <svg
                  class="w-12 h-12 text-gray-400"
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
                  <p class="text-gray-400">简历为空，请上传您的简历</p>
                  <p class="text-xs text-gray-500 mt-1">
                    支持 PDF、Word、TXT 格式
                  </p>
                </div>
              </label>
            </div>

            <!-- 已上传时的文件信息 -->
            <div
              v-else
              class="flex items-center justify-between p-4 bg-gray-800/50 border border-gray-600 rounded-lg"
            >
              <div class="flex items-center gap-3">
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
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <div>
                  <p class="text-gray-300 font-medium">{{ resumeFileName }}</p>
                  <p class="text-xs text-gray-500">
                    {{
                      resumeFile?.size
                        ? (resumeFile.size / 1024).toFixed(1) + " KB"
                        : ""
                    }}
                  </p>
                </div>
              </div>
              <button
                @click="handleRemoveFile"
                class="text-red-400 hover:text-red-300 transition-colors duration-200"
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
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- AI 面试官倾向设置 -->
        <div
          class="bg-gray-900/60 backdrop-blur-md border border-gray-700/50 rounded-2xl shadow-2xl shadow-blue-500/10 p-6"
        >
          <h2
            class="text-xl font-semibold mb-6 text-white flex items-center gap-2"
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
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
            AI 面试官倾向设置
          </h2>

          <div class="space-y-6">
            <div class="form-control">
              <label class="label mb-2">
                <span class="label-text text-gray-300 font-medium"
                  >面试官风格</span
                >
              </label>
              <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
                <button
                  v-for="style in interviewerStyles"
                  :key="style.value"
                  @click="personalization.interviewerStyle = style.value"
                  :class="[
                    'px-4 py-3 rounded-lg border transition-all duration-300 text-sm',
                    personalization.interviewerStyle === style.value
                      ? 'bg-blue-500/20 border-blue-500 text-blue-400'
                      : 'bg-gray-800/50 border-gray-600 text-gray-300 hover:border-gray-500',
                  ]"
                >
                  {{ style.label }}
                </button>
              </div>

              <div
                v-if="personalization.interviewerStyle === 'custom'"
                class="mt-4"
              >
                <label class="label mb-2">
                  <span class="label-text text-gray-300 font-medium"
                    >自定义风格描述</span
                  >
                </label>
                <textarea
                  v-model="customStyle"
                  placeholder="请描述您希望的面试官风格，例如：更注重实战能力、喜欢追问技术细节等..."
                  class="textarea textarea-bordered bg-gray-800/50 border-gray-600 text-white placeholder-gray-400 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 w-full px-4 py-3 rounded-lg transition-all duration-300 hover:border-gray-500 h-32 resize-none"
                ></textarea>
              </div>
            </div>
          </div>
        </div>

        <!-- 保存按钮和消息 -->
        <div class="space-y-4">
          <!-- 保存消息提示 -->
          <div
            v-if="saveMessage"
            :class="[
              'p-4 rounded-lg text-center',
              saveSuccess
                ? 'bg-green-500/20 border border-green-500/50 text-green-400'
                : 'bg-red-500/20 border border-red-500/50 text-red-400',
            ]"
          >
            {{ saveMessage }}
          </div>

          <!-- 保存按钮 -->
          <div class="flex justify-between items-center">
            <button
              @click="handleLogout"
              class="btn bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white border-none shadow-lg shadow-red-500/20 transition-all duration-300 px-8 py-3 rounded-lg hover:shadow-xl hover:shadow-red-500/30 transform hover:-translate-y-0.5"
            >
              注销用户
            </button>
            <button
              @click="handleSave"
              :disabled="loading"
              class="btn bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white border-none shadow-lg shadow-blue-500/20 transition-all duration-300 px-8 py-3 rounded-lg hover:shadow-xl hover:shadow-blue-500/30 transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <svg
                v-if="loading"
                class="animate-spin h-5 w-5"
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
              {{ loading ? "保存中..." : "保存设置" }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 注销确认对话框 -->
    <ConfirmDialog
      :show="showLogoutDialog"
      title="确认注销"
      message="确定要注销用户吗？此操作将删除您的所有个人信息和档案，且无法恢复。"
      confirm-text="确认注销"
      cancel-text="取消"
      @confirm="confirmLogout"
      @cancel="cancelLogout"
    />
  </div>
</template>
