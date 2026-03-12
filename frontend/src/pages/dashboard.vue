<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { removeAccessToken } from "@/utils/token";

const router = useRouter();
const showDropdown = ref(false);
let hideTimeout: number | null = null;

const name = ref("奶龙");

const handleLogout = () => {
  // 清除 token
  removeAccessToken();
  console.log("用户登出");
  // 登出后跳转到登录页面
  router.push("/signin");
};

const goToHome = () => {
  router.push("/");
};

const goToProfile = () => {
  // 跳转到个人中心页面
  router.push("/profile");
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
              @click="handleLogout"
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
  </div>
</template>
