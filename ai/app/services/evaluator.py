import math
import re
from typing import Dict, List, Tuple

import numpy as np


class Evaluator:
    def __init__(self, sts_model, nli_model):
        self.sts_model = sts_model
        self.nli_model = nli_model

    def _parse_nli_logits(self, logits: np.ndarray) -> Dict[str, float]:
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)
        return {
            "Entailment": float(probs[0]),
            "Neutral": float(probs[1]),
            "Contradiction": float(probs[2]),
        }

    @staticmethod
    def _empty_result() -> Dict[str, object]:
        return {
            "mastery_score": 0.0,
            "coverage_raw": 0.0,
            "coverage_score": 0.0,
            "consistency_score": 0.0,
            "completeness_score": 0.0,
            "logic_status": "Neutral",
            "nli_probs": {"Entailment": 0.0, "Neutral": 1.0, "Contradiction": 0.0},
            "missing_points": [],
            "reason_tags": ["回答过短"],
        }

    @staticmethod
    def _extract_keypoints(text: str) -> List[str]:
        parts = re.split(r"[，。；;、\n]+", text or "")
        keypoints: List[str] = []
        for part in parts:
            normalized = part.strip()
            if len(normalized) < 4:
                continue
            if normalized not in keypoints:
                keypoints.append(normalized)
        return keypoints[:6]

    @staticmethod
    def _extract_tokens(text: str) -> List[str]:
        raw_tokens = re.findall(r"[A-Za-z0-9_+#./-]+|[\u4e00-\u9fff]+", text or "")
        tokens: List[str] = []
        for token in raw_tokens:
            normalized = token.strip().lower()
            if len(normalized) < 2:
                continue
            tokens.append(normalized)
        return tokens

    def _compute_completeness(
        self, user_answer: str, standard_answer: str, coverage_ratio: float
    ) -> Tuple[float, List[str], float]:
        keypoints = self._extract_keypoints(standard_answer)
        if not keypoints:
            return min(1.0, max(0.25, coverage_ratio)), [], 1.0

        user_text = (user_answer or "").lower()
        hit_count = 0
        missing_points: List[str] = []

        for point in keypoints:
            point_tokens = self._extract_tokens(point)
            if not point_tokens:
                continue

            matched = sum(1 for token in point_tokens if token in user_text)
            ratio = matched / len(point_tokens)
            if point.lower() in user_text or ratio >= 0.4:
                hit_count += 1
            else:
                missing_points.append(point)

        keypoint_ratio = hit_count / len(keypoints)
        normalized_len = min(len((user_answer or "").strip()) / 120, 1.0)
        completeness = min(1.0, 0.65 * keypoint_ratio + 0.25 * coverage_ratio + 0.10 * normalized_len)
        return completeness, missing_points[:4], keypoint_ratio

    @staticmethod
    def _build_reason_tags(
        coverage_score: float,
        consistency_score: float,
        completeness_score: float,
        logic_status: str,
        missing_points: List[str],
    ) -> List[str]:
        tags: List[str] = []

        if coverage_score >= 75:
            tags.append("核心方向基本对齐")
        elif coverage_score < 40:
            tags.append("与标答覆盖偏低")

        if logic_status == "Contradiction" or consistency_score < 45:
            tags.append("存在逻辑冲突")
        elif logic_status == "Neutral":
            tags.append("回答偏概念化")
        else:
            tags.append("逻辑基本自洽")

        if completeness_score >= 75:
            tags.append("回答较完整")
        elif missing_points:
            tags.append("关键点覆盖不足")
        else:
            tags.append("细节深度不足")

        return tags

    def evaluate_mastery(self, user_answer: str, standard_answer: str) -> Dict[str, object]:
        if not user_answer or len(user_answer.strip()) < 2:
            return self._empty_result()

        sts_logits = self.sts_model.predict([[standard_answer, user_answer]])[0]
        coverage_ratio = 1 / (1 + math.exp(-sts_logits))
        coverage_score = round(coverage_ratio * 100, 2)

        nli_logits = self.nli_model.predict([[user_answer, standard_answer]])[0]
        nli_probs = self._parse_nli_logits(nli_logits)
        logic_status = max(nli_probs, key=nli_probs.get)

        consistency_ratio = (
            nli_probs["Entailment"] * 1.0
            + nli_probs["Neutral"] * 0.7
            + nli_probs["Contradiction"] * 0.25
        )
        consistency_score = round(consistency_ratio * 100, 2)

        completeness_ratio, missing_points, keypoint_ratio = self._compute_completeness(
            user_answer=user_answer,
            standard_answer=standard_answer,
            coverage_ratio=coverage_ratio,
        )
        completeness_score = round(completeness_ratio * 100, 2)

        mastery_ratio = (
            coverage_ratio * 0.5
            + consistency_ratio * 0.3
            + completeness_ratio * 0.2
        )
        mastery_score = round(max(0.0, min(1.0, mastery_ratio)) * 100, 2)

        if logic_status == "Contradiction" and mastery_score > 55:
            mastery_score = 55.0

        if coverage_score < 25 and keypoint_ratio == 0:
            missing_points = self._extract_keypoints(standard_answer)[:4]

        reason_tags = self._build_reason_tags(
            coverage_score=coverage_score,
            consistency_score=consistency_score,
            completeness_score=completeness_score,
            logic_status=logic_status,
            missing_points=missing_points,
        )

        return {
            "mastery_score": mastery_score,
            "coverage_raw": coverage_score,
            "coverage_score": coverage_score,
            "consistency_score": consistency_score,
            "completeness_score": completeness_score,
            "logic_status": logic_status,
            "nli_probs": nli_probs,
            "missing_points": missing_points,
            "reason_tags": reason_tags,
        }


class PruningStrategy:
    @staticmethod
    def calculate_quota(mastery_score: float, logic_status: str) -> Tuple[int, int, int]:
        if logic_status == "Contradiction":
            return 0, 1, 3

        if mastery_score >= 80:
            return 3, 1, 0
        if mastery_score < 35:
            return 0, 1, 3
        return 1, 2, 1
