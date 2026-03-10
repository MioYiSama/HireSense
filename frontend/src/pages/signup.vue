<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { authApi } from "@/lib/api";
import { setAccessToken } from "@/utils/token";
import type { SignUpRequest } from "@/api";

const router = useRouter();
const account = ref("");
const name = ref("");
const password = ref("");
const confirmPassword = ref("");
const loading = ref(false);
const error = ref("");

const handleSignup = async () => {
  // 表单验证
  if (!account.value || !name.value || !password.value) {
    error.value = "请填写所有必填字段";
    return;
  }

  if (password.value !== confirmPassword.value) {
    error.value = "两次输入的密码不一致";
    return;
  }

  loading.value = true;
  error.value = "";

  try {
    const signUpRequest: SignUpRequest = {
      account: account.value,
      name: name.value,
      password: password.value,
    };

    const response = await authApi.apiAuthSignupPost(signUpRequest);
    const data = response.data;

    if (data.success) {
      // 注册成功，保存 Token
      setAccessToken(data.data);
      console.log("注册成功:", data.message);
      // 跳转到仪表盘
      router.push("/dashboard");
    } else {
      // 注册失败
      error.value = data.message || "注册失败，请稍后重试";
    }
  } catch (err: any) {
    console.error("注册错误:", err);
    error.value = err.response?.data?.message || "网络错误，请稍后重试";
  } finally {
    loading.value = false;
  }
};

const goToSignin = () => {
  router.push("/signin");
};

const goToHome = () => {
  router.push("/");
};
</script>

<template>
  <div
    class="min-h-screen flex items-center justify-center bg-linear-to-br from-gray-900 via-gray-800 to-gray-900 relative overflow-hidden"
  >
    <!-- 背景 -->
    <div
      class="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl"
    ></div>
    <div
      class="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl"
    ></div>

    <!-- 主容器 -->
    <div class="relative z-10 w-full max-w-md">
      <!-- Logo -->
      <div class="flex justify-center mb-8">
        <button
          @click="goToHome"
          class="flex items-center gap-2 transition-all duration-300 hover:scale-105 hover:opacity-90 cursor-pointer group relative"
          title="返回主页"
        >
          <img src="/logo-long.png" alt="HireSense" class="h-8 rounded-md" />
          <span
            class="absolute -bottom-6 left-1/2 -translate-x-1/2 text-xs text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap"
            >返回主页</span
          >
        </button>
      </div>

      <!-- 注册卡片 -->
      <div
        class="bg-gray-900/60 backdrop-blur-md border border-gray-700/50 rounded-2xl shadow-2xl shadow-blue-500/10 p-8 max-w-md mx-auto"
      >
        <h2 class="text-2xl font-bold text-center text-white mb-8">用户注册</h2>

        <!-- 错误提示 -->
        <div
          v-if="error"
          class="mb-6 p-3 bg-red-500/20 border border-red-500/30 rounded-lg"
        >
          <p class="text-red-400 text-sm text-center">{{ error }}</p>
        </div>

        <div class="space-y-6">
          <div class="form-control">
            <label class="label mb-2">
              <span class="label-text text-gray-300 font-medium">账号</span>
            </label>
            <input
              v-model="account"
              type="text"
              placeholder="请输入账号"
              class="input input-bordered bg-gray-800/50 border-gray-600 text-white placeholder-gray-400 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 w-full px-4 py-3 rounded-lg transition-all duration-300 hover:border-gray-500"
              :disabled="loading"
              @keyup.enter="handleSignup"
            />
          </div>

          <div class="form-control">
            <label class="label mb-2">
              <span class="label-text text-gray-300 font-medium">用户名</span>
            </label>
            <input
              v-model="name"
              type="text"
              placeholder="请输入用户名"
              class="input input-bordered bg-gray-800/50 border-gray-600 text-white placeholder-gray-400 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 w-full px-4 py-3 rounded-lg transition-all duration-300 hover:border-gray-500"
              :disabled="loading"
              @keyup.enter="handleSignup"
            />
          </div>

          <div class="form-control">
            <label class="label mb-2">
              <span class="label-text text-gray-300 font-medium">密码</span>
            </label>
            <input
              v-model="password"
              type="password"
              placeholder="请输入密码"
              class="input input-bordered bg-gray-800/50 border-gray-600 text-white placeholder-gray-400 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 w-full px-4 py-3 rounded-lg transition-all duration-300 hover:border-gray-500"
              :disabled="loading"
              @keyup.enter="handleSignup"
            />
          </div>

          <div class="form-control">
            <label class="label mb-2">
              <span class="label-text text-gray-300 font-medium">确认密码</span>
            </label>
            <input
              v-model="confirmPassword"
              type="password"
              placeholder="请再次输入密码"
              class="input input-bordered bg-gray-800/50 border-gray-600 text-white placeholder-gray-400 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 w-full px-4 py-3 rounded-lg transition-all duration-300 hover:border-gray-500"
              :disabled="loading"
              @keyup.enter="handleSignup"
            />
          </div>

          <div class="form-control mt-8">
            <button
              @click="handleSignup"
              :disabled="loading"
              class="btn bg-linear-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white border-none shadow-lg shadow-blue-500/20 transition-all duration-300 w-full py-3 rounded-lg hover:shadow-xl hover:shadow-blue-500/30 transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span
                v-if="loading"
                class="loading loading-spinner loading-sm mr-2"
              ></span>
              {{ loading ? "注册中..." : "注册" }}
            </button>
          </div>

          <div class="text-center mt-6">
            <span class="text-sm text-gray-400">已有账号？</span>
            <button
              @click="goToSignin"
              class="btn btn-link btn-sm text-blue-400 hover:text-blue-300 ml-1 transition-colors duration-300"
            >
              立即登录
            </button>
          </div>
        </div>
      </div>

      <!-- 底部信息 -->
      <div class="text-center mt-6 text-gray-500 text-sm">
        <p>© 2026 HireSense. 智能面试平台</p>
      </div>
    </div>
  </div>
</template>
