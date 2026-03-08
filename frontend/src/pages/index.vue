<script setup lang="ts">
import { useRouter } from "vue-router";
import LucideCircleUser from "~icons/lucide/circle-user";
import LucideLogIn from "~icons/lucide/log-in";
import LucideUserPlus from "~icons/lucide/user-plus";

const router = useRouter();

const goToSignin = () => {
  router.push("/signin");
};

const goToSignup = () => {
  router.push("/signup");
};
</script>

<template>
  <div
    class="min-h-screen bg-gradient-to-br from-primary to-secondary flex items-center justify-center"
  >
    <div class="text-center text-white">
      <h1 class="text-6xl font-bold mb-4">HireSense</h1>
      <p class="text-2xl mb-2">知聘</p>
      <p class="text-xl mb-8 opacity-90">AI驱动的模拟面试与能力提升平台</p>

      <div class="flex gap-4 justify-center">
        <button @click="goToSignin" class="btn btn-lg btn-accent">
          <LucideLogIn />
          <span>登录</span>
        </button>
        <button @click="goToSignup" class="btn btn-lg btn-neutral">
          <LucideUserPlus />
          <span>注册</span>
        </button>
      </div>

      <div class="mt-12">
        <div class="flex justify-center items-center gap-8">
          <div class="text-center">
            <LucideCircleUser class="w-16 h-16 mx-auto mb-2 opacity-80" />
            <p class="text-sm opacity-75">AI面试官</p>
          </div>
          <div class="text-center">
            <LucideCircleUser class="w-16 h-16 mx-auto mb-2 opacity-80" />
            <p class="text-sm opacity-75">智能评估</p>
          </div>
          <div class="text-center">
            <LucideCircleUser class="w-16 h-16 mx-auto mb-2 opacity-80" />
            <p class="text-sm opacity-75">个性化提升</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
