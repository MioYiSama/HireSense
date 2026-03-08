<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const account = ref("");
const password = ref("");

const handleLogin = () => {
  // 登录逻辑待添加...

  console.log("登录信息:", {
    account: account.value,
    password: password.value,
  });

  // 登录成功
  router.push("/dashboard");
};

const goToSignup = () => {
  router.push("/signup");
};
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-base-200">
    <div class="card w-96 bg-base-100 shadow-xl">
      <div class="card-body">
        <h2 class="card-title justify-center text-2xl mb-4">用户登录</h2>

        <div class="form-control">
          <label class="label">
            <span class="label-text">账号</span>
          </label>
          <input
            v-model="account"
            type="text"
            placeholder="请输入账号"
            class="input input-bordered"
          />
        </div>

        <div class="form-control">
          <label class="label">
            <span class="label-text">密码</span>
          </label>
          <input
            v-model="password"
            type="password"
            placeholder="请输入密码"
            class="input input-bordered"
          />
        </div>

        <div class="form-control mt-6">
          <button @click="handleLogin" class="btn btn-primary">登录</button>
        </div>

        <div class="text-center mt-4">
          <span class="text-sm">还没有账号？</span>
          <button @click="goToSignup" class="btn btn-link btn-sm">
            立即注册
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
