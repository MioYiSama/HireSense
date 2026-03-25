import json
from typing import Dict, Iterable, List

import httpx
from app.core.config import RECOMMEND_DATA
from app.models.schemas import AgentState, ReportContent, ReportPushRequest, ReviewItem
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

with open(str(RECOMMEND_DATA), "r", encoding="utf-8") as f:
    data = json.load(f)


class ReportNarrative(BaseModel):
    feedback: str = Field(description="给用户的总结反馈")
    shortcomings: List[str] = Field(description="列举用户的明显短板")
    advice: str = Field(description="给用户的总建议")
    urls: List[str] = Field(
        description="给出你所选择的推荐内容 text+url，必须完全来自所给 data，且内容不重复"
    )


class FinalReport:
    BACKEND_DIMENSIONS = {
        "分布式": ["分布式", "raft", "paxos", "一致性", "分片", "集群", "消息队列", "mq", "kafka", "redis锁", "微服务"],
        "性能": ["性能", "优化", "吞吐", "延迟", "压测", "jvm", "gc", "并发", "缓存", "switch", "复杂度"],
        "数据库": ["数据库", "mysql", "sql", "事务", "索引", "mvcc", "锁表", "binlog"],
        "API": ["api", "接口", "rest", "rpc", "http", "网关", "幂等", "鉴权", "openapi"],
        "安全": ["安全", "xss", "csrf", "sql注入", "权限", "认证", "授权", "加密"],
        "DevOps": ["devops", "docker", "k8s", "kubernetes", "部署", "ci/cd", "监控", "日志", "运维"],
    }
    FRONTEND_DIMENSIONS = {
        "设计": ["设计", "架构", "可维护", "模式", "抽象", "ui"],
        "性能": ["性能", "优化", "首屏", "渲染", "加载", "缓存", "包体积", "虚拟列表"],
        "工程化": ["工程化", "构建", "vite", "webpack", "eslint", "测试", "规范", "monorepo"],
        "组件化": ["组件", "复用", "封装", "hooks", "slot", "组合式", "设计系统"],
        "数据流": ["状态管理", "数据流", "vuex", "pinia", "redux", "响应式", "同步", "异步"],
        "安全": ["安全", "xss", "csrf", "权限", "鉴权", "沙箱", "内容安全策略"],
    }

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
        return FinalReport._round_dimension(min(value, cap))

    @staticmethod
    def _length_quality(text: str) -> float:
        normalized = min(len((text or "").strip()) / 160, 1.0)
        return normalized * 100

    def _specific_dimension_rules(self, job: str) -> Dict[str, List[str]]:
        if job == "backend":
            return self.BACKEND_DIMENSIONS
        if job == "frontend":
            return self.FRONTEND_DIMENSIONS
        raise ValueError(f"Invalid job type: {job}. Expected 'backend' or 'frontend'.")

    def _match_specific_dimensions(self, state: AgentState, log) -> List[str]:
        rules = self._specific_dimension_rules(state.job)
        haystack = " ".join(
            [
                log.concept or "",
                log.q_id or "",
                log.interviewer or "",
            ]
        ).lower()

        matched = [
            dimension
            for dimension, keywords in rules.items()
            if any(keyword.lower() in haystack for keyword in keywords)
        ]
        return matched

    def _build_general_scores(self, state: AgentState, final_score: float) -> Dict[str, float]:
        if not state.interview_logs:
            return {
                "逻辑思维": 0.0,
                "沟通表达": 0.0,
                "应变能力": 0.0,
                "自信度": 0.0,
                "学习能力": 0.0,
                "团队协同": 0.0,
            }

        overall_10 = final_score / 10
        coverage_avg = self._average(log.score_breakdown.coverage_score for log in state.interview_logs)
        consistency_avg = self._average(log.score_breakdown.consistency_score for log in state.interview_logs)
        completeness_avg = self._average(log.score_breakdown.completeness_score for log in state.interview_logs)
        length_avg = self._average(self._length_quality(log.interviewee) for log in state.interview_logs)
        probe_avg = self._average((log.probe_count for log in state.interview_logs), default=1.0)
        probe_pressure = max(0.0, min((probe_avg - 1.0) * 18, 25))
        recovery_score = max(0.0, min(final_score + probe_pressure, 100.0))

        raw_scores = {
            "逻辑思维": consistency_avg / 10,
            "沟通表达": (coverage_avg * 0.45 + completeness_avg * 0.30 + length_avg * 0.25) / 10,
            "应变能力": (consistency_avg * 0.40 + recovery_score * 0.35 + completeness_avg * 0.25) / 10,
            "自信度": (final_score * 0.55 + consistency_avg * 0.30 + max(0.0, 100 - probe_pressure * 2) * 0.15) / 10,
            "学习能力": (completeness_avg * 0.45 + recovery_score * 0.35 + final_score * 0.20) / 10,
            "团队协同": ((coverage_avg * 0.40 + length_avg * 0.25 + final_score * 0.35) / 10),
        }

        return {
            name: self._bound_against_overall(value, overall_10, spread=1.5)
            for name, value in raw_scores.items()
        }

    def _build_specific_scores(self, state: AgentState, final_score: float) -> Dict[str, float]:
        rules = self._specific_dimension_rules(state.job)
        overall_10 = final_score / 10
        buckets: Dict[str, List[float]] = {dimension: [] for dimension in rules}

        for log in state.interview_logs:
            matched = self._match_specific_dimensions(state, log)
            if not matched:
                continue
            for dimension in matched:
                buckets[dimension].append(log.final_score / 10)

        result: Dict[str, float] = {}
        for dimension in rules:
            raw_value = self._average(buckets[dimension], default=overall_10)
            result[dimension] = self._bound_against_overall(raw_value, overall_10, spread=1.8)
        return result

    def _build_reviews(self, state: AgentState) -> List[ReviewItem]:
        reviews = []
        for log in state.interview_logs:
            reviews.append(
                ReviewItem(
                    interviewer=log.interviewer,
                    interviewee=log.interviewee,
                    score=log.final_score,
                    advice=log.async_advice,
                    concept=log.concept or None,
                    reason_tags=log.reason_tags,
                )
            )
        return reviews

    def _build_history_transcript(self, state: AgentState) -> str:
        lines: List[str] = []
        for index, log in enumerate(state.interview_logs, start=1):
            lines.extend(
                [
                    f"题目{index}: {log.interviewer}",
                    f"考点: {log.concept}",
                    f"候选人回答: {log.interviewee}",
                    f"题级得分: {round(log.final_score, 2)}",
                    f"分项得分: 覆盖={log.score_breakdown.coverage_score}, 一致={log.score_breakdown.consistency_score}, 完整={log.score_breakdown.completeness_score}",
                    f"机器标签: {', '.join(log.reason_tags) if log.reason_tags else '无'}",
                    f"缺失点: {', '.join(log.missing_points) if log.missing_points else '无'}",
                    "--------------",
                ]
            )
        return "\n".join(lines)

    async def _build_narrative(
        self,
        state: AgentState,
        final_score: float,
        general_scores: Dict[str, float],
        specific_scores: Dict[str, float],
        history_transcript: str,
    ) -> ReportNarrative:
        prompt_tmp = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是技术总监。面试已结束，请基于底层【机器分数与题级证据】生成总结性文字。
                    你不能改写机器算出的总分和维度分，只能解释它们。

                    【候选人背景】{resume_star}
                    【建议学习资料】{data}

                    【输出要求】
                    1. feedback：总结候选人的整体表现，必须与机器分数一致。
                    2. shortcomings：列出 3~6 个短板，必须尽量来自机器缺失点和低分题表现。
                    3. advice：给出 1 段具体提升建议，不能空泛。
                    4. urls：从给定 data 中选择最相关的资源，格式必须是“标题  URL”。
                    5. 必须使用中文，必须客观，不允许把低分说成高分。""",
                ),
                (
                    "user",
                    "【机器总分】{final_score}\n【general维度】{general_scores}\n【specific维度】{specific_scores}\n【题级记录】\n{history_transcript}",
                ),
            ]
        )

        prompt = await prompt_tmp.ainvoke(
            {
                "resume_star": state.resume_star,
                "data": data,
                "final_score": round(final_score, 2),
                "general_scores": json.dumps(general_scores, ensure_ascii=False),
                "specific_scores": json.dumps(specific_scores, ensure_ascii=False),
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
        general_scores = self._build_general_scores(state, final_score)
        specific_scores = self._build_specific_scores(state, final_score)
        final_reviews = self._build_reviews(state)
        history_transcript = self._build_history_transcript(state)
        narrative = await self._build_narrative(
            state=state,
            final_score=final_score,
            general_scores=general_scores,
            specific_scores=specific_scores,
            history_transcript=history_transcript,
        )

        return ReportContent(
            score=final_score,
            general=general_scores,
            specific=specific_scores,
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
