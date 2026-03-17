<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import {
  getAccessToken,
  getInterviewId,
  removeInterviewId,
} from "@/utils/token";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import InterviewInput from "@/components/InterviewInput.vue";

const router = useRouter();
const showConfirmDialog = ref(false);
const interviewTime = ref(0);
const timerInterval = ref<number | null>(null);
const isLoading = ref(false);
const errorMessage = ref("");
const interviewId = ref(getInterviewId());

// 录音状态
const isRecording = ref(false);
const recordingTime = ref(0);
const recordingInterval = ref<number | null>(null);
const mediaRecorder = ref<MediaRecorder | null>(null);
const audioChunks = ref<Blob[]>([]);
const isCancelingRecording = ref(false);
const answerCountdown = ref(60);
const countdownInterval = ref<number | null>(null);

// 定义消息类型
interface Message {
  id: number;
  role: "ai" | "user";
  content: string;
  timestamp: string;
}

// 对话相关状态
const messages = ref<Message[]>([]);
const userInput = ref("");
const isSubmitting = ref(false);

// 处理输入消息
const handleInputMessage = (message: string) => {
  userInput.value = message;
  sendMessage();
};
const isInitialLoading = ref(true);

// API请求函数
const sendInterviewReply = async (payload: { text: string } | FormData) => {
  const token = getAccessToken();
  const id = getInterviewId();
  const url = `http://127.0.0.1:8080/api/interview/reply?id=${id}`;

  const options = {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,

      ...(payload instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
    },
    body: payload instanceof FormData ? payload : JSON.stringify(payload),
  };

  const response = await fetch(url, options);
  const data = await response.json();

  if (data.success) {
    // 添加AI回复
    const aiMessage = {
      id: Date.now() + 1,
      role: "ai" as const,
      content: data.data.reply,
      timestamp: new Date().toLocaleTimeString(),
    };
    messages.value.push(aiMessage);

    // 检查是否面试结束
    if (data.data.ending) {
      console.log("面试已结束");
    }
  } else {
    throw new Error(data.message || "API请求失败");
  }
};

const sendMessage = async () => {
  if (!userInput.value.trim() || isSubmitting.value) return;

  // 添加用户消息
  const userMessage = {
    id: Date.now(),
    role: "user" as const,
    content: userInput.value.trim(),
    timestamp: new Date().toLocaleTimeString(),
  };
  messages.value.push(userMessage);

  // 清空输入框
  const inputContent = userInput.value.trim();
  userInput.value = "";

  console.log("用户输入:", inputContent);

  // 发送请求获取AI回复
  isSubmitting.value = true;
  try {
    await sendInterviewReply({ text: inputContent });
  } catch (error) {
    console.error("发送消息失败:", error);
    // 添加错误提示消息
    const errorMessage = {
      id: Date.now() + 1,
      role: "ai" as const,
      content: "抱歉，我暂时无法回复，请稍后再试。",
      timestamp: new Date().toLocaleTimeString(),
    };
    messages.value.push(errorMessage);
  } finally {
    isSubmitting.value = false;
  }
};

const formatTime = (seconds: number) => {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  return `${hrs.toString().padStart(2, "0")}:${mins
    .toString()
    .padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
};

onMounted(() => {
  // 开始计时
  timerInterval.value = window.setInterval(() => {
    interviewTime.value++;
  }, 1000);

  setTimeout(() => {
    isInitialLoading.value = false;
    messages.value.push({
      id: 1,
      role: "ai",
      content:
        "你好！我是你的AI面试官。欢迎参加今天的面试。请先做一个简短的自我介绍，然后我们将开始技术问题的讨论。",
      timestamp: new Date().toLocaleTimeString(),
    });
  }, 1500);
});

onUnmounted(() => {
  // 清除计时器
  if (timerInterval.value) {
    clearInterval(timerInterval.value);
  }

  // 清除录音计时器
  if (recordingInterval.value) {
    clearInterval(recordingInterval.value);
  }

  // 停止录音
  if (mediaRecorder.value && isRecording.value) {
    mediaRecorder.value.stop();
  }
});

const endInterview = () => {
  // 显示确认对话框
  showConfirmDialog.value = true;
};

const confirmEndInterview = async () => {
  // 显示加载状态
  isLoading.value = true;
  errorMessage.value = "";

  try {
    // 从localStorage获取token
    const token = getAccessToken();

    if (!token) {
      errorMessage.value = "请先登录";
      isLoading.value = false;
      return;
    }

    if (!interviewId.value) {
      errorMessage.value = "面试ID不存在";
      isLoading.value = false;
      return;
    }

    // 发送面试结束请求
    const url = "http://127.0.0.1:8080/api/interview/stop";
    const options = {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ id: interviewId.value }),
    };

    const response = await fetch(url, options);

    if (!response.ok) {
      throw new Error("请求失败");
    }

    const data = await response.json();

    if (data.success) {
      // 清除计时器
      if (timerInterval.value) {
        clearInterval(timerInterval.value);
      }
      // 删除存储的面试ID
      removeInterviewId();
      // 请求成功，返回dashboard页面
      showConfirmDialog.value = false;
      router.push("/dashboard");
    } else {
      errorMessage.value = data.message || "结束面试失败";
      isLoading.value = false;
    }
  } catch (error) {
    console.error("结束面试失败:", error);
    errorMessage.value = "网络错误，请稍后重试";
    isLoading.value = false;
  }
};

const cancelEndInterview = () => {
  // 取消结束面试
  showConfirmDialog.value = false;
};

// WAV音频编码器
class WavEncoder {
  private sampleRate: number;

  constructor(sampleRate: number = 44100) {
    this.sampleRate = sampleRate;
  }

  async encode(audioBuffer: AudioBuffer): Promise<Blob> {
    const numberOfChannels = audioBuffer.numberOfChannels;
    const length = audioBuffer.length * numberOfChannels * 2 + 44;
    const buffer = new ArrayBuffer(length);
    const view = new DataView(buffer);

    // WAV文件头
    const writeString = (offset: number, string: string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };

    writeString(0, "RIFF");
    view.setUint32(4, 36 + audioBuffer.length * numberOfChannels * 2, true);
    writeString(8, "WAVE");
    writeString(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numberOfChannels, true);
    view.setUint32(24, this.sampleRate, true);
    view.setUint32(28, this.sampleRate * numberOfChannels * 2, true);
    view.setUint16(32, numberOfChannels * 2, true);
    view.setUint16(34, 16, true);
    writeString(36, "data");
    view.setUint32(40, audioBuffer.length * numberOfChannels * 2, true);

    // 写入音频数据
    const channels: Float32Array[] = [];
    for (let i = 0; i < numberOfChannels; i++) {
      channels.push(audioBuffer.getChannelData(i));
    }

    let offset = 44;
    for (let i = 0; i < audioBuffer.length; i++) {
      for (let channel = 0; channel < numberOfChannels; channel++) {
        const channelData = channels[channel];
        if (channelData && i < channelData.length) {
          const sampleValue = channelData[i];
          if (sampleValue !== undefined) {
            let sample = Math.max(-1, Math.min(1, sampleValue));
            sample = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
            view.setInt16(offset, sample, true);
            offset += 2;
          }
        }
      }
    }

    return new Blob([buffer], { type: "audio/wav" });
  }
}

// 开始录音
const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder.value = new MediaRecorder(stream, { mimeType: "audio/webm" });
    audioChunks.value = [];

    mediaRecorder.value.ondataavailable = (event) => {
      if (event.data.size > 0 && !isCancelingRecording.value) {
        audioChunks.value.push(event.data);
      }
    };

    mediaRecorder.value.onstop = async () => {
      // 检查是否有录音数据
      if (audioChunks.value.length === 0) {
        console.log("录音被中断，没有数据");
        // 重置取消标志
        isCancelingRecording.value = false;
        return;
      }

      const audioBlob = new Blob(audioChunks.value, { type: "audio/webm" });
      console.log("录音完成，音频数据:", audioBlob);
      console.log("音频大小:", audioBlob.size, "bytes");

      // 将WebM转换为WAV格式
      try {
        const audioContext = new AudioContext();
        const arrayBuffer = await audioBlob.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

        const encoder = new WavEncoder(audioBuffer.sampleRate);
        const wavBlob = await encoder.encode(audioBuffer);

        console.log("WAV文件生成成功:", wavBlob);
        console.log("WAV文件大小:", wavBlob.size, "bytes");

        // 发送录音消息到聊天界面
        await sendAudioMessage(wavBlob, recordingTime.value);

        // 可以在这里将WAV文件发送到服务器或进行其他处理
        const wavUrl = URL.createObjectURL(wavBlob);
        console.log("WAV文件URL:", wavUrl);

        // 清理URL对象
        setTimeout(() => URL.revokeObjectURL(wavUrl), 1000);
      } catch (error) {
        console.error("WAV转换失败:", error);
      }

      // 清空录音数据
      audioChunks.value = [];
      recordingTime.value = 0;
      // 重置取消标志
      isCancelingRecording.value = false;
    };

    mediaRecorder.value.start();
    isRecording.value = true;
    recordingTime.value = 0;
    answerCountdown.value = 60;

    // 开始录音计时
    recordingInterval.value = window.setInterval(() => {
      recordingTime.value++;
    }, 1000);

    // 开始作答倒计时
    countdownInterval.value = window.setInterval(() => {
      if (answerCountdown.value > 0) {
        answerCountdown.value--;
      } else {
        // 倒计时结束，自动停止录音
        stopRecording();
      }
    }, 1000);

    console.log("开始录音");
  } catch (error) {
    console.error("录音失败:", error);
    alert("无法访问麦克风，请确保已授予权限");
  }
};

// 停止录音
const stopRecording = () => {
  if (mediaRecorder.value && isRecording.value) {
    mediaRecorder.value.stop();
    isRecording.value = false;

    // 停止计时
    if (recordingInterval.value) {
      clearInterval(recordingInterval.value);
      recordingInterval.value = null;
    }

    // 停止倒计时
    if (countdownInterval.value) {
      clearInterval(countdownInterval.value);
      countdownInterval.value = null;
    }

    console.log("停止录音，录音时长:", recordingTime.value, "秒");
  }
};

// 中断录音
const cancelRecording = () => {
  if (mediaRecorder.value && isRecording.value) {
    // 设置取消标志，这样ondataavailable事件就不会添加数据
    isCancelingRecording.value = true;

    // 清空录音数据
    audioChunks.value = [];

    // 停止录音
    mediaRecorder.value.stop();
    isRecording.value = false;

    // 停止计时
    if (recordingInterval.value) {
      clearInterval(recordingInterval.value);
      recordingInterval.value = null;
    }

    // 停止倒计时
    if (countdownInterval.value) {
      clearInterval(countdownInterval.value);
      countdownInterval.value = null;
    }

    // 重置录音时间
    recordingTime.value = 0;
    answerCountdown.value = 60;

    console.log("中断录音");
  }
};

// 发送录音消息
const sendAudioMessage = async (audioBlob: Blob, duration: number) => {
  // 添加用户消息
  const id = Date.now();
  const newMessage: Message = {
    id,
    role: "user",
    content: `[语音消息] ${formatRecordingTime(duration)}`,
    timestamp: new Date().toLocaleTimeString(),
  };
  messages.value.push(newMessage);

  // 发送请求获取AI回复
  isSubmitting.value = true;
  try {
    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.wav");
    formData.append("text", `[语音消息] ${formatRecordingTime(duration)}`);

    await sendInterviewReply(formData);
  } catch (error) {
    console.error("发送语音消息失败:", error);
    // 添加错误提示消息
    const errorMessage = {
      id: Date.now() + 1,
      role: "ai" as const,
      content: "抱歉，我暂时无法处理语音消息，请稍后再试。",
      timestamp: new Date().toLocaleTimeString(),
    };
    messages.value.push(errorMessage);
  } finally {
    isSubmitting.value = false;
  }
};

// 格式化录音时间
const formatRecordingTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
};
</script>

<template>
  <div
    class="min-h-screen bg-linear-to-br from-gray-900 via-gray-800 to-gray-900 relative overflow-hidden"
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
        <div class="flex items-center gap-3">
          <img
            src="/logo-long.png"
            alt="HireSense"
            class="h-8 rounded-lg shadow-lg"
          />
        </div>
      </div>
      <div class="flex-none flex items-center gap-4">
        <!-- 面试时长计时器 -->
        <div
          class="flex items-center gap-2 px-4 py-1.5 rounded-xl bg-gray-800/50 border border-gray-700/50 shadow-lg"
        >
          <svg
            class="w-4 h-4 text-blue-400"
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
          <span class="text-gray-300 font-mono text-sm">
            {{ formatTime(interviewTime) }}
          </span>
        </div>

        <!-- 结束面试按钮 -->
        <button
          @click="endInterview"
          class="group px-4 py-1.5 rounded-xl bg-linear-to-r from-red-500/20 to-red-600/20 hover:from-red-500 hover:to-red-600 text-red-400 hover:text-white font-semibold transition-all duration-300 border border-red-500/40 hover:border-red-500 shadow-lg shadow-red-500/10 hover:shadow-red-500/30 cursor-pointer flex items-center gap-2 hover:scale-105 active:scale-95"
        >
          <div class="relative">
            <svg
              class="w-4 h-4 transition-transform duration-300 group-hover:rotate-90"
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
          </div>
          <span>结束面试</span>
          <svg
            class="w-3 h-3 opacity-0 -ml-2 group-hover:opacity-100 group-hover:ml-0 transition-all duration-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="flex-1 p-4 md:p-8">
      <div
        class="h-[calc(100vh-8rem)] flex flex-col bg-gray-900/60 backdrop-blur-md border border-gray-700/50 rounded-2xl shadow-xl overflow-hidden"
      >
        <!-- 对话内容展示区 -->
        <div class="flex-1 overflow-y-auto p-6 space-y-6">
          <!-- 初始加载状态 -->
          <div
            v-if="isInitialLoading"
            class="flex justify-center items-center h-full"
          >
            <div class="text-center">
              <div
                class="w-16 h-16 mx-auto mb-4 rounded-full bg-blue-500/20 flex items-center justify-center animate-pulse"
              >
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
                    d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
              </div>
              <p class="text-gray-400">AI面试官正在准备中...</p>
            </div>
          </div>

          <!-- 消息列表 -->
          <template v-else>
            <div
              v-for="message in messages"
              :key="message.id"
              class="flex"
              :class="message.role === 'ai' ? 'justify-start' : 'justify-end'"
            >
              <!-- AI面试官消息 -->
              <div
                v-if="message.role === 'ai'"
                class="flex items-start gap-3 max-w-[80%]"
              >
                <div
                  class="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center shrink-0"
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
                      d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                    />
                  </svg>
                </div>
                <div
                  class="bg-gray-800/50 border border-gray-700/50 rounded-2xl rounded-tl-none p-4 shadow-lg"
                >
                  <div class="flex items-center justify-between mb-2">
                    <span class="text-sm font-medium text-blue-400"
                      >AI面试官</span
                    >
                    <span class="text-xs text-gray-500">{{
                      message.timestamp
                    }}</span>
                  </div>
                  <p class="text-gray-300 leading-relaxed">
                    {{ message.content }}
                  </p>
                </div>
              </div>

              <!-- 用户消息 -->
              <div v-else class="flex items-start gap-3 max-w-[80%]">
                <div
                  class="bg-linear-to-r from-blue-500/20 to-purple-500/20 border border-blue-500/30 rounded-2xl rounded-tr-none p-4 shadow-lg"
                >
                  <div class="flex items-center justify-between mb-2">
                    <span class="text-sm font-medium text-blue-300">你</span>
                    <span class="text-xs text-gray-500">{{
                      message.timestamp
                    }}</span>
                  </div>
                  <p class="text-gray-200 leading-relaxed">
                    {{ message.content }}
                  </p>
                </div>
                <div
                  class="w-10 h-10 rounded-full bg-linear-to-br from-blue-500 to-purple-600 flex items-center justify-center shrink-0"
                >
                  <span class="text-white font-medium text-sm">你</span>
                </div>
              </div>
            </div>

            <!-- 加载状态 -->
            <div v-if="isSubmitting" class="flex justify-start">
              <div class="flex items-start gap-3 max-w-[80%]">
                <div
                  class="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center shrink-0"
                >
                  <svg
                    class="w-5 h-5 text-blue-400 animate-spin"
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
                </div>
                <div
                  class="bg-gray-800/50 border border-gray-700/50 rounded-2xl rounded-tl-none p-4 shadow-lg"
                >
                  <div class="flex space-x-1">
                    <div
                      class="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
                      style="animation-delay: 0s"
                    ></div>
                    <div
                      class="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
                      style="animation-delay: 0.2s"
                    ></div>
                    <div
                      class="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
                      style="animation-delay: 0.4s"
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- 底部输入区域 -->
        <div class="border-t border-gray-700/50 p-4 bg-gray-900/80">
          <InterviewInput
            :is-recording="isRecording"
            :is-submitting="isSubmitting"
            :recording-time="recordingTime"
            :answer-countdown="answerCountdown"
            @send-message="handleInputMessage"
            @start-recording="startRecording"
            @stop-recording="stopRecording"
            @cancel-recording="cancelRecording"
          />
        </div>
      </div>
    </div>

    <!-- 确认对话框 -->
    <ConfirmDialog
      :show="showConfirmDialog"
      type="danger"
      title="确认结束面试？"
      message="结束面试后，本次面试记录将被保存，但您将无法继续回答剩余问题。确定要结束吗？"
      confirm-text="结束面试"
      cancel-text="继续面试"
      :loading="isLoading"
      :error-message="errorMessage"
      @confirm="confirmEndInterview"
      @cancel="cancelEndInterview"
    />
  </div>
</template>
