<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

const handleLogout = () => {
  // 登出逻辑待添加...

  console.log("用户登出");

  // 登出后跳转到宣传页
  router.push("/");
};
</script>

<template>
  <div class="min-h-screen bg-base-200">
    <div class="navbar bg-base-100 shadow-lg">
      <div class="flex-1">
        <a class="btn btn-ghost text-xl">HireSense - 知聘</a>
      </div>
      <div class="flex-none">
        <button @click="handleLogout" class="btn btn-ghost">退出登录</button>
      </div>
    </div>

    <div class="container mx-auto p-8">
      <h1 class="text-3xl font-bold mb-6">欢迎来到HireSense</h1>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div class="card bg-base-100 shadow-xl">
          <div class="card-body">
            <h2 class="card-title">开始面试</h2>
            <p>选择岗位，开始AI模拟面试</p>
            <div class="card-actions justify-end">
              <button class="btn btn-primary">开始</button>
            </div>
          </div>
        </div>

        <div class="card bg-base-100 shadow-xl">
          <div class="card-body">
            <h2 class="card-title">面试历史</h2>
            <p>查看你的面试记录和报告</p>
            <div class="card-actions justify-end">
              <button class="btn btn-secondary">查看</button>
            </div>
          </div>
        </div>

        <div class="card bg-base-100 shadow-xl">
          <div class="card-body">
            <h2 class="card-title">个人档案</h2>
            <p>管理你的个人信息和设置</p>
            <div class="card-actions justify-end">
              <button class="btn btn-accent">编辑</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
