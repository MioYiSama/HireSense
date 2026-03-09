<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

const handleLogout = () => {
  // 登出逻辑待添加...

  console.log("用户登出");

  // 登出后跳转到宣传页
  router.push("/");
};

const goToHome = () => {
  router.push("/");
};
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
        <button
          @click="handleLogout"
          class="btn bg-gray-800/50 hover:bg-gray-700/50 text-gray-300 border border-gray-600 transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/10"
        >
          退出登录
        </button>
      </div>
    </div>

    <!-- 主内容 -->
    <div class="container mx-auto p-8 relative z-10">
      <h1 class="text-3xl font-bold mb-8 text-white">欢迎来到 HireSense</h1>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          class="bg-gray-900/60 backdrop-blur-md border border-gray-700/50 rounded-2xl shadow-2xl shadow-blue-500/10 p-6 transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/20 hover:-translate-y-1"
        >
          <div class="flex flex-col h-full">
            <h2 class="text-xl font-bold text-white mb-2">开始面试</h2>
            <p class="text-gray-300 mb-4">选择岗位，开始AI模拟面试</p>
            <div class="mt-auto">
              <button
                class="btn bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white border-none shadow-lg shadow-blue-500/20 transition-all duration-300 w-full py-2 rounded-lg hover:shadow-xl hover:shadow-blue-500/30 transform hover:-translate-y-0.5"
              >
                开始
              </button>
            </div>
          </div>
        </div>

        <div
          class="bg-gray-900/60 backdrop-blur-md border border-gray-700/50 rounded-2xl shadow-2xl shadow-blue-500/10 p-6 transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/20 hover:-translate-y-1"
        >
          <div class="flex flex-col h-full">
            <h2 class="text-xl font-bold text-white mb-2">面试历史</h2>
            <p class="text-gray-300 mb-4">查看你的面试记录和报告</p>
            <div class="mt-auto">
              <button
                class="btn bg-gray-800/50 hover:bg-gray-700/50 text-gray-300 border border-gray-600 transition-all duration-300 w-full py-2 rounded-lg hover:shadow-lg hover:shadow-blue-500/10"
              >
                查看
              </button>
            </div>
          </div>
        </div>

        <div
          class="bg-gray-900/60 backdrop-blur-md border border-gray-700/50 rounded-2xl shadow-2xl shadow-blue-500/10 p-6 transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/20 hover:-translate-y-1"
        >
          <div class="flex flex-col h-full">
            <h2 class="text-xl font-bold text-white mb-2">个人档案</h2>
            <p class="text-gray-300 mb-4">管理你的个人信息和设置</p>
            <div class="mt-auto">
              <button
                class="btn bg-gray-800/50 hover:bg-gray-700/50 text-gray-300 border border-gray-600 transition-all duration-300 w-full py-2 rounded-lg hover:shadow-lg hover:shadow-blue-500/10"
              >
                编辑
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
