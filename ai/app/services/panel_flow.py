from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from app.core.history_manager import HistoryManager
from app.db import chroma_client, neo4j_client
from app.models.schemas import AgentState, IntentResult
from app.services import evaluator, intent_router, llm_generator
from app.services.llm_generator import Clarify
from app.services.panel_question_bank import (
    PanelQuestion,
    get_panel_question_candidates,
)


@dataclass
class PanelTurnReply:
    reply_speech: str
    ending: bool = False
    mode: str = "panel_trio"
    speaker_role: str = "hr"


class PanelInterviewCoordinator:
    PANEL_ROLE_SEQUENCE = ("tech_lead", "hr", "tech_lead", "executive")
    PANEL_EXECUTIVE_MIN_LOGS = 3
    PANEL_MIN_LOGS_BEFORE_END = 5
    PANEL_PROBE_THRESHOLD = 60.0
    PANEL_MAX_PROBE_NUM = 1
    BASIC_QUESTION_ROOT_BY_JOB = {
        "frontend": "04-JavaScript基础",
        "backend": "basis",
    }

    def __init__(
        self,
        intent_router_: intent_router.IntentGateway,
        evaluator_: evaluator.Evaluator,
        chroma_client_: chroma_client.ChromaClient,
        neo4j_client_: neo4j_client.Neo4jClient,
        llm_gen: llm_generator.LLMGenerator,
        history_manager: HistoryManager,
        finalize_question_log: Callable[
            [AgentState, str, str, str, Dict[str, object]], Optional[int]
        ],
    ):
        self.intent_router = intent_router_
        self.evaluator = evaluator_
        self.chroma_client = chroma_client_
        self.neo4j_client = neo4j_client_
        self.llm_gen = llm_gen
        self.history_manager = history_manager
        self.finalize_question_log = finalize_question_log

    @staticmethod
    def _reply(role: str, text: str, ending: bool = False) -> PanelTurnReply:
        return PanelTurnReply(
            reply_speech=text,
            ending=ending,
            speaker_role=role,
        )

    @staticmethod
    def _role_label(role: str) -> str:
        labels = {
            "hr": "HR",
            "tech_lead": "技术主管",
            "executive": "大老板",
        }
        return labels.get(role, role)

    @classmethod
    def _get_basic_question_root_name(cls, job: Optional[str]) -> str:
        return cls.BASIC_QUESTION_ROOT_BY_JOB.get((job or "").strip(), "basis")

    @staticmethod
    def _format_opening_question(question_brief: str) -> str:
        normalized = (question_brief or "").strip()
        if not normalized:
            return "先简单介绍一下你最近做过的项目。"
        if normalized[-1] in "。！？!?":
            return normalized
        return f"{normalized}？"

    def _build_opening_speech(self, question: PanelQuestion) -> str:
        question_text = self._format_opening_question(question.question_brief)
        return (
            "你好，我是 HR。今天这场群面会从匹配度、技术深度和业务判断三个角度一起看。"
            f"先从我开始，{question_text}"
        )

    def _build_transition_reply(
        self, current_role: str, next_question: PanelQuestion
    ) -> str:
        question_text = self._format_opening_question(next_question.question_brief)
        if next_question.interviewer_role == "tech_lead":
            return f"{self._role_label(current_role)}这边先收到。接下来由技术主管继续，从技术深度往下追一轮。{question_text}"
        if next_question.interviewer_role == "hr":
            return f"{self._role_label(current_role)}这边先到这。接下来 HR 从沟通协作和动机角度补充了解。{question_text}"
        return f"{self._role_label(current_role)}这部分我先记下。最后我从业务影响和取舍角度补几个问题。{question_text}"

    def _build_probe_reply(self, role: str, score_res: Dict[str, object]) -> str:
        missing_points = [
            str(item).strip()
            for item in score_res.get("missing_points", [])
            if str(item).strip()
        ]
        if role == "hr":
            if missing_points:
                return f"我再追问一下，你把{missing_points[0]}这部分说具体一点。"
            return "我再往下问一步，把当时你的判断依据、具体动作和结果说完整。"
        if role == "tech_lead":
            if missing_points:
                return f"这个回答主线还差一点，你继续补充一下{missing_points[0]}。"
            return "我再追问一个细节，把实现方案、边界条件和风险点展开。"
        if missing_points:
            return (
                f"我更关心你当时怎么做判断，你把{missing_points[0]}和取舍依据讲清楚。"
            )
        return "我再往深一层问一下，把目标、风险和你最终的取舍依据讲清楚。"

    def _build_thinking_reply(self, role: str) -> str:
        if role == "hr":
            return "没关系，你可以整理一下，再按背景、动作、结果的顺序说。"
        if role == "tech_lead":
            return "你可以先稳一下，从原理、实现和边界条件三个层面慢慢讲。"
        return "别急，你先给结论，再补充判断依据和取舍过程。"

    @staticmethod
    def _build_end_reply() -> str:
        return "好的，今天这场群面我先收口到这里。我们已经拿到了足够的样本，会结合 HR 和技术主管的观察统一整理反馈。"

    @staticmethod
    def _build_empty_state(
        session_id: str, job: str, personalization: str
    ) -> AgentState:
        return AgentState(
            session_id=session_id,
            job=job,
            mode="panel_trio",
            personalization=personalization,
            resume_star="",
            resume_concept_list=[],
            q_id_list=[],
            new_concept_list=[],
            chat_history=[],
            current_concept=None,
            visited_concept=[],
            visited_question=[],
            interview_logs=[],
            candidate_fact_sheet=[],
            current_question_difficulty="unknown",
            current_concept_cumulative_answer="",
            recent_messages="",
        )

    def _pick_static_question(self, state: AgentState, role: str) -> PanelQuestion:
        candidates = get_panel_question_candidates(job=state.job, role=role)
        if not candidates:
            raise ValueError(
                f"No panel question candidates for role={role} job={state.job}"
            )
        for question in candidates:
            if question.question_id not in state.visited_question:
                return question
        index = state.panel_round_counts.get(role, 0) % len(candidates)
        return candidates[index]

    async def _pick_technical_question(self, state: AgentState) -> PanelQuestion:
        basic_question = await self.neo4j_client.get_random_basic_question(
            root_name=self._get_basic_question_root_name(state.job)
        )
        if basic_question and all(
            str(basic_question.get(key) or "").strip()
            for key in ("concept", "q_id", "brief")
        ):
            q_id = str(basic_question.get("q_id") or "").strip()
            if q_id and q_id not in state.visited_question:
                concept = str(basic_question.get("concept") or "").strip()
                brief = str(basic_question.get("brief") or "").strip()
                std_answer = (
                    await self.chroma_client.async_get_standard_answer(q_id=q_id)
                    or "暂无标准答案"
                )
                return PanelQuestion(
                    question_id=q_id,
                    interviewer_role="tech_lead",
                    question_type="technical",
                    question_brief=brief,
                    standard_answer=std_answer,
                    difficulty_label="basic",
                    concept=concept,
                    focus_tags=[concept] if concept else [],
                )

        final_concepts = await self.neo4j_client.get_icebreaker_concept(
            resume_concepts=state.resume_concept_list,
            visited_concepts=state.visited_concept,
        )
        question_menu = await self.neo4j_client.get_batch_questions_brief(
            concept_list=final_concepts
        )
        for item in question_menu:
            concept = str(item.get("concept") or "").strip()
            for question in item.get("question_info") or []:
                q_id = str(question.get("q_id") or "").strip()
                brief = str(question.get("brief") or "").strip()
                if q_id and brief and q_id not in state.visited_question:
                    std_answer = (
                        await self.chroma_client.async_get_standard_answer(q_id=q_id)
                        or "暂无标准答案"
                    )
                    return PanelQuestion(
                        question_id=q_id,
                        interviewer_role="tech_lead",
                        question_type="technical",
                        question_brief=brief,
                        standard_answer=std_answer,
                        difficulty_label="intermediate",
                        concept=concept,
                        focus_tags=[concept] if concept else [],
                    )

        raise ValueError("No technical panel question available")

    async def _pick_question(self, state: AgentState, role: str) -> PanelQuestion:
        if role == "tech_lead":
            return await self._pick_technical_question(state)
        return self._pick_static_question(state, role)

    def _set_current_question(self, state: AgentState, question: PanelQuestion) -> None:
        state.current_interviewer_role = question.interviewer_role
        state.current_question_type = question.question_type
        state.current_question_standard_answer = question.standard_answer
        state.current_question_difficulty = question.difficulty_label
        state.current_concept = question.concept
        state.current_concept_cumulative_answer = ""
        state.probe_num = 0
        if question.concept and question.concept not in state.visited_concept:
            state.visited_concept.append(question.concept)
        if question.question_id not in state.visited_question:
            state.visited_question.append(question.question_id)
        state.panel_round_counts[question.interviewer_role] = (
            state.panel_round_counts.get(question.interviewer_role, 0) + 1
        )
        self.history_manager.q_id_add(
            state=state,
            q_id=question.question_id,
            question_brief=question.question_brief,
        )

    def _pick_next_role(self, state: AgentState) -> str:
        attempts = 0
        while attempts < len(self.PANEL_ROLE_SEQUENCE) * 2:
            role = self.PANEL_ROLE_SEQUENCE[
                state.panel_turn_index % len(self.PANEL_ROLE_SEQUENCE)
            ]
            state.panel_turn_index += 1
            attempts += 1
            if (
                role == "executive"
                and len(state.interview_logs) < self.PANEL_EXECUTIVE_MIN_LOGS
            ):
                continue
            return role
        return "tech_lead"

    async def build_initial_state(
        self, session_id: str, job: str, personalization: str
    ) -> Tuple[AgentState, PanelTurnReply]:
        state = self._build_empty_state(session_id, job, personalization)
        opening_question = self._pick_static_question(state, "hr")
        self._set_current_question(state, opening_question)
        opening_speech = self._build_opening_speech(opening_question)
        self.history_manager.add_messages(
            state=state,
            content=opening_speech,
            role=opening_question.interviewer_role,
            concept=opening_question.concept,
        )
        return state, self._reply(opening_question.interviewer_role, opening_speech)

    async def _advance(self, state: AgentState) -> PanelTurnReply:
        current_role = state.current_interviewer_role
        if (
            current_role == "executive"
            and len(state.interview_logs) >= self.PANEL_MIN_LOGS_BEFORE_END
        ):
            state.is_finished = True
            closing = self._build_end_reply()
            self.history_manager.add_messages(
                state=state,
                content=closing,
                role="executive",
                concept=state.current_concept,
            )
            return self._reply("executive", closing, ending=True)

        try:
            next_role = self._pick_next_role(state)
            next_question = await self._pick_question(state, next_role)
        except Exception as exc:
            print(f"[Panel Flow] Failed to pick next interviewer: {exc}")
            state.is_finished = True
            closing = self._build_end_reply()
            self.history_manager.add_messages(
                state=state,
                content=closing,
                role="executive",
                concept=state.current_concept,
            )
            return self._reply("executive", closing, ending=True)

        self._set_current_question(state, next_question)
        reply_speech = self._build_transition_reply(current_role, next_question)
        self.history_manager.add_messages(
            state=state,
            content=reply_speech,
            role=next_question.interviewer_role,
            concept=next_question.concept,
        )
        return self._reply(next_question.interviewer_role, reply_speech)

    async def process_turn(self, state: AgentState, user_text: str) -> PanelTurnReply:
        self.history_manager.add_messages(
            state=state,
            content=user_text,
            role="interviewee",
            concept=state.current_concept,
        )
        self.history_manager.add_track_memory(state=state)

        intent_res: IntentResult = await self.intent_router.analyze(
            current_topic=state.current_concept,
            user_text=user_text,
        )
        q_id, question_brief = self.history_manager.q_id_get(state=state)
        std_ans = state.current_question_standard_answer or "暂无标准答案"
        current_role = state.current_interviewer_role

        if intent_res.intent == "THINKING":
            reply_speech = self._build_thinking_reply(current_role)
            self.history_manager.add_messages(
                state=state,
                content=reply_speech,
                role=current_role,
                concept=state.current_concept,
            )
            return self._reply(current_role, reply_speech)

        if intent_res.intent == "CLARIFY":
            res: Clarify = await self.llm_gen.clarify_question(
                user_text=user_text,
                current_topic=state.current_concept,
                question_brief=question_brief,
                std_answer=std_ans,
                history=state.recent_messages,
            )
            self.history_manager.add_messages(
                state=state,
                content=res.reply_speech,
                role=current_role,
                concept=state.current_concept,
            )
            return self._reply(current_role, res.reply_speech)

        state.current_concept_cumulative_answer += f" {user_text}"
        score_res = self.evaluator.evaluate_mastery(
            state.current_concept_cumulative_answer,
            std_ans,
            question_brief=question_brief,
            concept=state.current_concept or "",
            job=state.job,
            difficulty_label=state.current_question_difficulty,
        )
        if not isinstance(score_res, dict):
            score_res = {
                "mastery_score": 0.0,
                "logic_status": "Neutral",
                "coverage_raw": 0.0,
                "coverage_score": 0.0,
                "consistency_score": 0.0,
                "completeness_score": 0.0,
                "strength_points": [],
                "missing_points": [],
                "reason_tags": ["评分结果异常"],
                "score_rationale": "评分服务返回异常，按保守规则处理。",
            }

        should_probe = (
            intent_res.intent == "ANSWER"
            and state.probe_num < self.PANEL_MAX_PROBE_NUM
            and float(score_res.get("mastery_score", 0.0)) < self.PANEL_PROBE_THRESHOLD
        )
        if should_probe:
            state.probe_num += 1
            reply_speech = self._build_probe_reply(current_role, score_res)
            self.history_manager.add_messages(
                state=state,
                content=reply_speech,
                role=current_role,
                concept=state.current_concept,
            )
            return self._reply(current_role, reply_speech)

        self.finalize_question_log(
            state=state,
            q_id=q_id,
            question_brief=question_brief,
            std_answer=std_ans,
            score_res=score_res,
        )
        return await self._advance(state)
