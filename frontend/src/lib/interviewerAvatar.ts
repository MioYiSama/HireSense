import type { InterviewSpeakerRole } from "@/utils/token";

export type AvatarPresetKey = "ai" | "hr" | "tech_lead" | "executive";

export type AvatarAnimationMode = "idle" | "listening" | "thinking" | "speaking" | "ended";

export type InterviewerStageState = {
  role: AvatarPresetKey;
  animationMode: AvatarAnimationMode;
  statusLabel: string;
};

export type AvatarPreset = {
  key: AvatarPresetKey;
  label: string;
  accent: string;
  backgroundFrom: string;
  backgroundTo: string;
  backgroundGlow: string;
  stageTint: number;
  modelPath: string;
  modelScale: number;
  modelPosition: { x: number; y: number; z: number };
  modelRotationY: number;
  lookAt: { x: number; y: number; z: number };
  idleAction?: string;
};

const SHARED_MODEL_PATH_MALE = "/models/business-man.glb";

const PRESETS: Record<AvatarPresetKey, AvatarPreset> = {
  ai: {
    key: "ai",
    label: "AI 面试官",
    accent: "#60a5fa",
    backgroundFrom: "#050b18",
    backgroundTo: "#163454",
    backgroundGlow: "rgba(96, 165, 250, 0.22)",
    stageTint: 0x13304a,
    modelPath: SHARED_MODEL_PATH_MALE,
    modelScale: 1.74,
    modelPosition: { x: 0, y: -1.8, z: 0.08 },
    modelRotationY: 0,
    lookAt: { x: 0, y: 0.98, z: 0.18 },
  },
  hr: {
    key: "hr",
    label: "HR 面试官",
    accent: "#34d399",
    backgroundFrom: "#081812",
    backgroundTo: "#1e4b3f",
    backgroundGlow: "rgba(52, 211, 153, 0.22)",
    stageTint: 0x183f35,
    modelPath: SHARED_MODEL_PATH_MALE,
    modelScale: 1.74,
    modelPosition: { x: 0, y: -1.8, z: 0.08 },
    modelRotationY: 0,
    lookAt: { x: 0, y: 0.98, z: 0.18 },
  },
  tech_lead: {
    key: "tech_lead",
    label: "技术主管",
    accent: "#22d3ee",
    backgroundFrom: "#051319",
    backgroundTo: "#104556",
    backgroundGlow: "rgba(34, 211, 238, 0.22)",
    stageTint: 0x113541,
    modelPath: SHARED_MODEL_PATH_MALE,
    modelScale: 1.74,
    modelPosition: { x: 0, y: -1.8, z: 0.08 },
    modelRotationY: 0,
    lookAt: { x: 0, y: 0.98, z: 0.18 },
  },
  executive: {
    key: "executive",
    label: "大老板",
    accent: "#f472b6",
    backgroundFrom: "#180612",
    backgroundTo: "#512142",
    backgroundGlow: "rgba(244, 114, 182, 0.24)",
    stageTint: 0x44203b,
    modelPath: SHARED_MODEL_PATH_MALE,
    modelScale: 1.74,
    modelPosition: { x: 0, y: -1.8, z: 0.08 },
    modelRotationY: 0,
    lookAt: { x: 0, y: 0.98, z: 0.18 },
  },
};

export const getAvatarPreset = (role?: InterviewSpeakerRole): AvatarPreset => {
  if (role === "hr" || role === "tech_lead" || role === "executive") {
    return PRESETS[role];
  }

  return PRESETS.ai;
};
