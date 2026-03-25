import json
import math
import re
from typing import Any, Dict, List, Literal, Optional, Tuple, Type

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class ScoreJudgement(BaseModel):
    coverage_score: float = Field(description="回答对标准答案主线的覆盖度，0-100")
    consistency_score: float = Field(description="回答内部与标准答案的一致性，0-100")
    completeness_score: float = Field(description="回答对关键点与边界条件的完整度，0-100")
    logic_status: Literal["Entailment", "Neutral", "Contradiction"] = Field(
        description="回答与标准答案的逻辑关系"
    )
    reason_tags: List[str] = Field(default_factory=list, description="支撑分数的简洁标签")
    strength_points: List[str] = Field(default_factory=list, description="答到的关键点")
    missing_points: List[str] = Field(default_factory=list, description="缺失的关键点")
    score_rationale: str = Field(description="一句话解释该分数")


class Evaluator:
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm

    @staticmethod
    def _clamp_score(value: Any, default: float = 0.0) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = default
        return round(max(0.0, min(numeric, 100.0)), 2)

    @staticmethod
    def _normalize_points(points: Optional[List[str]], limit: int) -> List[str]:
        normalized: List[str] = []
        for point in points or []:
            text = str(point or "").strip()
            if not text or text in normalized:
                continue
            normalized.append(text)
            if len(normalized) >= limit:
                break
        return normalized

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
    ) -> Tuple[float, List[str], List[str], float]:
        keypoints = self._extract_keypoints(standard_answer)
        if not keypoints:
            return min(1.0, max(0.25, coverage_ratio)), [], [], 1.0

        user_text = (user_answer or "").lower()
        hit_count = 0
        missing_points: List[str] = []
        strength_points: List[str] = []

        for point in keypoints:
            point_tokens = self._extract_tokens(point)
            if not point_tokens:
                continue

            matched = sum(1 for token in point_tokens if token in user_text)
            ratio = matched / len(point_tokens)
            if point.lower() in user_text or ratio >= 0.4:
                hit_count += 1
                strength_points.append(point)
            else:
                missing_points.append(point)

        keypoint_ratio = hit_count / len(keypoints)
        normalized_len = min(len((user_answer or "").strip()) / 120, 1.0)
        completeness = min(
            1.0, 0.65 * keypoint_ratio + 0.25 * coverage_ratio + 0.10 * normalized_len
        )
        return completeness, missing_points[:4], strength_points[:3], keypoint_ratio

    @staticmethod
    def _build_reason_tags(
        coverage_score: float,
        consistency_score: float,
        completeness_score: float,
        logic_status: str,
        missing_points: List[str],
        provided_tags: Optional[List[str]] = None,
    ) -> List[str]:
        tags: List[str] = []
        for tag in provided_tags or []:
            normalized = str(tag or "").strip()
            if normalized and normalized not in tags:
                tags.append(normalized)

        if coverage_score >= 75 and "核心方向基本对齐" not in tags:
            tags.append("核心方向基本对齐")
        elif coverage_score < 40 and "与标答覆盖偏低" not in tags:
            tags.append("与标答覆盖偏低")

        if (
            logic_status == "Contradiction" or consistency_score < 45
        ) and "存在逻辑冲突" not in tags:
            tags.append("存在逻辑冲突")
        elif logic_status == "Neutral" and "回答偏概念化" not in tags:
            tags.append("回答偏概念化")
        elif logic_status == "Entailment" and "逻辑基本自洽" not in tags:
            tags.append("逻辑基本自洽")

        if completeness_score >= 75 and "回答较完整" not in tags:
            tags.append("回答较完整")
        elif missing_points and "关键点覆盖不足" not in tags:
            tags.append("关键点覆盖不足")
        elif "细节深度不足" not in tags:
            tags.append("细节深度不足")

        return tags[:4]

    @staticmethod
    def _build_logic_probs(logic_status: str, consistency_score: float) -> Dict[str, float]:
        dominant = max(0.55, min(0.92, 0.45 + consistency_score / 200))
        remainder = 1.0 - dominant

        if logic_status == "Entailment":
            probs = {
                "Entailment": dominant,
                "Neutral": remainder * 0.65,
                "Contradiction": remainder * 0.35,
            }
        elif logic_status == "Contradiction":
            probs = {
                "Entailment": remainder * 0.20,
                "Neutral": remainder * 0.80,
                "Contradiction": dominant,
            }
        else:
            probs = {
                "Entailment": remainder * 0.5,
                "Neutral": dominant,
                "Contradiction": remainder * 0.5,
            }

        return {name: round(value, 4) for name, value in probs.items()}

    @staticmethod
    def _build_default_rationale(
        mastery_score: float,
        coverage_score: float,
        consistency_score: float,
        completeness_score: float,
        logic_status: str,
        missing_points: List[str],
        strength_points: List[str],
    ) -> str:
        if logic_status == "Contradiction" or consistency_score < 45:
            return "回答存在明显冲突，虽然触及部分概念，但论证无法支撑高分。"
        if mastery_score >= 75 and completeness_score >= 70:
            return "回答覆盖主线较完整，逻辑基本自洽，主要得分点比较明确。"
        if coverage_score < 40:
            return "回答与考点主线偏离较多，关键点覆盖不足，因此分数偏低。"
        if missing_points:
            return f"回答触及主线，但{missing_points[0]}等关键点没有展开，限制了最终得分。"
        if strength_points:
            return f"回答答到了{strength_points[0]}等主线内容，但细节与边界条件仍可继续补强。"
        return "回答有一定相关性，但结构化程度和完整度一般，最终得分居中。"

    @staticmethod
    def _validate_model_payload(
        model_class: Type[BaseModel], payload: Dict[str, Any]
    ) -> BaseModel:
        if hasattr(model_class, "model_validate"):
            return model_class.model_validate(payload)
        return model_class.parse_obj(payload)

    def _extract_json_objects(self, text: str) -> List[str]:
        objects: List[str] = []
        start = None
        depth = 0
        in_string = False
        escape = False

        for index, char in enumerate(text):
            if start is None:
                if char == "{":
                    start = index
                    depth = 1
                    in_string = False
                    escape = False
                continue

            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    objects.append(text[start : index + 1])
                    start = None

        return objects

    def _recover_structured_generation(
        self, raw_message: Any, model_class: Type[BaseModel]
    ) -> Optional[BaseModel]:
        if raw_message is None:
            return None

        candidate_texts: List[str] = []
        if isinstance(raw_message, dict):
            tool_calls = raw_message.get("tool_calls") or []
            content = raw_message.get("content")
        else:
            additional_kwargs = getattr(raw_message, "additional_kwargs", {}) or {}
            tool_calls = additional_kwargs.get("tool_calls") or []
            content = getattr(raw_message, "content", None)

        for tool_call in tool_calls:
            function_info = tool_call.get("function") or {}
            arguments = function_info.get("arguments")
            if isinstance(arguments, str) and arguments.strip():
                candidate_texts.append(arguments)

        if isinstance(content, str) and content.strip():
            candidate_texts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text")
                    if isinstance(text, str) and text.strip():
                        candidate_texts.append(text)

        for candidate_text in candidate_texts:
            try:
                return self._validate_model_payload(model_class, json.loads(candidate_text))
            except Exception:
                pass

            for json_blob in self._extract_json_objects(candidate_text):
                try:
                    return self._validate_model_payload(model_class, json.loads(json_blob))
                except Exception:
                    continue

        return None

    def _retry_structured_generation(
        self,
        prompt_template: ChatPromptTemplate,
        input_data: Dict[str, Any],
        model_class: Type[BaseModel],
        max_retries: int = 3,
    ) -> BaseModel:
        if self.llm is None:
            raise RuntimeError("LLM judge is not configured")

        last_error: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                structured_llm = self.llm.with_structured_output(
                    model_class, include_raw=True
                )
                result = (prompt_template | structured_llm).invoke(input_data)
                parsed = result.get("parsed")
                if parsed is not None:
                    return parsed

                recovered = self._recover_structured_generation(
                    raw_message=result.get("raw"),
                    model_class=model_class,
                )
                if recovered is not None:
                    return recovered

                parsing_error = result.get("parsing_error")
                if parsing_error is not None:
                    raise parsing_error
                raise ValueError(
                    f"{model_class.__name__} structured generation returned no parsed result."
                )
            except Exception as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    continue
                raise last_error

        raise RuntimeError("structured generation retry exhausted")

    def _fallback_evaluate(
        self, user_answer: str, standard_answer: str
    ) -> Dict[str, object]:
        standard_tokens = set(self._extract_tokens(standard_answer))
        user_tokens = set(self._extract_tokens(user_answer))

        if not standard_tokens:
            coverage_ratio = min(len((user_answer or "").strip()) / 160, 1.0)
        else:
            coverage_ratio = min(
                1.0, len(standard_tokens & user_tokens) / max(len(standard_tokens), 1) * 1.2
            )

        completeness_ratio, missing_points, strength_points, keypoint_ratio = (
            self._compute_completeness(
                user_answer=user_answer,
                standard_answer=standard_answer,
                coverage_ratio=coverage_ratio,
            )
        )

        logic_status = "Entailment" if coverage_ratio >= 0.65 else "Neutral"
        consistency_ratio = min(
            1.0,
            max(
                0.3,
                coverage_ratio * 0.75
                + completeness_ratio * 0.20
                + min(len((user_answer or "").strip()) / 220, 1.0) * 0.05,
            ),
        )

        coverage_score = round(coverage_ratio * 100, 2)
        consistency_score = round(consistency_ratio * 100, 2)
        completeness_score = round(completeness_ratio * 100, 2)
        mastery_ratio = coverage_ratio * 0.5 + consistency_ratio * 0.3 + completeness_ratio * 0.2
        mastery_score = round(max(0.0, min(1.0, mastery_ratio)) * 100, 2)

        if coverage_score < 25 and keypoint_ratio == 0:
            missing_points = self._extract_keypoints(standard_answer)[:4]

        reason_tags = self._build_reason_tags(
            coverage_score=coverage_score,
            consistency_score=consistency_score,
            completeness_score=completeness_score,
            logic_status=logic_status,
            missing_points=missing_points,
            provided_tags=["规则降级评分"],
        )
        nli_probs = self._build_logic_probs(logic_status, consistency_score)
        score_rationale = self._build_default_rationale(
            mastery_score=mastery_score,
            coverage_score=coverage_score,
            consistency_score=consistency_score,
            completeness_score=completeness_score,
            logic_status=logic_status,
            missing_points=missing_points,
            strength_points=strength_points,
        )

        return {
            "mastery_score": mastery_score,
            "coverage_raw": coverage_score,
            "coverage_score": coverage_score,
            "consistency_score": consistency_score,
            "completeness_score": completeness_score,
            "logic_status": logic_status,
            "nli_probs": nli_probs,
            "strength_points": strength_points,
            "missing_points": missing_points,
            "reason_tags": reason_tags,
            "score_rationale": score_rationale,
        }

    def _empty_result(self, standard_answer: str = "") -> Dict[str, object]:
        missing_points = self._extract_keypoints(standard_answer)[:4]
        return {
            "mastery_score": 0.0,
            "coverage_raw": 0.0,
            "coverage_score": 0.0,
            "consistency_score": 0.0,
            "completeness_score": 0.0,
            "logic_status": "Neutral",
            "nli_probs": {"Entailment": 0.0, "Neutral": 1.0, "Contradiction": 0.0},
            "strength_points": [],
            "missing_points": missing_points,
            "reason_tags": ["回答过短", "关键点覆盖不足"],
            "score_rationale": "回答过短，缺少可评估内容。",
        }

    def evaluate_mastery(
        self,
        user_answer: str,
        standard_answer: str,
        *,
        question_brief: str = "",
        concept: str = "",
        job: str = "",
        difficulty_label: str = "unknown",
    ) -> Dict[str, object]:
        if not user_answer or len(user_answer.strip()) < 2:
            return self._empty_result(standard_answer=standard_answer)

        if self.llm is None:
            return self._fallback_evaluate(user_answer=user_answer, standard_answer=standard_answer)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是技术面试评分官。请基于岗位、题目、标准答案和候选人回答，对本题进行结构化打分。

评分要求：
- coverage_score: 是否答到标准答案主线，0-100。
- consistency_score: 回答是否自洽、是否与标准答案冲突，0-100。
- completeness_score: 关键点、边界条件、实现取舍是否完整，0-100。
- logic_status: 只能是 Entailment / Neutral / Contradiction。
- strength_points: 1-3 个，写候选人已经答到的点。
- missing_points: 1-4 个，写仍缺失的关键点。
- reason_tags: 2-4 个，必须和分数一致，例如“核心方向基本对齐”“关键点覆盖不足”“存在逻辑冲突”。
- score_rationale: 1 句话解释题级分数，必须客观，不能和分数冲突。

岗位差异：
- backend 更关注系统设计、数据一致性、数据库/缓存、分布式、高可用、安全与工程取舍。
- frontend 更关注浏览器机制、组件设计、状态管理、渲染性能、工程化、交互体验与安全。

规则：
- 如果回答明显和标准答案冲突，logic_status 必须为 Contradiction，consistency_score 不得高于 45。
- 如果回答只触及概念但没展开实现与边界，logic_status 应偏 Neutral。
- 不要补写候选人没说过的优势。""",
                ),
                (
                    "user",
                    "【岗位】{job}\n【考点】{concept}\n【难度】{difficulty_label}\n【题目】{question_brief}\n【标准答案】{standard_answer}\n【候选人回答】{user_answer}",
                ),
            ]
        )

        try:
            judgement: ScoreJudgement = self._retry_structured_generation(
                prompt_template=prompt,
                input_data={
                    "job": job or "backend",
                    "concept": concept or "未知考点",
                    "difficulty_label": difficulty_label or "unknown",
                    "question_brief": question_brief or "未提供题目",
                    "standard_answer": standard_answer or "暂无标准答案",
                    "user_answer": user_answer,
                },
                model_class=ScoreJudgement,
                max_retries=3,
            )
        except Exception as exc:
            print(f"[Evaluator Fallback] LLM judge failed: {exc}")
            return self._fallback_evaluate(
                user_answer=user_answer,
                standard_answer=standard_answer,
            )

        coverage_score = self._clamp_score(judgement.coverage_score)
        consistency_score = self._clamp_score(judgement.consistency_score)
        completeness_score = self._clamp_score(judgement.completeness_score)
        logic_status = judgement.logic_status
        strength_points = self._normalize_points(judgement.strength_points, limit=3)
        missing_points = self._normalize_points(judgement.missing_points, limit=4)

        if coverage_score < 25 and not missing_points:
            missing_points = self._extract_keypoints(standard_answer)[:4]

        reason_tags = self._build_reason_tags(
            coverage_score=coverage_score,
            consistency_score=consistency_score,
            completeness_score=completeness_score,
            logic_status=logic_status,
            missing_points=missing_points,
            provided_tags=judgement.reason_tags,
        )

        coverage_ratio = coverage_score / 100
        consistency_ratio = consistency_score / 100
        completeness_ratio = completeness_score / 100
        mastery_ratio = coverage_ratio * 0.5 + consistency_ratio * 0.3 + completeness_ratio * 0.2
        mastery_score = round(max(0.0, min(1.0, mastery_ratio)) * 100, 2)

        if logic_status == "Contradiction" and mastery_score > 55:
            mastery_score = 55.0

        score_rationale = str(judgement.score_rationale or "").strip() or self._build_default_rationale(
            mastery_score=mastery_score,
            coverage_score=coverage_score,
            consistency_score=consistency_score,
            completeness_score=completeness_score,
            logic_status=logic_status,
            missing_points=missing_points,
            strength_points=strength_points,
        )

        return {
            "mastery_score": mastery_score,
            "coverage_raw": coverage_score,
            "coverage_score": coverage_score,
            "consistency_score": consistency_score,
            "completeness_score": completeness_score,
            "logic_status": logic_status,
            "nli_probs": self._build_logic_probs(logic_status, consistency_score),
            "strength_points": strength_points,
            "missing_points": missing_points,
            "reason_tags": reason_tags,
            "score_rationale": score_rationale,
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
