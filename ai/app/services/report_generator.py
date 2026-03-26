import json
from typing import Dict, Iterable, List

import httpx
from app.core.config import RECOMMEND_DATA
from app.models.schemas import (
    AgentState,
    DimensionDetail,
    ReportContent,
    ReportPushRequest,
    ReviewItem,
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

with open(str(RECOMMEND_DATA), "r", encoding="utf-8") as f:
    data = json.load(f)


class DimensionNarrative(BaseModel):
    name: str = Field(description="维度名称")
    score: float = Field(description="0-10 的维度分")
    summary: str = Field(description="该维度的一句话总结")
    strength_points: List[str] = Field(default_factory=list, description="该维度下做得好的点")
    missing_points: List[str] = Field(default_factory=list, description="该维度下缺失的点")


class ReportNarrative(BaseModel):
    general_dimensions: List[DimensionNarrative] = Field(
        description="通用能力维度评分与解释"
    )
    specific_dimensions: List[DimensionNarrative] = Field(
        description="岗位能力维度评分与解释"
    )
    feedback: str = Field(description="给用户的总结反馈")
    shortcomings: List[str] = Field(description="列举用户的明显短板")
    advice: str = Field(description="给用户的总建议")
    urls: List[str] = Field(
        description="给出你所选择的推荐内容 text+url，必须完全来自所给 data，且内容不重复"
    )


class FinalReport:
    GENERAL_DIMENSIONS = [
        "逻辑思维",
        "沟通表达",
        "应变能力",
        "自信度",
        "学习能力",
        "团队协同",
    ]
    BACKEND_DIMENSIONS = [
        "后端基础",
        "数据库与缓存",
        "分布式与高可用",
        "接口设计与工程化",
        "稳定性与安全",
    ]
    FRONTEND_DIMENSIONS = [
        "前端基础",
        "组件设计与状态管理",
        "浏览器与渲染机制",
        "工程化与性能优化",
        "交互体验与安全",
    ]

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    @staticmethod
    def _round_dimension(value: float) -> float:
        return round(max(0.0, min(value, 10.0)), 1)

    @staticmethod
    def _average(values: Iterable[float], default: float = 0.0) -> float:
        collected = list(values)
        if not collected:
            return default
        return sum(collected) / len(collected)

    @staticmethod
    def _bound_against_overall(value: float, overall_10: float, spread: float = 1.5) -> float:
        cap = max(3.0, overall_10 + spread)
        floor = max(0.0, overall_10 - 3.0)
        return FinalReport._round_dimension(min(max(value, floor), cap))

    @staticmethod
    def _length_quality(text: str) -> float:
        normalized = min(len((text or "").strip()) / 160, 1.0)
        return normalized * 100

    @staticmethod
    def _normalize_points(points: List[str], limit: int = 3) -> List[str]:
        normalized: List[str] = []
        for point in points or []:
            text = str(point or "").strip()
            if not text or text in normalized:
                continue
            normalized.append(text)
            if len(normalized) >= limit:
                break
        return normalized

    def _specific_dimensions(self, job: str) -> List[str]:
        if job == "backend":
            return self.BACKEND_DIMENSIONS
        if job == "frontend":
            return self.FRONTEND_DIMENSIONS
        raise ValueError(f"Invalid job type: {job}. Expected 'backend' or 'frontend'.")

    def _build_general_score_baseline(
        self, state: AgentState, final_score: float
    ) -> Dict[str, float]:
        if not state.interview_logs:
            return {name: 0.0 for name in self.GENERAL_DIMENSIONS}

        overall_10 = final_score / 10
        coverage_avg = self._average(
            log.score_breakdown.coverage_score for log in state.interview_logs
        )
        consistency_avg = self._average(
            log.score_breakdown.consistency_score for log in state.interview_logs
        )
        completeness_avg = self._average(
            log.score_breakdown.completeness_score for log in state.interview_logs
        )
        length_avg = self._average(
            self._length_quality(log.interviewee) for log in state.interview_logs
        )
        probe_avg = self._average(
            (log.probe_count for log in state.interview_logs), default=1.0
        )
        probe_pressure = max(0.0, min((probe_avg - 1.0) * 18, 25))
        recovery_score = max(0.0, min(final_score + probe_pressure, 100.0))

        raw_scores = {
            "逻辑思维": consistency_avg / 10,
            "沟通表达": (coverage_avg * 0.45 + completeness_avg * 0.30 + length_avg * 0.25)
            / 10,
            "应变能力": (consistency_avg * 0.40 + recovery_score * 0.35 + completeness_avg * 0.25)
            / 10,
            "自信度": (
                final_score * 0.55
                + consistency_avg * 0.30
                + max(0.0, 100 - probe_pressure * 2) * 0.15
            )
            / 10,
            "学习能力": (completeness_avg * 0.45 + recovery_score * 0.35 + final_score * 0.20)
            / 10,
            "团队协同": ((coverage_avg * 0.40 + length_avg * 0.25 + final_score * 0.35) / 10),
        }
        return {
            name: self._bound_against_overall(value, overall_10, spread=1.5)
            for name, value in raw_scores.items()
        }

    def _default_dimension_detail(
        self, name: str, score: float, summary: str
    ) -> DimensionDetail:
        return DimensionDetail(
            score=self._round_dimension(score),
            summary=summary,
            strength_points=[],
            missing_points=[],
        )

    def _coerce_dimension_details(
        self,
        expected_names: List[str],
        payload_items: List[DimensionNarrative],
        fallback_scores: Dict[str, float],
        overall_10: float,
        spread: float,
    ) -> Dict[str, DimensionDetail]:
        payload_by_name = {str(item.name).strip(): item for item in payload_items or []}
        result: Dict[str, DimensionDetail] = {}

        for name in expected_names:
            payload = payload_by_name.get(name)
            base_score = fallback_scores.get(name, overall_10)
            score = base_score if payload is None else self._bound_against_overall(
                float(payload.score), overall_10, spread=spread
            )
            summary = (
                str(payload.summary).strip()
                if payload and str(payload.summary).strip()
                else f"{name}表现与整体得分基本一致。"
            )
            result[name] = DimensionDetail(
                score=score,
                summary=summary,
                strength_points=self._normalize_points(
                    payload.strength_points if payload else []
                ),
                missing_points=self._normalize_points(
                    payload.missing_points if payload else []
                ),
            )

        return result

    def _build_reviews(self, state: AgentState) -> List[ReviewItem]:
        reviews = []
        for log in state.interview_logs:
            reviews.append(
                ReviewItem(
                    interviewer=log.interviewer,
                    interviewer_role=log.interviewer_role,
                    interviewee=log.interviewee,
                    score=log.final_score,
                    advice=log.async_advice,
                    concept=log.concept or None,
                    difficulty_label=log.difficulty_label,
                    score_breakdown=log.score_breakdown,
                    reason_tags=log.reason_tags,
                    strength_points=log.strength_points,
                    missing_points=log.missing_points,
                    score_rationale=log.score_rationale,
                )
            )
        return reviews

    def _build_history_transcript(self, state: AgentState) -> str:
        lines: List[str] = []
        for index, log in enumerate(state.interview_logs, start=1):
            lines.extend(
                [
                    f"题目{index}: [{log.interviewer_role}] {log.interviewer}",
                    f"考点: {log.concept}",
                    f"难度: {log.difficulty_label}",
                    f"候选人回答: {log.interviewee}",
                    f"题级得分: {round(log.final_score, 2)}",
                    (
                        "分项得分: "
                        f"覆盖={log.score_breakdown.coverage_score}, "
                        f"一致={log.score_breakdown.consistency_score}, "
                        f"完整={log.score_breakdown.completeness_score}"
                    ),
                    f"亮点: {', '.join(log.strength_points) if log.strength_points else '无'}",
                    f"机器标签: {', '.join(log.reason_tags) if log.reason_tags else '无'}",
                    f"缺失点: {', '.join(log.missing_points) if log.missing_points else '无'}",
                    f"题级解释: {log.score_rationale or '无'}",
                    "--------------",
                ]
            )
        return "\n".join(lines)

    async def _build_narrative(
        self,
        state: AgentState,
        final_score: float,
        baseline_general_scores: Dict[str, float],
        history_transcript: str,
    ) -> ReportNarrative:
        specific_dimension_names = self._specific_dimensions(state.job)
        prompt_tmp = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是技术总监。面试已结束，请基于底层【机器总分与题级证据】输出结构化总结。
你不能改写机器总分，只能在机器总分附近给出合理的维度分和解释。

【候选人背景】{resume_star}
【岗位】{job}
【建议学习资料】{data}

【通用维度】{general_dimension_names}
【岗位维度】{specific_dimension_names}
【机器总分】{final_score}
【通用维度参考分】{baseline_general_scores}

输出要求：
1. general_dimensions 和 specific_dimensions 必须覆盖给定的所有维度名称，名称必须完全一致。
2. 每个维度都要给出 0-10 分、1 句 summary、1-3 个 strength_points、1-3 个 missing_points。
3. 维度分必须与题级证据一致，不允许整体低分却大面积高分。
4. feedback 要总结整体表现，必须和机器总分一致。
5. shortcomings 要列 3-6 个短板，优先来自低分题、缺失点和岗位维度短板。
6. advice 要给出具体提升建议，不能空泛。
7. urls 必须只从给定 data 中选择，格式必须是“标题  URL”。
8. 必须使用中文，客观，不允许把低分写成高分。""",
                ),
                (
                    "user",
                    "【题级记录】\n{history_transcript}",
                ),
            ]
        )

        prompt = await prompt_tmp.ainvoke(
            {
                "resume_star": state.resume_star,
                "job": state.job,
                "data": data,
                "general_dimension_names": json.dumps(
                    self.GENERAL_DIMENSIONS, ensure_ascii=False
                ),
                "specific_dimension_names": json.dumps(
                    specific_dimension_names, ensure_ascii=False
                ),
                "final_score": round(final_score, 2),
                "baseline_general_scores": json.dumps(
                    baseline_general_scores, ensure_ascii=False
                ),
                "history_transcript": history_transcript or "无有效题级记录",
            }
        )

        llm_with_structure = self.llm.with_structured_output(ReportNarrative)
        return await llm_with_structure.ainvoke(prompt)

    async def build_report(self, state: AgentState) -> ReportContent:
        if state.interview_logs is None:
            raise ValueError("面试日志不存在")

        final_score = round(
            self._average((log.final_score for log in state.interview_logs), default=0.0),
            2,
        )
        overall_10 = final_score / 10
        baseline_general_scores = self._build_general_score_baseline(state, final_score)
        baseline_specific_scores = {
            name: self._bound_against_overall(overall_10, overall_10, spread=1.8)
            for name in self._specific_dimensions(state.job)
        }
        history_transcript = self._build_history_transcript(state)
        final_reviews = self._build_reviews(state)
        narrative = await self._build_narrative(
            state=state,
            final_score=final_score,
            baseline_general_scores=baseline_general_scores,
            history_transcript=history_transcript,
        )

        general_details = self._coerce_dimension_details(
            expected_names=self.GENERAL_DIMENSIONS,
            payload_items=narrative.general_dimensions,
            fallback_scores=baseline_general_scores,
            overall_10=overall_10,
            spread=1.5,
        )
        specific_details = self._coerce_dimension_details(
            expected_names=self._specific_dimensions(state.job),
            payload_items=narrative.specific_dimensions,
            fallback_scores=baseline_specific_scores,
            overall_10=overall_10,
            spread=1.8,
        )
        general_scores = {
            name: detail.score for name, detail in general_details.items()
        }
        specific_scores = {
            name: detail.score for name, detail in specific_details.items()
        }

        return ReportContent(
            job=state.job,
            mode=state.mode,
            score=final_score,
            general=general_scores,
            general_details=general_details,
            specific=specific_scores,
            specific_details=specific_details,
            feedback=narrative.feedback,
            shortcomings=narrative.shortcomings,
            advice=narrative.advice,
            reviews=final_reviews,
            resources=narrative.urls,
        )

    async def generate_and_push(self, state: AgentState, target_url: str, secret: str):
        try:
            print(f" [Webhook] 正在为会话 {state.session_id} 生成评估报告...")
            report_content = await self.build_report(state)

            payload = ReportPushRequest(
                secret=secret, id=state.session_id, report=report_content
            )

            print(f" [Webhook] 报告生成完毕，正在推送到主控服务器: {target_url}")
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    target_url,
                    json=payload.model_dump(),
                    timeout=10.0,
                )
                response.raise_for_status()

                resp_data = response.json()
                if resp_data.get("success"):
                    print(
                        f" [Webhook] 报告归档成功！主控返回: {resp_data.get('message')}"
                    )
                else:
                    print(f" [Webhook] 报告推送被拒绝: {resp_data}")

        except Exception as e:
            print(f" [Webhook Error] 报告推送失败: {e}")

        finally:
            from app.core.state_manager import session_store

            session_store.delete_state(state.session_id)
            print(f"🧹 [System] 会话 {state.session_id} 内存已清理。")
