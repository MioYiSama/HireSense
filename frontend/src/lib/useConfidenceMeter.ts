import { readonly, ref } from "vue";

const ANALYSIS_WINDOW_MS = 4500;
const RECOVERY_WINDOW_MS = 900;
const RHYTHM_WINDOW_MS = 1800;
const PAUSE_WINDOW_MS = 2200;
const BASELINE_WINDOW_MS = 400;
const SAMPLE_INTERVAL_MS = 50;
const FREEZE_DURATION_MS = 1200;
const ACTIVE_MIN_SCORE = 6;
const MAX_SCORE = 98;
const IDLE_SCORE = 58;
const RMS_FLOOR = 0.018;
const DISPLAY_FOLLOW_FACTOR = 0.18;
const MIN_SAMPLES_BEFORE_SCORING = 8;
const TREND_POINTS = 24;
const SCORE_DEBOUNCE_MS = 220;
const SCORE_COMMIT_TOLERANCE = 4;
const SCORE_FAST_PATH_DELTA = 18;

export type ConfidenceZone = "red" | "amber" | "green";

export type ConfidenceCue = "paused" | "recovering" | "steady" | null;

interface ConfidenceMetrics {
  speechRatio: number;
  stability: number;
  pauseLoad: number;
}

export interface ConfidenceSnapshot {
  score: number;
  displayScore: number;
  zone: ConfidenceZone;
  label: string;
  trend: number[];
  metrics: ConfidenceMetrics;
  cue: ConfidenceCue;
  active: boolean;
  visible: boolean;
}

interface AudioSample {
  at: number;
  rms: number;
  speaking: boolean;
}

interface ScoreSample {
  at: number;
  score: number;
}

interface Segment {
  speaking: boolean;
  duration: number;
}

type AudioContextCtor = typeof AudioContext;

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const average = (values: number[]) =>
  values.length === 0 ? 0 : values.reduce((sum, value) => sum + value, 0) / values.length;

const standardDeviation = (values: number[]) => {
  if (values.length === 0) {
    return 0;
  }

  const mean = average(values);
  const variance = average(values.map((value) => (value - mean) ** 2));
  return Math.sqrt(variance);
};

const createInitialSnapshot = (): ConfidenceSnapshot => ({
  score: IDLE_SCORE,
  displayScore: IDLE_SCORE,
  zone: "amber",
  label: "正在进入状态",
  trend: Array.from({ length: TREND_POINTS }, () => IDLE_SCORE),
  metrics: {
    speechRatio: 0.52,
    stability: 0.62,
    pauseLoad: 0.18,
  },
  cue: null,
  active: false,
  visible: false,
});

const getZone = (score: number): ConfidenceZone => {
  if (score < 42) {
    return "red";
  }

  if (score < 70) {
    return "amber";
  }

  return "green";
};

const getLabel = (zone: ConfidenceZone) => {
  if (zone === "red") {
    return "需要稳住节奏";
  }

  if (zone === "amber") {
    return "正在进入状态";
  }

  return "表达流畅";
};

const getAudioContextCtor = (): AudioContextCtor | undefined => {
  if (typeof window === "undefined") {
    return undefined;
  }

  const browserWindow = window as Window & typeof globalThis & { webkitAudioContext?: AudioContextCtor };
  return browserWindow.AudioContext ?? browserWindow.webkitAudioContext;
};

const computeRms = (buffer: Uint8Array) => {
  let sumSquares = 0;

  for (let index = 0; index < buffer.length; index++) {
    const sample = ((buffer[index] ?? 128) - 128) / 128;
    sumSquares += sample * sample;
  }

  return Math.sqrt(sumSquares / buffer.length);
};

const buildSegments = (samples: AudioSample[]) => {
  const segments: Segment[] = [];

  for (const sample of samples) {
    const lastSegment = segments.at(-1);

    if (lastSegment && lastSegment.speaking === sample.speaking) {
      lastSegment.duration += SAMPLE_INTERVAL_MS;
      continue;
    }

    segments.push({
      speaking: sample.speaking,
      duration: SAMPLE_INTERVAL_MS,
    });
  }

  return segments;
};

const buildTrend = (scores: ScoreSample[]) => {
  const recentScores = scores.slice(-TREND_POINTS).map((entry) => Math.round(entry.score));
  const paddedTrend = Array.from({ length: TREND_POINTS - recentScores.length }, () => IDLE_SCORE);

  return [...paddedTrend, ...recentScores];
};

const calculateSpeechStats = (samples: AudioSample[]) => {
  if (samples.length === 0) {
    return {
      ratio: 0,
      stability: 0,
    };
  }

  const speechSamples = samples.filter((entry) => entry.speaking);
  const speechRatio = clamp(speechSamples.length / samples.length, 0, 1);
  const speechLevels = speechSamples.map((entry) => entry.rms);
  const speechMean = average(speechLevels);
  const stability = speechLevels.length === 0
    ? 0
    : clamp(1 - standardDeviation(speechLevels) / (speechMean + 0.001), 0, 1);

  return {
    ratio: speechRatio,
    stability,
  };
};

export const useConfidenceMeter = () => {
  const snapshot = ref<ConfidenceSnapshot>(createInitialSnapshot());
  const supported = ref(Boolean(getAudioContextCtor()));

  let audioContext: AudioContext | null = null;
  let analyserNode: AnalyserNode | null = null;
  let sourceNode: MediaStreamAudioSourceNode | null = null;
  let timeDomainBuffer: Uint8Array<ArrayBuffer> | null = null;
  let frameHandle: number | null = null;
  let hideTimeout: number | null = null;
  let sessionStartedAt = 0;
  let lastAggregateAt = 0;
  let smoothedRms = 0;
  let noiseFloor = 0.01;
  let baselineSamples: number[] = [];
  let audioSamples: AudioSample[] = [];
  let scoreSamples: ScoreSample[] = [];
  let trendSamples: ScoreSample[] = [];
  let committedScore = IDLE_SCORE;
  let pendingScore = IDLE_SCORE;
  let pendingScoreStartedAt = 0;

  const clearHideTimeout = () => {
    if (hideTimeout !== null) {
      window.clearTimeout(hideTimeout);
      hideTimeout = null;
    }
  };

  const resetSession = () => {
    sessionStartedAt = 0;
    lastAggregateAt = 0;
    smoothedRms = 0;
    noiseFloor = 0.01;
    baselineSamples = [];
    audioSamples = [];
    scoreSamples = [];
    trendSamples = [];
    committedScore = IDLE_SCORE;
    pendingScore = IDLE_SCORE;
    pendingScoreStartedAt = 0;
  };

  const stopLoop = () => {
    if (frameHandle !== null) {
      window.cancelAnimationFrame(frameHandle);
      frameHandle = null;
    }
  };

  const teardownAudioGraph = () => {
    stopLoop();

    if (sourceNode) {
      sourceNode.disconnect();
      sourceNode = null;
    }

    if (analyserNode) {
      analyserNode.disconnect();
      analyserNode = null;
    }

    if (audioContext) {
      void audioContext.close().catch(() => undefined);
      audioContext = null;
    }

    timeDomainBuffer = null;
    resetSession();
  };

  const applyIdleSnapshot = () => {
    snapshot.value = createInitialSnapshot();
  };

  const computeRecovery = (now: number) => {
    const recentScores = scoreSamples
      .filter((entry) => now - entry.at <= RECOVERY_WINDOW_MS)
      .map((entry) => entry.score);
    const previousScores = scoreSamples
      .filter((entry) => {
        const age = now - entry.at;
        return age > RECOVERY_WINDOW_MS && age <= RECOVERY_WINDOW_MS * 2;
      })
      .map((entry) => entry.score);

    if (recentScores.length === 0 || previousScores.length === 0) {
      return 0;
    }

    return clamp((average(recentScores) - average(previousScores)) / 8, 0, 1);
  };

  const debounceScore = (rawScore: number, now: number) => {
    const deltaFromCommitted = Math.abs(rawScore - committedScore);
    const deltaFromPending = Math.abs(rawScore - pendingScore);

    if (deltaFromCommitted <= SCORE_COMMIT_TOLERANCE) {
      committedScore += (rawScore - committedScore) * 0.28;
      pendingScore = committedScore;
      pendingScoreStartedAt = now;
      return committedScore;
    }

    if (rawScore <= 18 || deltaFromCommitted >= SCORE_FAST_PATH_DELTA) {
      committedScore += (rawScore - committedScore) * 0.42;
      pendingScore = committedScore;
      pendingScoreStartedAt = now;
      return committedScore;
    }

    if (deltaFromPending > SCORE_COMMIT_TOLERANCE) {
      pendingScore = rawScore;
      pendingScoreStartedAt = now;
      return committedScore;
    }

    if (now - pendingScoreStartedAt >= SCORE_DEBOUNCE_MS) {
      committedScore += (pendingScore - committedScore) * 0.6;
      pendingScoreStartedAt = now;
    }

    return committedScore;
  };

  const updateSnapshot = (now: number) => {
    const recentSamples = audioSamples.filter((entry) => now - entry.at <= ANALYSIS_WINDOW_MS);
    audioSamples = recentSamples;

    if (recentSamples.length < MIN_SAMPLES_BEFORE_SCORING) {
      snapshot.value = {
        ...snapshot.value,
        active: true,
        visible: true,
        cue: null,
        label: "正在进入状态",
        zone: "amber",
        trend: buildTrend(trendSamples),
      };
      return;
    }

    const rhythmSamples = recentSamples.filter((entry) => now - entry.at <= RHYTHM_WINDOW_MS);
    const pauseSamples = recentSamples.filter((entry) => now - entry.at <= PAUSE_WINDOW_MS);
    const overallStats = calculateSpeechStats(recentSamples);
    const recentStats = calculateSpeechStats(rhythmSamples);
    const speechRatio = clamp(overallStats.ratio * 0.35 + recentStats.ratio * 0.65, 0, 1);
    const stability = clamp(
      overallStats.stability * 0.4 + recentStats.stability * 0.6,
      0,
      1,
    );
    const segments = buildSegments(pauseSamples);

    let pauseCount = 0;
    let longPauseCount = 0;
    let burstCount = 0;
    let seenSpeech = false;

    for (let index = 0; index < segments.length; index++) {
      const segment = segments[index];

      if (!segment) {
        continue;
      }

      if (segment.speaking) {
        seenSpeech = true;
        const previousSegment = segments[index - 1];
        const nextSegment = segments[index + 1];

        if (
          segment.duration >= 90 &&
          segment.duration <= 260 &&
          previousSegment &&
          nextSegment &&
          !previousSegment.speaking &&
          !nextSegment.speaking &&
          previousSegment.duration < 220 &&
          nextSegment.duration < 220
        ) {
          burstCount++;
        }

        continue;
      }

      if (!seenSpeech) {
        continue;
      }

      if (segment.duration >= 180) {
        pauseCount++;
      }

      if (segment.duration >= 650) {
        longPauseCount++;
      }
    }

    const pauseLoad = clamp(
      pauseCount * 0.18 + longPauseCount * 0.34 + burstCount * 0.22,
      0,
      1,
    );
    const trailingSilenceDuration = segments.at(-1)?.speaking ? 0 : (segments.at(-1)?.duration ?? 0);
    const recentLift = clamp(
      (recentStats.ratio - overallStats.ratio) * 0.9 +
        (recentStats.stability - overallStats.stability) * 0.7,
      -0.35,
      0.5,
    );
    let provisionalScore = clamp(
      48 + 24 * speechRatio + 16 * stability + 12 * recentLift - 18 * pauseLoad,
      ACTIVE_MIN_SCORE,
      MAX_SCORE,
    );

    if (recentStats.ratio < 0.03 && overallStats.ratio < 0.06 && trailingSilenceDuration >= 900) {
      provisionalScore = clamp(
        6 + overallStats.ratio * 140 + recentStats.stability * 6,
        ACTIVE_MIN_SCORE,
        18,
      );
    } else if (
      recentStats.ratio < 0.08 &&
      overallStats.ratio < 0.16 &&
      trailingSilenceDuration >= 500
    ) {
      provisionalScore = Math.min(
        provisionalScore,
        clamp(
          14 +
            overallStats.ratio * 110 +
            recentStats.ratio * 80 +
            recentStats.stability * 6,
          ACTIVE_MIN_SCORE,
          34,
        ),
      );
    }

    scoreSamples.push({
      at: now,
      score: provisionalScore,
    });
    scoreSamples = scoreSamples.filter((entry) => now - entry.at <= ANALYSIS_WINDOW_MS);

    const recovery = computeRecovery(now);
    const rawTargetScore = clamp(provisionalScore + 18 * recovery, ACTIVE_MIN_SCORE, MAX_SCORE);
    const targetScore = debounceScore(rawTargetScore, now);
    trendSamples.push({
      at: now,
      score: targetScore,
    });
    trendSamples = trendSamples.filter((entry) => now - entry.at <= ANALYSIS_WINDOW_MS);

    const zone = getZone(targetScore);
    const lastSegment = segments.at(-1);
    let cue: ConfidenceCue = null;

    if (lastSegment && !lastSegment.speaking && lastSegment.duration >= 350 && speechRatio > 0.15) {
      cue = "paused";
    } else if (recovery > 0.35 && targetScore >= 52) {
      cue = "recovering";
    } else if (speechRatio > 0.42 && stability > 0.5) {
      cue = "steady";
    }

    const followFactor =
      targetScore > snapshot.value.displayScore
        ? 0.34
        : targetScore <= 18
          ? 0.28
          : DISPLAY_FOLLOW_FACTOR;
    const displayScore =
      snapshot.value.displayScore + (targetScore - snapshot.value.displayScore) * followFactor;

    snapshot.value = {
      score: Math.round(targetScore),
      displayScore,
      zone,
      label: getLabel(zone),
      trend: buildTrend(trendSamples),
      metrics: {
        speechRatio,
        stability,
        pauseLoad,
      },
      cue,
      active: true,
      visible: true,
    };
  };

  const runAnalysisFrame = () => {
    if (!analyserNode || !timeDomainBuffer) {
      return;
    }

    const now = performance.now();
    analyserNode.getByteTimeDomainData(timeDomainBuffer);

    const rms = computeRms(timeDomainBuffer);
    smoothedRms = smoothedRms === 0 ? rms : smoothedRms * 0.55 + rms * 0.45;

    if (lastAggregateAt === 0 || now - lastAggregateAt >= SAMPLE_INTERVAL_MS) {
      const sessionAge = now - sessionStartedAt;

      if (sessionAge <= BASELINE_WINDOW_MS) {
        baselineSamples.push(smoothedRms);
        noiseFloor = Math.max(average(baselineSamples), 0.005);
      }

      const speakingThreshold = Math.max(RMS_FLOOR, noiseFloor * 1.8);
      const speaking = sessionAge > BASELINE_WINDOW_MS && smoothedRms >= speakingThreshold;

      if (!speaking && sessionAge > BASELINE_WINDOW_MS) {
        noiseFloor = noiseFloor * 0.985 + smoothedRms * 0.015;
      }

      audioSamples.push({
        at: now,
        rms: smoothedRms,
        speaking,
      });
      lastAggregateAt = now;
      updateSnapshot(now);
    }

    frameHandle = window.requestAnimationFrame(runAnalysisFrame);
  };

  const start = async (stream: MediaStream) => {
    clearHideTimeout();
    teardownAudioGraph();

    const AudioContextClass = getAudioContextCtor();

    if (!AudioContextClass) {
      supported.value = false;
      applyIdleSnapshot();
      return;
    }

    supported.value = true;
    snapshot.value = {
      ...createInitialSnapshot(),
      active: true,
      visible: true,
    };

    audioContext = new AudioContextClass();
    sourceNode = audioContext.createMediaStreamSource(stream);
    analyserNode = audioContext.createAnalyser();
    analyserNode.fftSize = 2048;
    analyserNode.smoothingTimeConstant = 0.82;
    sourceNode.connect(analyserNode);
    timeDomainBuffer = new Uint8Array(new ArrayBuffer(analyserNode.fftSize));

    if (audioContext.state === "suspended") {
      await audioContext.resume();
    }

    resetSession();
    sessionStartedAt = performance.now();
    lastAggregateAt = 0;
    frameHandle = window.requestAnimationFrame(runAnalysisFrame);
  };

  const freezeAndHide = () => {
    clearHideTimeout();
    teardownAudioGraph();
    snapshot.value = {
      ...snapshot.value,
      active: false,
      visible: true,
      cue: null,
    };

    hideTimeout = window.setTimeout(() => {
      applyIdleSnapshot();
    }, FREEZE_DURATION_MS);
  };

  const cancelAndHide = () => {
    clearHideTimeout();
    teardownAudioGraph();
    applyIdleSnapshot();
  };

  const reset = () => {
    clearHideTimeout();
    teardownAudioGraph();
    applyIdleSnapshot();
  };

  return {
    supported: readonly(supported),
    snapshot: readonly(snapshot),
    start,
    freezeAndHide,
    cancelAndHide,
    reset,
  };
};
