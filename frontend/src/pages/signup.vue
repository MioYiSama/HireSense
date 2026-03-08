<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const account = ref("");
const password = ref("");
const confirmPassword = ref("");

const handleSignup = () => {
  // 验证密码是否一致
  if (password.value !== confirmPassword.value) {
    alert("两次输入的密码不一致");
    return;
  }

  // 注册逻辑待添加...

  console.log("注册信息:", {
    account: account.value,
    password: password.value,
  });

  // 注册成功
  router.push("/signin");
};

const goToSignin = () => {
  router.push("/signin");
};
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-base-200">
    <div class="card w-96 bg-base-100 shadow-xl">
      <div class="card-body">
        <h2 class="card-title justify-center text-2xl mb-4">用户注册</h2>

        <div class="form-control">
          <label class="label">
            <span class="label-text">邮箱</span>
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

        <div class="form-control">
          <label class="label">
            <span class="label-text">确认密码</span>
          </label>
          <input
            v-model="confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            class="input input-bordered"
          />
        </div>

        <div class="form-control mt-6">
          <button @click="handleSignup" class="btn btn-primary">注册</button>
        </div>

        <div class="text-center mt-4">
          <span class="text-sm">已有账号？</span>
          <button @click="goToSignin" class="btn btn-link btn-sm">
            立即登录
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
