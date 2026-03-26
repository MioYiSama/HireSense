import { ResumeAnalysisLabel } from "@/api";
import type { ResumeAnalysis, ResumeAnalysisBlock, ResumeAnalysisHighlightPhrase } from "@/api";

export type ResumeTextSegment = {
  text: string;
  label: ResumeAnalysisLabel | null;
  comment?: string;
};

const labelPriority: Record<ResumeAnalysisLabel, number> = {
  [ResumeAnalysisLabel.Risk]: 4,
  [ResumeAnalysisLabel.Probe]: 3,
  [ResumeAnalysisLabel.Strength]: 2,
  [ResumeAnalysisLabel.Neutral]: 1,
};

const tonePhraseMap: Record<string, string> = {
  "data-driven": "数据导向",
  "impact-driven": "结果导向",
  "results-driven": "结果导向",
  "well-structured": "结构清晰",
  "high-risk": "高风险",
  "low-signal": "信息密度偏低",
};

const toneWordMap: Record<string, string> = {
  aggressive: "进攻性强",
  assertive: "表达强势",
  balanced: "较为均衡",
  cautious: "偏保守",
  clear: "表达清晰",
  concise: "表达简洁",
  confident: "表达自信",
  credible: "可信度较高",
  direct: "表达直接",
  focused: "重点明确",
  generic: "辨识度不足",
  inflated: "表述夸张",
  inconsistent: "前后不一",
  passive: "表达被动",
  polished: "表达成熟",
  pragmatic: "务实",
  promising: "有潜力",
  scattered: "重点分散",
  sharp: "表达直接",
  solid: "较为扎实",
  strong: "竞争力较强",
  structured: "结构清晰",
  technical: "技术导向",
  thin: "内容偏薄",
  underwhelming: "说服力不足",
  vague: "表述模糊",
  weak: "偏弱",
};

function normalizeToneSegment(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[()]/g, " ")
    .replace(/\s+/g, " ")
    .replace(/^[^a-z]+|[^a-z-]+$/g, "");
}

export function buildHighlightedSegments(block: ResumeAnalysisBlock): ResumeTextSegment[] {
  const text = block.text ?? "";
  const phrases = (block.highlight_phrases ?? [])
    .map((phrase) => {
      const phraseText = phrase.text?.trim() ?? "";
      if (!phraseText) {
        return null;
      }

      const index = text.indexOf(phraseText);
      if (index < 0) {
        return null;
      }

      return {
        index,
        length: phraseText.length,
        phrase,
      };
    })
    .filter(
      (item): item is { index: number; length: number; phrase: ResumeAnalysisHighlightPhrase } => {
        return Boolean(item);
      },
    )
    .sort((left, right) => {
      if (left.index !== right.index) {
        return left.index - right.index;
      }

      const leftPriority = labelPriority[left.phrase.label];
      const rightPriority = labelPriority[right.phrase.label];
      if (leftPriority !== rightPriority) {
        return rightPriority - leftPriority;
      }

      return right.length - left.length;
    });

  const segments: ResumeTextSegment[] = [];
  let cursor = 0;

  phrases.forEach((item) => {
    if (item.index < cursor) {
      return;
    }

    if (item.index > cursor) {
      segments.push({
        text: text.slice(cursor, item.index),
        label: null,
      });
    }

    segments.push({
      text: text.slice(item.index, item.index + item.length),
      label: item.phrase.label,
      comment: item.phrase.comment,
    });
    cursor = item.index + item.length;
  });

  if (cursor < text.length) {
    segments.push({
      text: text.slice(cursor),
      label: null,
    });
  }

  if (segments.length === 0) {
    return [{ text, label: null }];
  }

  return segments;
}

export function countBlocksByLabel(analysis: ResumeAnalysis) {
  return analysis.blocks.reduce(
    (totals, block) => {
      const label = block.label;
      if (label === ResumeAnalysisLabel.Strength) {
        totals.strength += 1;
      } else if (label === ResumeAnalysisLabel.Probe) {
        totals.probe += 1;
      } else if (label === ResumeAnalysisLabel.Risk) {
        totals.risk += 1;
      } else {
        totals.neutral += 1;
      }

      return totals;
    },
    {
      strength: 0,
      probe: 0,
      risk: 0,
      neutral: 0,
    },
  );
}

export function formatResumeAnalysisTone(value?: string | null) {
  if (!value?.trim()) {
    return "综合评估";
  }

  const translated = value
    .split(/[,\u3001/;&]+/)
    .flatMap((segment) => {
      const normalized = normalizeToneSegment(segment);
      if (!normalized) {
        return [];
      }

      const exactMatch = tonePhraseMap[normalized];
      if (exactMatch) {
        return [exactMatch];
      }

      return normalized
        .split(/[\s-]+/)
        .map((token) => toneWordMap[token])
        .filter((item): item is string => Boolean(item));
    })
    .filter((item, index, list) => list.indexOf(item) === index);

  if (translated.length === 0) {
    return "综合评估";
  }

  return translated.slice(0, 2).join(" / ");
}

export function formatResumeAnalysisTime(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "时间未知";
  }

  return parsed.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
