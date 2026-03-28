import { computed, onUnmounted, ref } from "vue";

import { synthesizeInterviewSpeech } from "@/lib/api";
import type { InterviewSpeakerRole } from "@/utils/token";

const INTERVIEW_TTS_ENABLED_KEY = "INTERVIEW_TTS_ENABLED";
const USER_ACTIVATION_EVENTS = ["pointerdown", "keydown", "touchstart"] as const;

export type InterviewTtsMessage = {
  id: number;
  text: string;
  speakerRole?: InterviewSpeakerRole;
};

const hasEdgeTtsSupport = () => {
  return (
    typeof window !== "undefined" &&
    typeof fetch !== "undefined" &&
    typeof Audio !== "undefined" &&
    typeof Blob !== "undefined"
  );
};

const loadStoredEnabled = () => {
  if (typeof window === "undefined") {
    return true;
  }

  const storedValue = window.localStorage.getItem(INTERVIEW_TTS_ENABLED_KEY);
  if (storedValue === null) {
    return true;
  }

  return storedValue !== "false";
};

const normalizeMessageText = (text: string) => {
  return text.replace(/\s+/g, " ").trim();
};

export const useInterviewTts = () => {
  const ttsEnabled = ref(loadStoredEnabled());
  const ttsSupported = computed(() => hasEdgeTtsSupport());
  const hasUserActivated = ref(
    typeof navigator === "undefined" ? true : (navigator.userActivation?.hasBeenActive ?? false),
  );
  const pendingMessage = ref<InterviewTtsMessage | null>(null);
  let activationListenersBound = false;
  let currentPlaybackToken = 0;
  let activeAudio: HTMLAudioElement | null = null;
  let activeAudioUrl: string | null = null;
  let activeAbortController: AbortController | null = null;

  const canSpeakNow = () => {
    if (typeof navigator === "undefined") {
      return true;
    }

    return hasUserActivated.value || navigator.userActivation?.hasBeenActive === true;
  };

  const cleanupActivationListeners = () => {
    if (typeof window === "undefined" || !activationListenersBound) {
      return;
    }

    USER_ACTIVATION_EVENTS.forEach((eventName) => {
      window.removeEventListener(eventName, handleUserActivation);
    });
    activationListenersBound = false;
  };

  const cleanupActiveAudio = () => {
    if (activeAbortController) {
      activeAbortController.abort();
      activeAbortController = null;
    }

    if (activeAudio) {
      activeAudio.pause();
      activeAudio.src = "";
      activeAudio = null;
    }

    if (activeAudioUrl) {
      URL.revokeObjectURL(activeAudioUrl);
      activeAudioUrl = null;
    }
  };

  const speakNow = async (message: InterviewTtsMessage) => {
    if (!ttsSupported.value) {
      return;
    }

    const text = normalizeMessageText(message.text);
    if (!text) {
      return;
    }

    const playbackToken = ++currentPlaybackToken;
    cleanupActiveAudio();

    try {
      const abortController = new AbortController();
      activeAbortController = abortController;
      const audioBlob = await synthesizeInterviewSpeech(text, abortController.signal);

      if (playbackToken !== currentPlaybackToken || !ttsEnabled.value) {
        return;
      }

      activeAbortController = null;

      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      const cleanupPlayback = () => {
        if (activeAudio === audio) {
          activeAudio = null;
        }

        if (activeAudioUrl === audioUrl) {
          URL.revokeObjectURL(audioUrl);
          activeAudioUrl = null;
        }

        audio.removeEventListener("ended", cleanupPlayback);
        audio.removeEventListener("error", cleanupPlayback);
      };

      activeAudio = audio;
      activeAudioUrl = audioUrl;
      audio.addEventListener("ended", cleanupPlayback);
      audio.addEventListener("error", cleanupPlayback);
      await audio.play();

      if (playbackToken !== currentPlaybackToken) {
        cleanupPlayback();
      }
    } catch (error) {
      if (playbackToken !== currentPlaybackToken) {
        return;
      }

      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }

      cleanupActiveAudio();
      console.error("Interview TTS request failed:", error);
    }
  };

  const flushPendingMessage = () => {
    if (!ttsSupported.value || !ttsEnabled.value || !pendingMessage.value) {
      return;
    }

    if (!canSpeakNow()) {
      bindActivationListeners();
      return;
    }

    const messageToSpeak = pendingMessage.value;
    pendingMessage.value = null;
    void speakNow(messageToSpeak);
  };

  const handleUserActivation = () => {
    hasUserActivated.value = true;
    cleanupActivationListeners();
    flushPendingMessage();
  };

  const bindActivationListeners = () => {
    if (typeof window === "undefined" || activationListenersBound || hasUserActivated.value) {
      return;
    }

    USER_ACTIVATION_EVENTS.forEach((eventName) => {
      window.addEventListener(eventName, handleUserActivation, { once: true });
    });
    activationListenersBound = true;
  };

  const stop = () => {
    currentPlaybackToken += 1;
    pendingMessage.value = null;
    cleanupActiveAudio();
  };

  const setEnabled = (enabled: boolean) => {
    ttsEnabled.value = enabled;

    if (typeof window !== "undefined") {
      window.localStorage.setItem(INTERVIEW_TTS_ENABLED_KEY, enabled ? "true" : "false");
    }

    if (!enabled) {
      stop();
      return;
    }

    flushPendingMessage();
  };

  const speakMessage = (message: InterviewTtsMessage) => {
    if (!ttsSupported.value || !ttsEnabled.value) {
      return;
    }

    const normalizedText = normalizeMessageText(message.text);
    if (!normalizedText) {
      return;
    }

    const nextMessage = { ...message, text: normalizedText };
    if (!canSpeakNow()) {
      pendingMessage.value = nextMessage;
      bindActivationListeners();
      return;
    }

    pendingMessage.value = null;
    void speakNow(nextMessage);
  };

  if (ttsSupported.value) {
    bindActivationListeners();
  }

  onUnmounted(() => {
    cleanupActivationListeners();
    stop();
  });

  return {
    ttsEnabled,
    ttsSupported,
    speakMessage,
    setEnabled,
    stop,
  };
};
