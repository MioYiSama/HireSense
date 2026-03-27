import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from app.models.schemas import AgentState, IntentResult, InterviewRoundLog, StartRequest, ParsedResume
from app.core.history_manager import HistoryManager
from app.db import chroma_client, neo4j_client
from app.services import intent_router, llm_generator, evaluator
from app.services.llm_generator import Clarify, TacticalDecision
from app.services.panel_flow import PanelInterviewCoordinator
from app.services.resume_analyzer import ResumeAnalyzer
from app.core.state_manager import session_store


@dataclass
class TurnReply:
    reply_speech: str
    ending: bool = False
    mode: str = "single"
    speaker_role: str = "ai"


class AgentFlow:
    MIN_COMPLETED_ROUNDS_BEFORE_END = 3
    LOW_SCORE_THRESHOLD = 40.0
    LOW_RECENT_SCORE_THRESHOLD = 45.0
    LOW_AVG_SCORE_THRESHOLD = 50.0
    HIGH_SCORE_THRESHOLD = 85.0
    HIGH_AVG_SCORE_THRESHOLD = 80.0

    def __init__(self,
                 intent_router_: intent_router.IntentGateway,
                 evaluator_: evaluator.Evaluator,
                 chroma_client_: chroma_client.ChromaClient,
                 neo4j_client_: neo4j_client.Neo4jClient,
                 llm_gen: llm_generator.LLMGenerator,
                 history_manager: HistoryManager,
                 strategy: evaluator.PruningStrategy,
                 resume_analyzer: ResumeAnalyzer,
                 ):
        self.intent_router = intent_router_
        self.evaluator = evaluator_
        self.chroma_client = chroma_client_
        self.neo4j_client = neo4j_client_
        self.llm_gen = llm_gen
        self.history_manager = history_manager
        self.strategy = strategy
        self.resume_analyzer = resume_analyzer

        # 强引用后台任务，防止被垃圾回收 (非 FastAPI 环境下的纯 asyncio 保底做法)
        self._background_tasks = set()
        self.panel_coordinator = PanelInterviewCoordinator(
            intent_router_=intent_router_,
            evaluator_=evaluator_,
            chroma_client_=chroma_client_,
            neo4j_client_=neo4j_client_,
            llm_gen=llm_gen,
            history_manager=history_manager,
            finalize_question_log=self._finalize_question_log,
        )

    def _track_background_task(self, task: asyncio.Task) -> None:
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    @staticmethod
    def _iter_menu_items(question_menu) -> List[dict]:
        if isinstance(question_menu, dict):
            items: List[dict] = []
            for value in question_menu.values():
                if isinstance(value, list):
                    items.extend(item for item in value if isinstance(item, dict))
            return items
        if isinstance(question_menu, list):
            return [item for item in question_menu if isinstance(item, dict)]
        return []

    @staticmethod
    def _map_bucket_to_difficulty(bucket_name: Optional[str]) -> str:
        normalized = (bucket_name or "").strip()
        if "问题深入" in normalized:
            return "advanced"
        if "问题降级" in normalized:
            return "basic"
        if "问题平移" in normalized or "扩展" in normalized or "跳跃" in normalized:
            return "intermediate"
        return "intermediate" if normalized else "unknown"

    def _infer_question_difficulty(
        self,
        question_menu,
        q_id: Optional[str],
        concept: Optional[str],
    ) -> str:
        target_q_id = str(q_id or "").strip()
        target_concept = str(concept or "").strip()

        if isinstance(question_menu, dict):
            for bucket_name, items in question_menu.items():
                for item in self._iter_menu_items(items):
                    concept_name = str(item.get("concept") or "").strip()
                    if target_concept and concept_name and target_concept != concept_name:
                        continue

                    question_info = item.get("question_info") or []
                    if not isinstance(question_info, list):
                        continue

                    for question in question_info:
                        if not isinstance(question, dict):
                            continue
                        current_q_id = str(question.get("q_id") or "").strip()
                        if target_q_id and current_q_id == target_q_id:
                            return self._map_bucket_to_difficulty(bucket_name)
            return "unknown"

        if isinstance(question_menu, list):
            for item in self._iter_menu_items(question_menu):
                concept_name = str(item.get("concept") or "").strip()
                if target_concept and concept_name and target_concept != concept_name:
                    continue

                question_info = item.get("question_info") or []
                if not isinstance(question_info, list):
                    continue

                for question in question_info:
                    if not isinstance(question, dict):
                        continue
                    current_q_id = str(question.get("q_id") or "").strip()
                    if target_q_id and current_q_id == target_q_id:
                        return "intermediate"

        return "unknown"

    @staticmethod
    def _pick_initial_question(question_menu: list) -> Tuple[str, str, str]:
        for item in AgentFlow._iter_menu_items(question_menu):
            if not isinstance(item, dict):
                continue

            concept = str(item.get("concept") or "").strip()
            if not concept:
                continue

            question_info = item.get("question_info") or []
            if not isinstance(question_info, list):
                continue

            for question in question_info:
                if not isinstance(question, dict):
                    continue

                q_id = str(question.get("q_id") or "").strip()
                brief = str(question.get("brief") or "").strip()
                if q_id and brief:
                    return concept, q_id, brief

        raise ValueError("No valid opening question available")

    def _build_prospective_rounds(
        self,
        state: AgentState,
        include_current_answer: bool,
        score_res: Optional[Dict[str, object]],
    ) -> List[Dict[str, object]]:
        rounds = [
            {
                "score": float(log.final_score),
                "difficulty": str(log.difficulty_label or "unknown"),
            }
            for log in state.interview_logs
        ]

        if include_current_answer and state.current_concept_cumulative_answer.strip() and score_res:
            rounds.append(
                {
                    "score": float(score_res.get("mastery_score", 0.0)),
                    "difficulty": str(state.current_question_difficulty or "unknown"),
                }
            )

        return rounds

    def _qualifies_for_poor_end(self, rounds: List[Dict[str, object]]) -> bool:
        if len(rounds) < self.MIN_COMPLETED_ROUNDS_BEFORE_END:
            return False

        scores = [float(item["score"]) for item in rounds]
        recent_scores = scores[-2:]
        low_score_count = sum(score <= self.LOW_SCORE_THRESHOLD for score in scores)
        average_score = sum(scores) / len(scores)
        return (
            low_score_count >= 2
            and len(recent_scores) == 2
            and all(score <= self.LOW_RECENT_SCORE_THRESHOLD for score in recent_scores)
            and average_score <= self.LOW_AVG_SCORE_THRESHOLD
        )

    def _qualifies_for_strong_end(self, rounds: List[Dict[str, object]]) -> bool:
        if len(rounds) < self.MIN_COMPLETED_ROUNDS_BEFORE_END:
            return False

        scores = [float(item["score"]) for item in rounds]
        average_score = sum(scores) / len(scores)
        has_advanced_high_score = any(
            str(item.get("difficulty") or "") == "advanced"
            and float(item.get("score") or 0.0) >= self.HIGH_SCORE_THRESHOLD
            for item in rounds
        )
        no_clear_collapse = all(score >= 60.0 for score in scores[-2:])
        return (
            has_advanced_high_score
            and average_score >= self.HIGH_AVG_SCORE_THRESHOLD
            and scores[-1] >= self.HIGH_SCORE_THRESHOLD
            and no_clear_collapse
        )

    def _allow_end(
        self,
        state: AgentState,
        include_current_answer: bool,
        score_res: Optional[Dict[str, object]] = None,
    ) -> bool:
        rounds = self._build_prospective_rounds(
            state=state,
            include_current_answer=include_current_answer,
            score_res=score_res,
        )
        return self._qualifies_for_poor_end(rounds) or self._qualifies_for_strong_end(rounds)

    def _build_forced_transition_reply(
        self,
        current_topic: Optional[str],
        next_concept: str,
        next_question_brief: str,
    ) -> str:
        question = self._format_opening_question(next_question_brief)
        if current_topic and current_topic != next_concept:
            return f"这个点我先记下，我们继续扩大样本，接下来换到{next_concept}。{question}"
        return f"这个点先到这，我换个角度继续考察。{question}"

    def _build_forced_probe_reply(self, score_res: Dict[str, object]) -> str:
        missing_points = [str(item).strip() for item in score_res.get("missing_points", []) if str(item).strip()]
        if missing_points:
            return f"先别急着结束，我再追问一个关键点：你补充一下{missing_points[0]}这部分。"
        if float(score_res.get("mastery_score", 0.0)) >= 70:
            return "先别急着结束，我再追问一个细节：把刚才的实现取舍和边界条件展开一下。"
        return "先别急着结束，我再换个角度追问一下，把核心原理、实现细节和边界条件补充完整。"

    def _stabilize_early_end(
        self,
        state: AgentState,
        res: TacticalDecision,
        question_menu,
        score_res: Optional[Dict[str, object]],
        include_current_answer: bool,
    ) -> TacticalDecision:
        if res.action != "END" or self._allow_end(state, include_current_answer, score_res):
            return res

        try:
            next_concept, next_q_id, next_brief = self._pick_initial_question(question_menu)
            return TacticalDecision(
                reasoning=f"{res.reasoning} | 系统兜底：当前有效题数不足，禁止结束，改为继续采样。",
                action="TRANSITION",
                selected_node=next_concept,
                reply_speech=self._build_forced_transition_reply(
                    current_topic=state.current_concept,
                    next_concept=next_concept,
                    next_question_brief=next_brief,
                ),
                q_id_and_brief=[next_q_id, next_brief],
            )
        except Exception:
            return TacticalDecision(
                reasoning=f"{res.reasoning} | 系统兜底：当前有效题数不足，且暂无可靠新题，改为追问。",
                action="PROBE",
                selected_node=None,
                reply_speech=self._build_forced_probe_reply(score_res or {}),
                q_id_and_brief=None,
            )

    @staticmethod
    def _format_opening_question(question_brief: str) -> str:
        normalized = (question_brief or "").strip()
        if not normalized:
            return "先简单介绍一下你最近做过的项目。"

        if normalized[-1] in "。！？!?":
            return normalized
        return f"{normalized}？"

    def _build_fast_opening_speech(
        self, personalization: str, concept: str, question_brief: str
    ) -> str:
        question = self._format_opening_question(question_brief)
        if personalization:
            return f"我们按你偏好的节奏来，先从{concept}开始。{question}"
        return f"我们直接开始，先从{concept}这个点切入。{question}"

    async def _hydrate_session_context(
        self, state: AgentState, resume_text: str, job_domain: str
    ) -> None:
        try:
            resume: ParsedResume = await self.resume_analyzer.analyze_and_align(
                resume_text=resume_text,
                job_domain=job_domain,
            )
            align_concepts = await self.chroma_client.async_batch_align_concepts(
                resume.core_skills
            )

            state.resume_star = resume.projects_star_summary
            state.resume_concept_list = align_concepts
        except Exception as e:
            print(f"[Start Warmup Error] Session {state.session_id}: {e}")

    async def _async_generate_and_save_advice(self, state: AgentState, round_index: int, question: str,
                                              user_answer: str, std_answer: str, score: float,
                                              score_breakdown: Dict[str, float],
                                              strength_points: List[str],
                                              missing_points: List[str], logic_status: str,
                                              reason_tags: List[str],
                                              score_rationale: str):
        try:
            advice = await self.llm_gen.gen_single_advice(
                question=question,
                user_ans=user_answer,
                std_ans=std_answer,
                score=score,
                score_breakdown=score_breakdown,
                strength_points=strength_points,
                missing_points=missing_points,
                logic_status=logic_status,
                reason_tags=reason_tags,
                score_rationale=score_rationale,
            )
            state.interview_logs[round_index].async_advice = advice
        except Exception as e:
            print(f"[Async Advice Error] 第 {round_index} 题点评生成失败: {e}")
            state.interview_logs[round_index].async_advice = "暂无点评"

    def _finalize_question_log(
        self,
        state: AgentState,
        q_id: str,
        question_brief: str,
        std_answer: str,
        score_res: Dict[str, object],
    ) -> Optional[int]:
        cumulative_answer = state.current_concept_cumulative_answer.strip()
        if not cumulative_answer:
            return None

        round_log = InterviewRoundLog(
            q_id=q_id,
            question_type=state.current_question_type or "technical",
            concept=state.current_concept or "",
            difficulty_label=state.current_question_difficulty or "unknown",
            interviewer_role=state.current_interviewer_role or "ai",
            interviewer=question_brief,
            interviewee=cumulative_answer,
            standard_answer=std_answer or "",
            sts_coverage=float(score_res.get("coverage_raw", 0.0)),
            nli_logic=str(score_res.get("logic_status", "Neutral")),
            nli_probs=dict(score_res.get("nli_probs", {})),
            score_breakdown={
                "coverage_score": float(score_res.get("coverage_score", 0.0)),
                "consistency_score": float(score_res.get("consistency_score", 0.0)),
                "completeness_score": float(score_res.get("completeness_score", 0.0)),
            },
            strength_points=list(score_res.get("strength_points", [])),
            missing_points=list(score_res.get("missing_points", [])),
            reason_tags=list(score_res.get("reason_tags", [])),
            score_rationale=str(score_res.get("score_rationale", "")),
            probe_count=state.probe_num + 1,
            final_score=float(score_res.get("mastery_score", 0.0)),
            async_advice="",
        )
        state.interview_logs.append(round_log)
        round_index = len(state.interview_logs) - 1

        task = asyncio.create_task(
            self._async_generate_and_save_advice(
                state=state,
                round_index=round_index,
                question=question_brief,
                user_answer=cumulative_answer,
                std_answer=std_answer,
                score=float(score_res.get("mastery_score", 0.0)),
                score_breakdown={
                    "coverage_score": float(score_res.get("coverage_score", 0.0)),
                    "consistency_score": float(score_res.get("consistency_score", 0.0)),
                    "completeness_score": float(score_res.get("completeness_score", 0.0)),
                },
                strength_points=list(score_res.get("strength_points", [])),
                missing_points=list(score_res.get("missing_points", [])),
                logic_status=str(score_res.get("logic_status", "Neutral")),
                reason_tags=list(score_res.get("reason_tags", [])),
                score_rationale=str(score_res.get("score_rationale", "")),
            )
        )
        self._track_background_task(task)
        return round_index

    async def process_turn(self, state: AgentState, user_text: str) -> TurnReply:
        if state.mode == "panel_trio":
            panel_reply = await self.panel_coordinator.process_turn(state, user_text)
            return TurnReply(
                reply_speech=panel_reply.reply_speech,
                ending=panel_reply.ending,
                mode=panel_reply.mode,
                speaker_role=panel_reply.speaker_role,
            )

        # 1. 记忆更新与切片
        self.history_manager.add_messages(state=state, content=user_text, role="interviewee",
                                          concept=state.current_concept)
        self.history_manager.add_track_memory(state=state)
        # 2. 意图获取与当前基础信息读取
        intent_res: IntentResult = await self.intent_router.analyze(current_topic=state.current_concept,
                                                                    user_text=user_text)
        q_id, question_brief = self.history_manager.q_id_get(state=state)
        std_ans = await self.chroma_client.async_get_standard_answer(q_id=q_id)

        # ---------------------------------------------------------
        # 分支 A: 意图拦截 (THINKING / CLARIFY)
        # ---------------------------------------------------------
        if intent_res.intent == "THINKING":  # 修正大小写保持一致
            reply_speech = "没关系，你可以慢慢理一下思路。"
            self.history_manager.add_messages(state=state, content=reply_speech, role="interviewer",
                                              concept=state.current_concept)
            return TurnReply(reply_speech=reply_speech)

        if intent_res.intent == "CLARIFY":
            res: Clarify = await self.llm_gen.clarify_question(
                user_text=user_text, current_topic=state.current_concept,
                question_brief=question_brief, std_answer=std_ans, history=state.recent_messages
            )
            self.history_manager.add_messages(state=state, content=res.reply_speech, role="interviewer",
                                              concept=state.current_concept)
            return TurnReply(reply_speech=res.reply_speech)

        # ---------------------------------------------------------
        # 模块：新概念/话题跃迁提取 (按需执行，避免 I/O 浪费)
        # ---------------------------------------------------------
        final_concepts = []
        if intent_res.extracted_novel_concepts:
            align_concepts = await self.chroma_client.async_batch_align_concepts(raw_skills=intent_res.extracted_novel_concepts)
            if align_concepts:
                # 返回合法概念的列表，如未命中返回 ["No result"]
                final_concepts = await self.neo4j_client.verify_and_route_novel_concepts(concept_list=align_concepts)

        # ---------------------------------------------------------
        # 分支 B: 纯话题跃迁 (SHIFT) -
        # ---------------------------------------------------------
        if intent_res.intent == "SHIFT":
            # 如果新提取的概念全军覆没，使用破冰题兜底
            if not final_concepts or final_concepts[0] == "No result":
                fallback_concept = await self.neo4j_client.get_icebreaker_concept(
                    resume_concepts=state.resume_concept_list, visited_concepts=state.visited_concept
                )
                final_concepts = fallback_concept

            # 获取菜单 (此时是强制切换，菜单里只有用户想聊的内容或兜底内容)
            question_menu = await self.neo4j_client.get_batch_questions_brief(concept_list=final_concepts)

            res: TacticalDecision = await self.llm_gen.decide_tactics_and_generate(
                current_topic=state.current_concept,
                question_brief=question_brief,
                std_answer=std_ans,
                cumulative_answer=user_text,
                mastery_score=0.0,  # 逃兵直接定 0 分
                completed_rounds=len(state.interview_logs),
                current_turn=state.probe_num,
                menu=question_menu,
                history=state.recent_messages,
                candidate_fact_sheet=state.candidate_fact_sheet,
                resume_star=state.resume_star,
                max_turn=state.MAX_probe_num,
                allow_end=self._allow_end(state, include_current_answer=False, score_res=None),
            )
            res = self._stabilize_early_end(
                state=state,
                res=res,
                question_menu=question_menu,
                score_res=None,
                include_current_answer=False,
            )

            if res.action == "END":
                state.is_finished = True
                self.history_manager.add_messages(state=state, content=res.reply_speech, role="interviewer",
                                                  concept=state.current_concept)
                return TurnReply(reply_speech=res.reply_speech, ending=True)

            if res.action == "TRANSITION":
                self._execute_transition(state, res, question_menu)
            else:
                self.history_manager.add_messages(state=state, content=res.reply_speech, role="interviewer",
                                                  concept=state.current_concept)
            return TurnReply(reply_speech=res.reply_speech)

        # ---------------------------------------------------------
        # 分支 C: 正常回答 (ANSWER) - 核心逻辑流
        # ---------------------------------------------------------
        if intent_res.intent == "ANSWER":
            # 1. 如果用户边答题边提到了新概念 ，加入扩展菜单
            menu_extend = {}
            if final_concepts and final_concepts[0] != "No result":
                menu_extend = await self.neo4j_client.get_batch_questions_brief(concept_list=final_concepts)

            # 2. 累计打分机制
            state.current_concept_cumulative_answer += f" {user_text}"  # 统一变量名

            # 防御性检查：确保 std_ans 不为空
            if not std_ans:
                std_ans = "暂无标准答案"

            score_res = self.evaluator.evaluate_mastery(
                state.current_concept_cumulative_answer,
                std_ans,
                question_brief=question_brief,
                concept=state.current_concept or "",
                job=state.job,
                difficulty_label=state.current_question_difficulty,
            )

            # 防御性检查：确保 score_res 是字典
            if not isinstance(score_res, dict):
                print(f"[Warning] evaluate_mastery returned non-dict: {type(score_res)}, {score_res}")
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

            m_score, l_status, c_score = score_res["mastery_score"], score_res["logic_status"], score_res["coverage_raw"]

            # 3. 图谱菜单剪枝 (结合真实分数)
            limit_fwd, limit_sib, limit_bwd = self.strategy.calculate_quota(m_score, l_status)
            menu = await self.neo4j_client.get_action_space_candidates(
                current_concept=state.current_concept, visited=state.visited_concept,
                resume_concepts=state.resume_concept_list, limit_fwd=limit_fwd, limit_bwd=limit_bwd, limit_sib=limit_sib
            )

            # 防御性检查：确保 menu 是字典
            if not isinstance(menu, dict):
                print(f"[Warning] get_action_space_candidates returned non-dict: {type(menu)}, {menu}")
                menu = {}

            # 【高阶设计】：完美融合底层硬性路由选项与用户意图产生的新选项
            if menu_extend and isinstance(menu_extend, list):
                menu["用户发散扩展"] = menu_extend

            # 4. LLM 中枢决断 (传入真实的 m_score)
            res: TacticalDecision = await self.llm_gen.decide_tactics_and_generate(
                current_topic=state.current_concept,
                question_brief=question_brief,
                std_answer=std_ans,
                cumulative_answer=state.current_concept_cumulative_answer,
                mastery_score=m_score,
                completed_rounds=len(state.interview_logs),
                current_turn=state.probe_num,
                menu=menu,
                history=state.recent_messages,
                candidate_fact_sheet=state.candidate_fact_sheet,
                resume_star=state.resume_star,
                max_turn=state.MAX_probe_num,
                allow_end=self._allow_end(state, include_current_answer=True, score_res=score_res),
            )
            res = self._stabilize_early_end(
                state=state,
                res=res,
                question_menu=menu,
                score_res=score_res,
                include_current_answer=True,
            )

            # 5. 状态机推进
            if res.action == "END":
                self._finalize_question_log(
                    state=state,
                    q_id=q_id,
                    question_brief=question_brief,
                    std_answer=std_ans,
                    score_res=score_res,
                )
                state.is_finished = True
                self.history_manager.add_messages(state=state, content=res.reply_speech, role="interviewer",
                                                  concept=state.current_concept)
                return TurnReply(reply_speech=res.reply_speech, ending=True)

            if res.action == "TRANSITION":
                self._finalize_question_log(
                    state=state,
                    q_id=q_id,
                    question_brief=question_brief,
                    std_answer=std_ans,
                    score_res=score_res,
                )
                self._execute_transition(state, res, menu)
            elif res.action == "PROBE":
                state.probe_num += 1
                self.history_manager.add_messages(state=state, content=res.reply_speech, role="interviewer",
                                                  concept=state.current_concept)

            return TurnReply(reply_speech=res.reply_speech)

    # ==========================================
    # 辅助私有方法
    # ==========================================
    def _execute_transition(self, state: AgentState, res: TacticalDecision, question_menu=None):
        """统一封装状态跳转逻辑，保持主流程整洁"""
        if res.selected_node:
            inferred_difficulty = self._infer_question_difficulty(
                question_menu=question_menu,
                q_id=(res.q_id_and_brief[0] if res.q_id_and_brief else None),
                concept=res.selected_node,
            )
            state.current_concept = res.selected_node
            state.visited_concept.append(res.selected_node)
            state.probe_num = 0
            state.current_question_difficulty = inferred_difficulty
            state.current_question_type = "technical"
            state.current_interviewer_role = "ai"
            state.current_question_standard_answer = ""
            state.current_concept_cumulative_answer = ""  # 清空上题的累积回答

        if res.q_id_and_brief:
            # 你在模型里返回了元组 [q_id, brief]，这里更新题目游标
            self.history_manager.q_id_add(state, res.q_id_and_brief[0], res.q_id_and_brief[1])

        self.history_manager.add_messages(state=state, content=res.reply_speech, role="interviewer",
                                          concept=state.current_concept)

    async def initialize_session(self, req: StartRequest) -> dict:
        personalization = (req.personalization or "").strip()
        resume_text = req.resume or ""

        if req.mode == "panel_trio":
            new_state, opening_reply = await self.panel_coordinator.build_initial_state(
                session_id=req.id,
                job=req.job,
                personalization=personalization,
            )
            session_store.save_state(req.id, new_state)
            warmup_task = asyncio.create_task(
                self._hydrate_session_context(
                    state=new_state,
                    resume_text=resume_text,
                    job_domain=req.job,
                )
            )
            self._track_background_task(warmup_task)

            return {
                "id": req.id,
                "reply_speech": opening_reply.reply_speech,
                "mode": opening_reply.mode,
                "speaker_role": opening_reply.speaker_role,
            }

        # 首题快速路径：优先从基础题题库随机抽题；若题库缺失则回退到既有破冰逻辑。
        basic_question = await self.neo4j_client.get_random_basic_question()
        if basic_question and all(
            str(basic_question.get(key) or "").strip()
            for key in ("concept", "q_id", "brief")
        ):
            selected_concept = str(basic_question.get("concept") or "").strip()
            q_id = str(basic_question.get("q_id") or "").strip()
            question_brief = str(basic_question.get("brief") or "").strip()
        else:
            final_concepts = await self.neo4j_client.get_icebreaker_concept(
                resume_concepts=[],
                visited_concepts=[],
            )
            question_menu = await self.neo4j_client.get_batch_questions_brief(concept_list=final_concepts)
            selected_concept, q_id, question_brief = self._pick_initial_question(question_menu)

        opening_speech = self._build_fast_opening_speech(
            personalization=personalization,
            concept=selected_concept,
            question_brief=question_brief,
        )

        # 创建状态
        new_state = AgentState(
            session_id=req.id,
            job=req.job,
            mode="single",
            personalization=personalization,
            resume_star="",
            resume_concept_list=[],
            current_concept=selected_concept,
            current_interviewer_role="ai",
            visited_concept=[selected_concept],
            q_id_list=[],
            new_concept_list=[],
            chat_history=[],
            interview_logs=[],
            candidate_fact_sheet=[],
            current_question_type="technical",
            current_question_difficulty="basic",
            current_question_standard_answer="",
            current_concept_cumulative_answer="",
            recent_messages=""
        )

        # 添加历史与题目
        self.history_manager.add_messages(state=new_state,
                                          content=opening_speech,
                                          role="interviewer",
                                          concept=selected_concept)

        self.history_manager.q_id_add(state=new_state,
                                      q_id=q_id,
                                      question_brief=question_brief)

        session_store.save_state(req.id, new_state)
        warmup_task = asyncio.create_task(
            self._hydrate_session_context(
                state=new_state,
                resume_text=resume_text,
                job_domain=req.job,
            )
        )
        self._track_background_task(warmup_task)

        return {
            "id": req.id,
            "reply_speech": opening_speech,
            "mode": "single",
            "speaker_role": "ai",
        }
