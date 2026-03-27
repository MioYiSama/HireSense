<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

import { getAvatarPreset, type AvatarAnimationMode } from "@/lib/interviewerAvatar";
import type { InterviewSpeakerRole } from "@/utils/token";

const props = withDefaults(
  defineProps<{
    role: InterviewSpeakerRole;
    mode: AvatarAnimationMode;
    statusLabel: string;
    panelMode?: boolean;
  }>(),
  {
    panelMode: false,
  },
);

const stageEl = ref<HTMLDivElement | null>(null);
const canvasEl = ref<HTMLCanvasElement | null>(null);
const useFallback = ref(false);
const preset = computed(() => getAvatarPreset(props.role));

const stageBackgroundStyle = computed(() => {
  const currentPreset = preset.value;

  return {
    background: [
      `radial-gradient(circle at 50% 18%, ${currentPreset.backgroundGlow}, transparent 42%)`,
      "radial-gradient(circle at 50% 74%, rgba(255, 255, 255, 0.06), transparent 44%)",
      `linear-gradient(180deg, ${currentPreset.backgroundFrom} 0%, ${currentPreset.backgroundTo} 100%)`,
    ].join(", "),
  };
});

const stageBorderStyle = computed(() => ({
  borderColor: `${preset.value.accent}2b`,
}));

const loader = new GLTFLoader();

let renderer: THREE.WebGLRenderer | null = null;
let scene: THREE.Scene | null = null;
let camera: THREE.PerspectiveCamera | null = null;
let stageGroup: THREE.Group | null = null;
let avatarRoot: THREE.Group | null = null;
let loadedModel: THREE.Object3D | null = null;
let keyLight: THREE.DirectionalLight | null = null;
let fillLight: THREE.HemisphereLight | null = null;
let rimLight: THREE.PointLight | null = null;
let deskTop: THREE.Mesh | null = null;
let deskFront: THREE.Mesh | null = null;
let deskEdge: THREE.Mesh | null = null;
let backdropPanel: THREE.Mesh | null = null;
let animationFrameId: number | null = null;
let resizeObserver: ResizeObserver | null = null;
let reducedMotionQuery: MediaQueryList | null = null;
let modelLoadToken = 0;
let activeModelPath = "";
const accentColor = new THREE.Color();
const stageColor = new THREE.Color();
const hoverTarget = new THREE.Vector2(0, 0);
const smoothedLookOffset = new THREE.Vector2(0, 0);
const cameraBasePosition = new THREE.Vector3(0, 1.26, 3.92);
let isHoveringModel = false;

const supportsWebGL = () => {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(
      window.WebGLRenderingContext &&
        (canvas.getContext("webgl") || canvas.getContext("experimental-webgl")),
    );
  } catch {
    return false;
  }
};

const disposeMaterial = (material: THREE.Material) => {
  const materialRecord = material as THREE.Material & Record<string, unknown>;

  Object.values(materialRecord).forEach((value) => {
    if (value instanceof THREE.Texture) {
      value.dispose();
    }
  });

  material.dispose();
};

const disposeNode = (node: THREE.Object3D) => {
  node.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) {
      return;
    }

    child.geometry.dispose();
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    materials.forEach((material) => {
      disposeMaterial(material);
    });
  });
};

const applyStagePalette = () => {
  const currentPreset = preset.value;
  accentColor.set(currentPreset.accent);
  stageColor.set(currentPreset.stageTint);

  if (deskTop) {
    const material = deskTop.material as THREE.MeshStandardMaterial;
    material.color.copy(stageColor);
    material.emissive.copy(accentColor).multiplyScalar(0.04);
  }

  if (deskFront) {
    const material = deskFront.material as THREE.MeshStandardMaterial;
    material.color.copy(stageColor).multiplyScalar(0.92);
    material.emissive.copy(accentColor).multiplyScalar(0.03);
  }

  if (deskEdge) {
    const material = deskEdge.material as THREE.MeshStandardMaterial;
    material.color.copy(accentColor);
    material.emissive.copy(accentColor);
  }

  if (backdropPanel) {
    const material = backdropPanel.material as THREE.MeshBasicMaterial;
    material.color.copy(accentColor);
  }

  if (keyLight) {
    keyLight.color.copy(accentColor).lerp(new THREE.Color(0xffffff), 0.78);
  }

  if (rimLight) {
    rimLight.color.copy(accentColor);
  }
};

const applyModelTransform = () => {
  if (!avatarRoot) {
    return;
  }

  const currentPreset = preset.value;
  avatarRoot.position.set(
    currentPreset.modelPosition.x,
    currentPreset.modelPosition.y,
    currentPreset.modelPosition.z,
  );
  avatarRoot.rotation.set(0, currentPreset.modelRotationY, 0);
  avatarRoot.scale.setScalar(currentPreset.modelScale);
};

const resetHoverTracking = () => {
  isHoveringModel = false;
  hoverTarget.set(0, 0);
};

const applyModelMaterials = (model: THREE.Object3D) => {
  model.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) {
      return;
    }

    child.frustumCulled = false;
    child.castShadow = false;
    child.receiveShadow = false;

    const materials = Array.isArray(child.material) ? child.material : [child.material];
    materials.forEach((material) => {
      if (material instanceof THREE.MeshStandardMaterial) {
        material.envMapIntensity = 1.15;
        material.needsUpdate = true;
      }
    });
  });
};

const loadModel = async () => {
  if (!avatarRoot) {
    return;
  }

  const currentPreset = preset.value;
  if (loadedModel && activeModelPath === currentPreset.modelPath) {
    applyModelTransform();
    return;
  }

  const token = ++modelLoadToken;

  try {
    const gltf = await loader.loadAsync(currentPreset.modelPath);
    if (token !== modelLoadToken || !avatarRoot) {
      disposeNode(gltf.scene);
      return;
    }

    if (loadedModel) {
      avatarRoot.remove(loadedModel);
      disposeNode(loadedModel);
      loadedModel = null;
    }

    loadedModel = gltf.scene;
    activeModelPath = currentPreset.modelPath;
    applyModelMaterials(loadedModel);
    avatarRoot.add(loadedModel);
    applyModelTransform();
    resetHoverTracking();
  } catch (error) {
    console.error("加载面试官模型失败:", error);
    useFallback.value = true;
  }
};

const resizeRenderer = () => {
  if (!renderer || !camera || !stageEl.value) {
    return;
  }

  const { clientWidth, clientHeight } = stageEl.value;
  if (!clientWidth || !clientHeight) {
    return;
  }

  renderer.setSize(clientWidth, clientHeight, false);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  camera.aspect = clientWidth / clientHeight;
  camera.updateProjectionMatrix();
};

const handlePointerMove = (event: PointerEvent) => {
  if (!stageEl.value) {
    return;
  }

  const rect = stageEl.value.getBoundingClientRect();
  if (!rect.width || !rect.height) {
    return;
  }

  const offsetX = event.clientX - rect.left;
  const offsetY = event.clientY - rect.top;
  const normalizedX = (offsetX / rect.width) * 2 - 1;
  const normalizedY = -((offsetY / rect.height) * 2 - 1);

  isHoveringModel = true;
  hoverTarget.set(
    THREE.MathUtils.clamp(normalizedX, -0.95, 0.95),
    THREE.MathUtils.clamp(normalizedY, -0.8, 0.8),
  );
};

const handlePointerLeave = () => {
  resetHoverTracking();
};

const animate = (time: number) => {
  if (
    !renderer ||
    !scene ||
    !camera ||
    !avatarRoot ||
    !keyLight ||
    !fillLight ||
    !rimLight ||
    !deskEdge ||
    !backdropPanel
  ) {
    return;
  }

  animationFrameId = window.requestAnimationFrame(animate);
  const currentPreset = preset.value;
  const idlePhase = time * 0.00108;
  const idleMotionEnabled = props.mode === "idle";
  const idleBob = idleMotionEnabled ? Math.sin(idlePhase) * 0.022 : 0;
  const idleYaw = idleMotionEnabled ? Math.sin(idlePhase * 0.9) * 0.014 : 0;
  const idlePitch = idleMotionEnabled ? Math.cos(idlePhase * 1.14) * 0.01 : 0;
  const targetYaw = isHoveringModel ? hoverTarget.x * 0.54 : 0;
  const targetPitch = isHoveringModel ? -hoverTarget.y * 0.18 : 0;

  smoothedLookOffset.x = THREE.MathUtils.lerp(smoothedLookOffset.x, targetPitch, 0.2);
  smoothedLookOffset.y = THREE.MathUtils.lerp(smoothedLookOffset.y, targetYaw, 0.2);

  avatarRoot.position.set(
    currentPreset.modelPosition.x,
    currentPreset.modelPosition.y + idleBob,
    currentPreset.modelPosition.z,
  );
  avatarRoot.rotation.set(
    idlePitch + smoothedLookOffset.x,
    currentPreset.modelRotationY + idleYaw + smoothedLookOffset.y,
    0,
  );

  deskEdge.scale.set(1, 1, 1);
  backdropPanel.rotation.z = 0;
  backdropPanel.position.x = 0.24;
  const backdropMaterial = backdropPanel.material as THREE.MeshBasicMaterial;
  backdropMaterial.opacity = 0.12;

  keyLight.intensity = 2.34;
  fillLight.intensity = 1.2;
  rimLight.intensity = 1.32;

  camera.position.copy(cameraBasePosition);
  camera.lookAt(currentPreset.lookAt.x, currentPreset.lookAt.y, currentPreset.lookAt.z);

  renderer.render(scene, camera);
};

const initScene = async () => {
  if (!canvasEl.value || !stageEl.value) {
    return;
  }

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100);
  camera.position.copy(cameraBasePosition);

  renderer = new THREE.WebGLRenderer({
    canvas: canvasEl.value,
    antialias: true,
    alpha: true,
    powerPreference: "high-performance",
  });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.3;

  stageGroup = new THREE.Group();
  scene.add(stageGroup);

  avatarRoot = new THREE.Group();
  stageGroup.add(avatarRoot);

  fillLight = new THREE.HemisphereLight(0xffffff, 0x111827, 1.2);
  scene.add(fillLight);

  keyLight = new THREE.DirectionalLight(0xffffff, 2.38);
  keyLight.position.set(3.2, 4.2, 2.4);
  scene.add(keyLight);

  rimLight = new THREE.PointLight(0x93c5fd, 1.36, 8, 2);
  rimLight.position.set(-2.1, 2.2, -0.2);
  scene.add(rimLight);

  const deskMaterial = new THREE.MeshStandardMaterial({
    color: 0x132b40,
    emissive: 0x10253b,
    emissiveIntensity: 0.03,
    metalness: 0.2,
    roughness: 0.58,
  });
  deskTop = new THREE.Mesh(new THREE.BoxGeometry(3.8, 0.16, 1.34), deskMaterial);
  deskTop.position.set(0, -0.62, 0.96);
  deskTop.rotation.x = -0.06;
  stageGroup.add(deskTop);

  deskFront = new THREE.Mesh(
    new THREE.BoxGeometry(3.86, 0.68, 0.18),
    new THREE.MeshStandardMaterial({
      color: 0x10263a,
      emissive: 0x0d1b2b,
      emissiveIntensity: 0.02,
      metalness: 0.12,
      roughness: 0.72,
    }),
  );
  deskFront.position.set(0, -1.02, 1.48);
  stageGroup.add(deskFront);

  deskEdge = new THREE.Mesh(
    new THREE.BoxGeometry(2.34, 0.04, 0.08),
    new THREE.MeshStandardMaterial({
      color: 0x60a5fa,
      emissive: 0x60a5fa,
      emissiveIntensity: 0.48,
      metalness: 0.64,
      roughness: 0.18,
    }),
  );
  deskEdge.position.set(0, -0.54, 1.44);
  stageGroup.add(deskEdge);

  backdropPanel = new THREE.Mesh(
    new THREE.CircleGeometry(1.56, 48),
    new THREE.MeshBasicMaterial({
      color: 0x60a5fa,
      transparent: true,
      opacity: 0.14,
      depthWrite: false,
    }),
  );
  backdropPanel.position.set(0.24, 0.9, -1.18);
  backdropPanel.scale.set(1.08, 1.18, 1);
  scene.add(backdropPanel);

  applyStagePalette();
  resizeRenderer();

  if (typeof ResizeObserver !== "undefined" && stageEl.value) {
    resizeObserver = new ResizeObserver(() => {
      resizeRenderer();
    });
    resizeObserver.observe(stageEl.value);
  } else {
    window.addEventListener("resize", resizeRenderer);
  }

  await loadModel();
  animationFrameId = window.requestAnimationFrame(animate);
};

const teardownScene = () => {
  if (animationFrameId !== null) {
    window.cancelAnimationFrame(animationFrameId);
    animationFrameId = null;
  }
  modelLoadToken += 1;

  if (resizeObserver && stageEl.value) {
    resizeObserver.unobserve(stageEl.value);
    resizeObserver.disconnect();
    resizeObserver = null;
  } else {
    window.removeEventListener("resize", resizeRenderer);
  }

  if (loadedModel && avatarRoot) {
    avatarRoot.remove(loadedModel);
    disposeNode(loadedModel);
    loadedModel = null;
  }

  [deskTop, deskFront, deskEdge, backdropPanel].forEach((node) => {
    if (node) {
      disposeNode(node);
    }
  });

  deskTop = null;
  deskFront = null;
  deskEdge = null;
  backdropPanel = null;
  avatarRoot = null;
  resetHoverTracking();
  smoothedLookOffset.set(0, 0);

  if (renderer) {
    renderer.dispose();
    renderer.forceContextLoss();
    renderer = null;
  }

  scene = null;
  camera = null;
  stageGroup = null;
  keyLight = null;
  fillLight = null;
  rimLight = null;
  activeModelPath = "";
};

watch(
  () => props.role,
  async () => {
    if (useFallback.value) {
      return;
    }

    applyStagePalette();
    await loadModel();
  },
);

onMounted(async () => {
  reducedMotionQuery =
    typeof window.matchMedia === "function"
      ? window.matchMedia("(prefers-reduced-motion: reduce)")
      : null;
  useFallback.value = Boolean(reducedMotionQuery?.matches) || !supportsWebGL();

  if (useFallback.value) {
    return;
  }

  try {
    await initScene();
  } catch (error) {
    console.error("初始化 3D 面试官失败:", error);
    teardownScene();
    useFallback.value = true;
  }
});

onUnmounted(() => {
  teardownScene();
});
</script>

<template>
  <div
    ref="stageEl"
    class="relative h-full min-h-[19rem] overflow-hidden rounded-[2rem] border bg-slate-950 shadow-[0_28px_80px_rgba(2,6,23,0.68)] md:min-h-[21rem] lg:min-h-[23rem]"
    :style="stageBorderStyle"
    @pointermove="handlePointerMove"
    @pointerleave="handlePointerLeave"
  >
    <div class="absolute inset-0" :style="stageBackgroundStyle"></div>
    <div
      class="absolute inset-0 opacity-65"
      style="background: radial-gradient(circle at top, rgba(255, 255, 255, 0.1), transparent 38%)"
    ></div>

    <canvas v-if="!useFallback" ref="canvasEl" class="absolute inset-0 h-full w-full"></canvas>

    <div v-else class="absolute inset-0 flex items-center justify-center px-6">
      <div class="relative h-56 w-40 rounded-[2rem] border border-white/10 bg-slate-950/55">
        <div
          class="absolute top-8 left-1/2 h-20 w-20 -translate-x-1/2 rounded-full"
          :style="{ background: preset.accent }"
        ></div>
        <div
          class="absolute top-[6.5rem] left-1/2 h-28 w-24 -translate-x-1/2 rounded-[2rem]"
          :style="{ background: `${preset.accent}44` }"
        ></div>
      </div>
    </div>

    <div class="pointer-events-none relative z-10 flex h-full flex-col p-5 md:p-6">
      <div class="max-w-[17rem]">
        <h2 class="text-2xl font-semibold text-white md:text-[2rem]">
          {{ preset.label }}
        </h2>
      </div>
    </div>
  </div>
</template>
