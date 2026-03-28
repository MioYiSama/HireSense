<script setup lang="ts">
import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import ConfidenceMeter from "@/components/ConfidenceMeter.vue";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import InterviewerStage from "@/components/InterviewerStage.vue";
import InterviewInput from "@/components/InterviewInput.vue";
import { getApiErrorMessage, queryKeys, replyInterview, stopInterview } from "@/lib/api";
import { getCodeLanguageForJob, getCodeLanguageLabel, type CodeLanguage } from "@/lib/codeEditor";
import type { AvatarAnimationMode } from "@/lib/interviewerAvatar";
import { useConfidenceMeter } from "@/lib/useConfidenceMeter";
import { useInterviewTts } from "@/lib/useInterviewTts";
import {
  getAccessToken,
  getInterviewId,
  getInitialInterviewState,
  getUserInfo,
  removeInterviewId,
  removeInitialReply,
  type InterviewMode,
  type InterviewSpeakerRole,
} from "@/utils/token";

const CodeEditorDialog = defineAsyncComponent(() => import("@/components/CodeEditorDialog.vue"));

// 常量定义
const INITIAL_LOADING_DELAY = 1500;
const SCROLL_DELAY = 100;
const AUDIO_URL_RELEASE_DELAY = 1000;
const ANSWER_COUNTDOWN_TIME = 60;

const router = useRouter();
const queryClient = useQueryClient();
const showConfirmDialog = ref(false);
const interviewTime = ref(0);
const timerInterval = ref<number | null>(null);
const errorMessage = ref("");
const interviewId = ref(getInterviewId());
const storedUserInfo = getUserInfo();
const storedInitialInterviewState = getInitialInterviewState();

// 录音状态
const isRecording = ref(false);
const recordingTime = ref(0);
const recordingInterval = ref<number | null>(null);
const mediaRecorder = ref<MediaRecorder | null>(null);
const activeRecordingStream = ref<MediaStream | null>(null);
const audioChunks = ref<Blob[]>([]);
const isCancelingRecording = ref(false);
const answerCountdown = ref(ANSWER_COUNTDOWN_TIME);
const countdownInterval = ref<number | null>(null);
const confidenceMeter = useConfidenceMeter();
const confidenceMeterSnapshot = confidenceMeter.snapshot;
const isConfidenceMeterSupported = confidenceMeter.supported;

// 定义消息类型
type MessageType = "text" | "audio" | "code";

interface Message {
  id: number;
  role: "ai" | "user";
  type: MessageType;
  content: string;
  timestamp: string;
  speakerRole?: InterviewSpeakerRole;
  audioBlob?: Blob;
  duration?: number;
  codeLanguage?: CodeLanguage;
}

// 对话相关状态
const messages = ref<Message[]>([]);
const isInterviewEnded = ref(false);
const stageAnimationMode = ref<AvatarAnimationMode>("idle");
const chatContainer = ref<HTMLElement | null>(null);
const isCodeEditorOpen = ref(false);
const codeDraft = ref("");
const codeLanguage = ref<CodeLanguage>(getCodeLanguageForJob(storedUserInfo?.job));
const activeInterviewMode = ref<InterviewMode>(storedInitialInterviewState?.mode ?? "single");
const { ttsEnabled, ttsSupported, speakMessage, setEnabled: setTtsEnabled, stop: stopTts } =
  useInterviewTts();
let stageSpeakingTimeout: number | null = null;

// 音频播放状态
const audioElements = ref<{ [key: number]: HTMLAudioElement }>({});
const isPlaying = ref<{ [key: number]: boolean }>({});

// 清理音频资源
const cleanupAudioResources = (messageId: number) => {
  // 停止并移除音频元素
  if (audioElements.value[messageId]) {
    audioElements.value[messageId].pause();
    // 释放创建的URL
    const audio = audioElements.value[messageId];
    if (audio.src) {
      URL.revokeObjectURL(audio.src);
    }
    delete audioElements.value[messageId];
    delete isPlaying.value[messageId];
  }
};

const createMessageId = () => Date.now() + Math.floor(Math.random() * 1000);

const normalizeSpeakerRole = (speakerRole?: string): InterviewSpeakerRole => {
  if (speakerRole === "hr" || speakerRole === "tech_lead" || speakerRole === "executive") {
    return speakerRole;
  }
  return "ai";
};

const pushTextMessage = (
  role: Message["role"],
  content: string,
  speakerRole?: InterviewSpeakerRole,
) => {
  const message: Message = {
    id: createMessageId(),
    role,
    type: "text",
    content,
    timestamp: new Date().toLocaleTimeString(),
    speakerRole: role === "ai" ? normalizeSpeakerRole(speakerRole) : undefined,
  };
  messages.value.push(message);
  return message;
};

const appendAiTextMessage = (content: string, speakerRole?: InterviewSpeakerRole) => {
  const message = pushTextMessage("ai", content, speakerRole);
  triggerStageSpeaking();
  speakMessage({
    id: message.id,
    text: message.content,
    speakerRole: message.speakerRole,
  });
};

const pushCodeMessage = (content: string, language: CodeLanguage) => {
  messages.value.push({
    id: createMessageId(),
    role: "user",
    type: "code",
    content,
    timestamp: new Date().toLocaleTimeString(),
    codeLanguage: language,
  });
};

const pushErrorReply = (content: string) => {
  appendAiTextMessage(
    content,
    activeInterviewMode.value === "panel_trio" ? latestSpeakerRole.value : "ai",
  );
};

// 处理输入消息
const handleInputMessage = (message: string) => {
  void sendTextMessage(message);
};

const handleOpenCodeEditor = () => {
  if (isRecording.value || isSubmitting.value || isInterviewEnded.value) {
    return;
  }

  isCodeEditorOpen.value = true;
};

const handleCloseCodeEditor = () => {
  if (isSubmitting.value) {
    return;
  }

  isCodeEditorOpen.value = false;
};

// 播放音频消息
const toggleAudioPlayback = (messageId: number) => {
  stopTts();

  const message = messages.value.find((msg) => msg.id === messageId);
  if (!message || message.type !== "audio" || !message.audioBlob) return;

  // 停止其他正在播放的音频
  Object.keys(audioElements.value).forEach((key) => {
    const id = parseInt(key);
    if (id !== messageId && audioElements.value[id]) {
      audioElements.value[id].pause();
      isPlaying.value[id] = false;
    }
  });

  // 检查是否已经有音频元素
  if (!audioElements.value[messageId]) {
    // 创建新的音频元素
    const audio = new Audio(URL.createObjectURL(message.audioBlob));
    audioElements.value[messageId] = audio;

    // 监听播放结束事件
    audio.addEventListener("ended", () => {
      isPlaying.value[messageId] = false;
    });
  }

  const audio = audioElements.value[messageId];
  if (audio.paused) {
    audio.play();
    isPlaying.value[messageId] = true;
  } else {
    audio.pause();
    isPlaying.value[messageId] = false;
  }
};

// 自动滚动到最新消息
const scrollToBottom = () => {
  setTimeout(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
    }
  }, SCROLL_DELAY);
};

// 返回面试中心
const goBackToDashboard = () => {
  stopTts();
  // 删除存储的面试ID
  removeInterviewId();
  // 跳转到dashboard页面
  router.push("/dashboard");
};
const isInitialLoading = ref(true);
const ttsStatusLabel = computed(() => {
  if (!ttsSupported.value) {
    return "TTS 不可用";
  }

  return ttsEnabled.value ? "朗读开" : "朗读关";
});

type InterviewReplyPayload = { text: string } | Blob;

const stopInterviewMutation = useMutation({
  mutationFn: stopInterview,
});

const replyInterviewMutation = useMutation({
  mutationFn: async (payload: InterviewReplyPayload) => {
    const id = getInterviewId();

    if (!id) {
      throw new Error("面试ID不存在");
    }

    return replyInterview({
      id,
      payload,
      contentType: payload instanceof Blob ? payload.type || "audio/wav" : undefined,
    });
  },
});

const isLoading = computed(() => stopInterviewMutation.isPending.value);
const isSubmitting = computed(() => replyInterviewMutation.isPending.value);

const clearStageSpeakingTimeout = () => {
  if (stageSpeakingTimeout) {
    clearTimeout(stageSpeakingTimeout);
    stageSpeakingTimeout = null;
  }
};

const syncStageAnimationMode = () => {
  if (isInterviewEnded.value) {
    stageAnimationMode.value = "ended";
    return;
  }

  if (isRecording.value) {
    stageAnimationMode.value = "listening";
    return;
  }

  if (isSubmitting.value || isInitialLoading.value) {
    stageAnimationMode.value = "thinking";
    return;
  }

  stageAnimationMode.value = "idle";
};

const triggerStageSpeaking = () => {
  clearStageSpeakingTimeout();

  if (isInterviewEnded.value) {
    stageAnimationMode.value = "ended";
    return;
  }

  stageAnimationMode.value = "speaking";
  stageSpeakingTimeout = window.setTimeout(() => {
    stageSpeakingTimeout = null;
    syncStageAnimationMode();
  }, 1800);
};

const latestSpeakerRole = computed<InterviewSpeakerRole>(() => {
  const latestMessage = [...messages.value]
    .reverse()
    .find((message) => message.role === "ai" && message.speakerRole);
  return latestMessage?.speakerRole ?? (activeInterviewMode.value === "panel_trio" ? "hr" : "ai");
});

const panelInterviewers: Array<{
  role: Extract<InterviewSpeakerRole, "hr" | "tech_lead" | "executive">;
  label: string;
  description: string;
}> = [
  {
    role: "hr",
    label: "HR",
    description: "经历、沟通、动机",
  },
  {
    role: "tech_lead",
    label: "技术主管",
    description: "技术深挖、实现取舍",
  },
  {
    role: "executive",
    label: "大老板",
    description: "业务影响、Owner 意识",
  },
];

const getSpeakerMeta = (speakerRole?: InterviewSpeakerRole) => {
  const role = normalizeSpeakerRole(speakerRole);

  if (role === "hr") {
    return {
      label: "HR 面试官",
      chipClass: "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20",
      avatarClass: "bg-emerald-500/20 text-emerald-300",
    };
  }

  if (role === "tech_lead") {
    return {
      label: "技术主管",
      chipClass: "bg-cyan-500/10 text-cyan-300 border border-cyan-500/20",
      avatarClass: "bg-cyan-500/20 text-cyan-300",
    };
  }

  if (role === "executive") {
    return {
      label: "大老板",
      chipClass: "bg-fuchsia-500/10 text-fuchsia-300 border border-fuchsia-500/20",
      avatarClass: "bg-fuchsia-500/20 text-fuchsia-300",
    };
  }

  return {
    label: "AI 面试官",
    chipClass: "bg-blue-500/10 text-blue-300 border border-blue-500/20",
    avatarClass: "bg-blue-500/20 text-blue-300",
  };
};

const currentStageRole = computed<InterviewSpeakerRole>(() => {
  return latestSpeakerRole.value;
});

const stageStatusLabel = computed(() => {
  const currentSpeaker = getSpeakerMeta(currentStageRole.value).label;

  if (isInterviewEnded.value) {
    return "面试已结束，系统正在收束本轮问答并整理结果。";
  }

  if (isRecording.value) {
    return `${currentSpeaker} 正在聆听你的回答，继续完整讲清楚思路。`;
  }

  if (isSubmitting.value || isInitialLoading.value) {
    return `${currentSpeaker} 正在组织下一轮追问。`;
  }

  if (activeInterviewMode.value === "panel_trio") {
    return `${currentSpeaker} 当前在场，左侧舞台会随发言人切换。`;
  }

  return "准备进入下一轮提问。";
});

watch(
  [isRecording, isSubmitting, isInterviewEnded, isInitialLoading],
  () => {
    if (isInterviewEnded.value || isRecording.value || isSubmitting.value || isInitialLoading.value) {
      clearStageSpeakingTimeout();
      syncStageAnimationMode();
      return;
    }

    if (stageAnimationMode.value !== "speaking") {
      syncStageAnimationMode();
    }
  },
  { immediate: true },
);

const stopRecordingTimers = () => {
  if (recordingInterval.value) {
    clearInterval(recordingInterval.value);
    recordingInterval.value = null;
  }

  if (countdownInterval.value) {
    clearInterval(countdownInterval.value);
    countdownInterval.value = null;
  }
};

const resetRecordingCountdown = () => {
  recordingTime.value = 0;
  answerCountdown.value = ANSWER_COUNTDOWN_TIME;
};

const releaseRecordingStream = () => {
  if (!activeRecordingStream.value) {
    return;
  }

  activeRecordingStream.value.getTracks().forEach((track) => track.stop());
  activeRecordingStream.value = null;
};

const finalizeRecordingSession = () => {
  releaseRecordingStream();
  mediaRecorder.value = null;
};

// API请求函数
const sendInterviewReply = async (payload: InterviewReplyPayload) => {
  const data = await replyInterviewMutation.mutateAsync(payload);

  activeInterviewMode.value = data.mode;
  appendAiTextMessage(data.reply, normalizeSpeakerRole(data.speaker_role));

  // 检查是否面试结束
  if (data.ending) {
    console.log("面试已结束");
    isInterviewEnded.value = true;
    void queryClient.invalidateQueries({ queryKey: queryKeys.interviews() });

    if (timerInterval.value) {
      clearInterval(timerInterval.value);
    }
    stopRecordingTimers();
    if (mediaRecorder.value && isRecording.value) {
      isCancelingRecording.value = true;
      audioChunks.value = [];
      confidenceMeter.cancelAndHide();
      mediaRecorder.value.stop();
      isRecording.value = false;
    }
  }
};

const sendTextMessage = async (message: string) => {
  const inputContent = message.trim();
  if (!inputContent || isSubmitting.value || isInterviewEnded.value) return;

  stopTts();
  pushTextMessage("user", inputContent);
  console.log("用户输入:", inputContent);

  try {
    await sendInterviewReply({ text: inputContent });
  } catch (error) {
    console.error("发送消息失败:", error);
    pushErrorReply("抱歉，我暂时无法回复，请稍后再试。");
  }
};

const handleCodeSubmit = async () => {
  const content = codeDraft.value;
  if (!content.trim() || isSubmitting.value || isInterviewEnded.value) {
    return;
  }

  stopTts();
  const language = codeLanguage.value;
  pushCodeMessage(content, language);
  isCodeEditorOpen.value = false;

  try {
    await sendInterviewReply({ text: content });
    codeDraft.value = "";
  } catch (error) {
    console.error("发送代码失败:", error);
    pushErrorReply("抱歉，我暂时无法处理这段代码，请稍后再试。");
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
    const initialState = storedInitialInterviewState;
    activeInterviewMode.value = initialState?.mode ?? "single";
    const initialReply = initialState?.reply ?? "";
    appendAiTextMessage(
      initialReply ||
        "你好！我是你的AI面试官。欢迎参加今天的面试。请先做一个简短的自我介绍，然后我们将开始技术问题的讨论。",
      normalizeSpeakerRole(initialState?.speakerRole),
    );
    // 清除已使用的初始回复
    removeInitialReply();
    scrollToBottom();
  }, INITIAL_LOADING_DELAY);

  // 监听消息变化，自动滚动到最新消息
  watch(
    messages,
    () => {
      scrollToBottom();
    },
    { deep: true },
  );
});

onUnmounted(() => {
  // 清除计时器
  if (timerInterval.value) {
    clearInterval(timerInterval.value);
  }

  stopTts();
  clearStageSpeakingTimeout();

  // 清理所有音频资源
  Object.keys(audioElements.value).forEach((key) => {
    const messageId = parseInt(key);
    cleanupAudioResources(messageId);
  });

  stopRecordingTimers();

  if (mediaRecorder.value && isRecording.value) {
    isCancelingRecording.value = true;
    audioChunks.value = [];
    mediaRecorder.value.stop();
  }

  confidenceMeter.reset();
  releaseRecordingStream();
});

const endInterview = () => {
  // 显示确认对话框
  showConfirmDialog.value = true;
};

const toggleTts = () => {
  if (!ttsSupported.value) {
    return;
  }

  setTtsEnabled(!ttsEnabled.value);
};

const confirmEndInterview = async () => {
  // 显示加载状态
  errorMessage.value = "";

  try {
    // 从localStorage获取token
    const token = getAccessToken();

    if (!token) {
      errorMessage.value = "请先登录";
      return;
    }

    if (!interviewId.value) {
      errorMessage.value = "面试ID不存在";
      return;
    }

    await stopInterviewMutation.mutateAsync({ id: interviewId.value });

    stopTts();
    if (timerInterval.value) {
      clearInterval(timerInterval.value);
    }
    removeInterviewId();
    showConfirmDialog.value = false;
    await queryClient.invalidateQueries({ queryKey: queryKeys.interviews() });
    router.push("/dashboard");
  } catch (error) {
    console.error("结束面试失败:", error);
    errorMessage.value = getApiErrorMessage(error, "网络错误，请稍后重试");
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
    stopTts();
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    activeRecordingStream.value = stream;
    mediaRecorder.value = new MediaRecorder(stream, { mimeType: "audio/webm" });
    audioChunks.value = [];
    isCancelingRecording.value = false;
    await confidenceMeter.start(stream);

    mediaRecorder.value.ondataavailable = (event) => {
      if (event.data.size > 0 && !isCancelingRecording.value) {
        audioChunks.value.push(event.data);
      }
    };

    mediaRecorder.value.onstop = async () => {
      const finalDuration = recordingTime.value;

      try {
        // 检查是否有录音数据
        if (audioChunks.value.length === 0) {
          console.log("录音被中断，没有数据");
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
          await sendAudioMessage(wavBlob, finalDuration);

          // 可以在这里将WAV文件发送到服务器或进行其他处理
          const wavUrl = URL.createObjectURL(wavBlob);
          console.log("WAV文件URL:", wavUrl);

          // 清理URL对象
          setTimeout(() => URL.revokeObjectURL(wavUrl), AUDIO_URL_RELEASE_DELAY);
        } catch (error) {
          console.error("WAV转换失败:", error);
        }
      } finally {
        audioChunks.value = [];
        resetRecordingCountdown();
        isCancelingRecording.value = false;
        finalizeRecordingSession();
      }
    };

    mediaRecorder.value.start();
    isRecording.value = true;
    resetRecordingCountdown();

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
    confidenceMeter.reset();
    finalizeRecordingSession();
    alert("无法访问麦克风，请确保已授予权限");
  }
};

// 停止录音
const stopRecording = () => {
  if (mediaRecorder.value && isRecording.value) {
    confidenceMeter.freezeAndHide();
    mediaRecorder.value.stop();
    isRecording.value = false;
    stopRecordingTimers();
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
    confidenceMeter.cancelAndHide();
    mediaRecorder.value.stop();
    isRecording.value = false;
    stopRecordingTimers();

    // 重置录音时间
    resetRecordingCountdown();

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
    type: "audio",
    content: `[语音消息] ${formatRecordingTime(duration)}`,
    timestamp: new Date().toLocaleTimeString(),
    audioBlob,
    duration,
  };
  messages.value.push(newMessage);

  try {
    await sendInterviewReply(audioBlob);
  } catch (error) {
    console.error("发送语音消息失败:", error);
    pushErrorReply("抱歉，我暂时无法处理语音消息，请稍后再试。");
  }
};

// 格式化录音时间
const formatRecordingTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
};

const formatCodeLanguage = (language: string | undefined) => {
  return getCodeLanguageLabel(language);
};
</script>

<template>
  <div
    class="relative min-h-screen overflow-hidden bg-linear-to-br from-gray-900 via-gray-800 to-gray-900"
  >
    <ConfidenceMeter
      v-if="isConfidenceMeterSupported"
      :snapshot="confidenceMeterSnapshot"
      :recording-time="recordingTime"
      :answer-countdown="answerCountdown"
    />

    <!-- 背景 -->
    <div class="absolute top-0 left-1/4 h-96 w-96 rounded-full bg-blue-500/10 blur-3xl"></div>
    <div class="absolute right-1/4 bottom-0 h-96 w-96 rounded-full bg-purple-500/10 blur-3xl"></div>

    <!-- 导航栏 -->
    <div
      class="navbar relative z-10 border-b border-gray-700/50 bg-gray-900/60 shadow-lg backdrop-blur-md"
    >
      <div class="flex-1">
        <div class="flex items-center gap-2">
          <img src="/favicon.png" alt="HireSense" class="h-8 w-8 rounded-md object-contain" />
          <span class="text-xl font-bold tracking-tight text-white">Hire Sense</span>
        </div>
      </div>
      <div class="flex flex-none items-center gap-4">
        <!-- 面试时长计时器 -->
        <div
          class="flex items-center gap-2 rounded-xl border border-gray-700/50 bg-gray-800/50 px-4 py-1.5 shadow-lg"
        >
          <svg class="h-4 w-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span class="font-mono text-sm text-gray-300">
            {{ formatTime(interviewTime) }}
          </span>
        </div>

        <button
          @click="toggleTts"
          :disabled="!ttsSupported"
          :aria-pressed="ttsSupported ? ttsEnabled : undefined"
          class="group flex items-center gap-2 rounded-xl border px-4 py-1.5 font-medium shadow-lg transition-all duration-300 disabled:cursor-not-allowed disabled:opacity-60"
          :class="
            !ttsSupported
              ? 'border-gray-700/60 bg-gray-800/50 text-gray-500'
              : ttsEnabled
                ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-300 hover:border-emerald-400 hover:bg-emerald-500/20'
                : 'border-gray-700/60 bg-gray-800/70 text-gray-300 hover:border-gray-600 hover:bg-gray-800/90'
          "
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M11 5L6 9H3v6h3l5 4V5z"
            />
            <path
              v-if="ttsSupported && ttsEnabled"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M15.54 8.46a5 5 0 010 7.07M18.36 5.64a9 9 0 010 12.72"
            />
            <path
              v-else
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 5L5 19"
            />
          </svg>
          <span>{{ ttsStatusLabel }}</span>
        </button>

        <!-- 结束面试按钮 -->
        <button
          @click="endInterview"
          :disabled="messages.length < 3"
          class="group flex cursor-pointer items-center gap-2 rounded-xl border border-red-500/40 bg-linear-to-r from-red-500/20 to-red-600/20 px-4 py-1.5 font-semibold text-red-400 shadow-lg shadow-red-500/10 transition-all duration-300 hover:scale-105 hover:border-red-500 hover:from-red-500 hover:to-red-600 hover:text-white hover:shadow-red-500/30 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100 disabled:hover:from-red-500/20 disabled:hover:to-red-600/20 disabled:hover:text-red-400"
        >
          <div class="relative">
            <svg
              class="h-4 w-4 transition-transform duration-300 group-hover:rotate-90"
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
            class="-ml-2 h-3 w-3 opacity-0 transition-all duration-300 group-hover:ml-0 group-hover:opacity-100"
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
    <div class="flex flex-1 justify-center p-4 md:p-6 xl:p-8">
      <div class="flex h-[calc(100vh-8rem)] w-full max-w-7xl flex-col gap-4 lg:flex-row">
        <aside class="h-[32vh] min-h-[19rem] w-full shrink-0 md:min-h-[21rem] lg:h-full lg:min-h-[23rem] lg:w-[19.5rem] lg:max-w-[19.5rem] xl:w-[21rem] xl:max-w-[21rem]">
          <InterviewerStage
            class="h-full"
            :role="currentStageRole"
            :mode="stageAnimationMode"
            :status-label="stageStatusLabel"
            :panel-mode="activeInterviewMode === 'panel_trio'"
          />
        </aside>

        <div
          class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-gray-700/50 bg-gray-900/60 shadow-xl backdrop-blur-md"
        >
          <div
            v-if="activeInterviewMode === 'panel_trio'"
            class="grid grid-cols-1 gap-3 border-b border-white/6 bg-white/2 p-4 md:grid-cols-3"
          >
            <div
              v-for="member in panelInterviewers"
              :key="member.role"
              :class="[
                'rounded-2xl border p-4 transition-all duration-200',
                latestSpeakerRole === member.role
                  ? 'border-white/15 bg-white/6 shadow-lg'
                  : 'border-white/6 bg-white/3',
              ]"
            >
              <div class="flex items-center justify-between gap-3">
                <span class="text-sm font-semibold text-white">{{ member.label }}</span>
                <span
                  class="rounded-full px-2.5 py-1 text-[11px] font-medium"
                  :class="getSpeakerMeta(member.role).chipClass"
                >
                  {{ latestSpeakerRole === member.role ? "当前发言" : "在场" }}
                </span>
              </div>
              <p class="mt-2 text-xs leading-relaxed text-slate-400">
                {{ member.description }}
              </p>
            </div>
          </div>
 
          <!-- 对话内容展示区 -->
          <div ref="chatContainer" class="flex-1 space-y-6 overflow-y-auto p-6">
            <!-- 初始加载状态 -->
            <div v-if="isInitialLoading" class="flex h-full items-center justify-center">
              <div class="text-center">
                <div
                  class="mx-auto mb-4 flex h-16 w-16 animate-pulse items-center justify-center rounded-full bg-blue-500/20"
                >
                  <svg
                    class="h-8 w-8 animate-spin text-blue-400"
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
                <p class="text-gray-400">
                  {{ activeInterviewMode === "panel_trio" ? "群面官正在就位..." : "AI面试官正在准备中..." }}
                </p>
              </div>
            </div>
 
            <!-- 消息列表 -->
            <template v-else>
              <div
                v-for="message in messages"
                :key="message.id"
                class="animate-message-in flex"
                :class="message.role === 'ai' ? 'justify-start' : 'justify-end'"
              >
                <!-- AI面试官消息 -->
                <div v-if="message.role === 'ai'" class="flex max-w-[80%] flex-col items-start gap-1">
                <div class="flex items-start gap-3">
                  <div
                    class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
                    :class="getSpeakerMeta(message.speakerRole).avatarClass"
                  >
                    <svg
                      class="h-5 w-5"
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
                    class="rounded-2xl rounded-tl-none bg-gray-800/50 p-4 shadow-lg shadow-gray-900/50"
                  >
                    <div class="mb-2 flex items-center gap-2">
                      <span
                        class="rounded-full px-2.5 py-1 text-xs font-medium"
                        :class="getSpeakerMeta(message.speakerRole).chipClass"
                      >
                        {{ getSpeakerMeta(message.speakerRole).label }}
                      </span>
                    </div>
                    <div v-if="message.type === 'audio'" class="flex items-center gap-3">
                      <button
                        @click="toggleAudioPlayback(message.id)"
                        class="flex h-10 w-10 items-center justify-center rounded-full bg-blue-500/20 transition-colors hover:bg-blue-500/30"
                      >
                        <svg
                          v-if="!isPlaying[message.id]"
                          class="h-5 w-5 text-blue-400"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                          />
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                        <svg
                          v-else
                          class="h-5 w-5 text-blue-400"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                      </button>
                      <span class="text-gray-300">{{ message.content }}</span>
                    </div>
                    <div v-else-if="message.type === 'code'" class="space-y-3">
                      <div class="flex items-center gap-2">
                        <span
                          class="inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/10 px-2.5 py-1 text-xs font-medium text-blue-200"
                        >
                          代码
                        </span>
                        <span class="text-xs text-gray-400">
                          {{ formatCodeLanguage(message.codeLanguage) }}
                        </span>
                      </div>
                      <pre
                        class="max-h-80 overflow-auto rounded-2xl border border-gray-700/70 bg-[#060b16] p-4 font-mono text-[13px] leading-6 text-slate-100"
                      ><code>{{ message.content }}</code></pre>
                    </div>
                    <p v-else class="leading-relaxed text-gray-300">
                      {{ message.content }}
                    </p>
                  </div>
                </div>
                <div class="ml-[52px]">
                  <span class="text-xs text-gray-500">{{ message.timestamp }}</span>
                </div>
              </div>

              <!-- 用户消息 -->
              <div v-else class="flex max-w-[80%] flex-col items-end gap-1">
                <div class="flex items-start gap-3">
                  <div
                    class="rounded-2xl rounded-tr-none bg-linear-to-r from-blue-500/20 to-purple-500/20 p-4 shadow-lg shadow-blue-900/20"
                  >
                    <div class="mb-2 flex items-center">
                      <span class="text-sm font-medium text-blue-300">你</span>
                    </div>
                    <div v-if="message.type === 'audio'" class="flex items-center gap-3">
                      <button
                        @click="toggleAudioPlayback(message.id)"
                        class="flex h-10 w-10 items-center justify-center rounded-full bg-blue-500/20 transition-colors hover:bg-blue-500/30"
                      >
                        <svg
                          v-if="!isPlaying[message.id]"
                          class="h-5 w-5 text-blue-400"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                          />
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                        <svg
                          v-else
                          class="h-5 w-5 text-blue-400"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                      </button>
                      <span class="text-gray-200">{{ message.content }}</span>
                    </div>
                    <div v-else-if="message.type === 'code'" class="space-y-3">
                      <div class="flex items-center gap-2">
                        <span
                          class="inline-flex items-center rounded-full border border-cyan-400/30 bg-cyan-500/10 px-2.5 py-1 text-xs font-medium text-cyan-100"
                        >
                          代码
                        </span>
                        <span class="text-xs text-blue-100/80">
                          {{ formatCodeLanguage(message.codeLanguage) }}
                        </span>
                      </div>
                      <pre
                        class="max-h-80 overflow-auto rounded-2xl border border-white/10 bg-[#050b16]/90 p-4 font-mono text-[13px] leading-6 text-slate-100"
                      ><code>{{ message.content }}</code></pre>
                    </div>
                    <p v-else class="leading-relaxed text-gray-200">
                      {{ message.content }}
                    </p>
                  </div>
                  <div
                    class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-linear-to-br from-blue-500 to-purple-600"
                  >
                    <span class="text-sm font-medium text-white">你</span>
                  </div>
                </div>
                <div class="mr-[52px]">
                  <span class="text-xs text-gray-500">{{ message.timestamp }}</span>
                </div>
              </div>
            </div>

            <!-- 面试结束提示 -->
            <div v-if="isInterviewEnded" class="mt-8">
              <div
                class="rounded-2xl border border-blue-500/30 bg-linear-to-r from-blue-500/20 to-purple-600/20 p-6 text-center shadow-lg"
              >
                <div class="mb-4 flex justify-center">
                  <div
                    class="flex h-16 w-16 items-center justify-center rounded-full bg-green-500/20"
                  >
                    <svg
                      class="h-8 w-8 text-green-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                  </div>
                </div>
                <h3 class="mb-2 text-xl font-semibold text-white">面试已完成</h3>
                <p class="mb-6 text-gray-300">
                  感谢您的精彩表现！面试官已收到您的回答，我们将尽快生成面试报告。
                  <br /><br />
                  请回到面试中心耐心等待结果通知。
                </p>
                <button
                  @click="goBackToDashboard"
                  class="transform rounded-xl bg-linear-to-r from-blue-500 to-purple-600 px-6 py-3 font-semibold text-white shadow-lg transition-all duration-300 hover:scale-105 hover:from-blue-600 hover:to-purple-700 hover:shadow-blue-500/20"
                >
                  返回面试中心
                </button>
              </div>
            </div>

            <!-- 加载状态 -->
            <div v-if="isSubmitting" class="animate-message-in flex justify-start">
              <div class="flex max-w-[80%] items-start gap-3">
                <div
                  class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-500/20"
                >
                  <svg
                    class="h-5 w-5 animate-spin text-blue-400"
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
                  class="rounded-2xl rounded-tl-none bg-gray-800/50 p-4 shadow-lg shadow-gray-900/50"
                >
                  <div class="flex space-x-1.5">
                    <div
                      class="h-2 w-2 animate-bounce rounded-full bg-blue-400"
                      style="animation-delay: 0s"
                    ></div>
                    <div
                      class="h-2 w-2 animate-bounce rounded-full bg-blue-400"
                      style="animation-delay: 0.2s"
                    ></div>
                    <div
                      class="h-2 w-2 animate-bounce rounded-full bg-blue-400"
                      style="animation-delay: 0.4s"
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- 底部输入区域 -->
        <div
          class="border-t border-gray-700/50 bg-gray-900/90 p-4 backdrop-blur-sm transition-all duration-300 hover:border-gray-600/50"
        >
          <InterviewInput
            :is-recording="isRecording"
            :is-submitting="isSubmitting"
            :recording-time="recordingTime"
            :answer-countdown="answerCountdown"
            :is-interview-ended="isInterviewEnded"
            @send-message="handleInputMessage"
            @start-recording="startRecording"
            @stop-recording="stopRecording"
            @cancel-recording="cancelRecording"
            @open-code-editor="handleOpenCodeEditor"
          />
        </div>
      </div>
    </div>
    </div>

    <CodeEditorDialog
      v-if="isCodeEditorOpen"
      :show="isCodeEditorOpen"
      :code="codeDraft"
      :language="codeLanguage"
      :is-submitting="isSubmitting"
      @update:code="codeDraft = $event"
      @close="handleCloseCodeEditor"
      @submit="handleCodeSubmit"
    />

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

<style scoped>
/* 消息气泡渐入动画 */
@keyframes message-fade-in {
  from {
    opacity: 0;
    transform: translateY(16px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.animate-message-in {
  animation: message-fade-in 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
</style>
