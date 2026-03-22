import asyncio
from typing import Tuple, Optional, Dict
from app.models.schemas import AgentState, IntentResult, InterviewRoundLog, StartRequest, ParsedResume
from app.core.history_manager import HistoryManager
from app.db import chroma_client, neo4j_client
from app.services import intent_router, llm_generator, evaluator
from app.services.llm_generator import Clarify, TacticalDecision, StartInterview
from app.services.resume_analyzer import ResumeAnalyzer
from app.core.state_manager import session_store


class AgentFlow:
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

    async def _async_generate_and_save_advice(self, state: AgentState, round_index: int, question: str,
                                              user_answer: str, std_answer: str, score: float):
        try:
            advice = await self.llm_gen.gen_single_advice(question, user_answer, std_answer, score)
            state.interview_logs[round_index].async_advice = advice
        except Exception as e:
            print(f"[Async Advice Error] 第 {round_index} 题点评生成失败: {e}")
            state.interview_logs[round_index].async_advice = "暂无点评"

    async def process_turn(self, state: AgentState, user_text: str) -> str:
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
            return reply_speech

        if intent_res.intent == "CLARIFY":
            res: Clarify = await self.llm_gen.clarify_question(
                user_text=user_text, current_topic=state.current_concept,
                question_brief=question_brief, std_answer=std_ans, history=state.recent_messages
            )
            self.history_manager.add_messages(state=state, content=res.reply_speech, role="interviewer",
                                              concept=state.current_concept)
            return res.reply_speech

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
                current_turn=state.probe_num,
                menu=question_menu,
                history=state.recent_messages,
                candidate_fact_sheet=state.candidate_fact_sheet,
                resume_star=state.resume_star,
                max_turn=state.MAX_probe_num
            )

            # 执行转移状态清理
            self._execute_transition(state, res)
            return res.reply_speech

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

            score_res = self.evaluator.evaluate_mastery(state.current_concept_cumulative_answer, std_ans)

            # 防御性检查：确保 score_res 是字典
            if not isinstance(score_res, dict):
                print(f"[Warning] evaluate_mastery returned non-dict: {type(score_res)}, {score_res}")
                score_res = {"mastery_score": 0.0, "logic_status": "Neutral", "coverage_raw": 0.0}

            m_score, l_status, c_score = score_res["mastery_score"], score_res["logic_status"], score_res["coverage_raw"]

            # 3. 记录日志，供最终出表用
            round_log = InterviewRoundLog(
                interviewer=question_brief, interviewee=user_text,
                sts_coverage=c_score, nli_logic=l_status, final_score=m_score, async_advice=""
            )
            state.interview_logs.append(round_log)
            current_round_index = len(state.interview_logs) - 1

            # 4. 【核心修复】：真正的非阻塞后台任务触发
            task = asyncio.create_task(
                self._async_generate_and_save_advice(state, current_round_index, state.current_concept, user_text,
                                                     std_ans, m_score)
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)  # 执行完毕后自动清理引用

            # 5. 图谱菜单剪枝 (结合真实分数)
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

            # 6. LLM 中枢决断 (传入真实的 m_score)
            res: TacticalDecision = await self.llm_gen.decide_tactics_and_generate(
                current_topic=state.current_concept,
                question_brief=question_brief,
                std_answer=std_ans,
                cumulative_answer=state.current_concept_cumulative_answer,
                mastery_score=m_score,
                current_turn=state.probe_num,
                menu=menu,
                history=state.recent_messages,
                candidate_fact_sheet=state.candidate_fact_sheet,
                resume_star=state.resume_star,
                max_turn=state.MAX_probe_num
            )

            # 7. 状态机推进
            if res.action == "TRANSITION":
                self._execute_transition(state, res)
            elif res.action == "PROBE":
                state.probe_num += 1
                self.history_manager.add_messages(state=state, content=res.reply_speech, role="interviewer",
                                                  concept=state.current_concept)

            return res.reply_speech

    # ==========================================
    # 辅助私有方法
    # ==========================================
    def _execute_transition(self, state: AgentState, res: TacticalDecision):
        """统一封装状态跳转逻辑，保持主流程整洁"""
        if res.selected_node:
            state.current_concept = res.selected_node
            state.visited_concept.append(res.selected_node)
            state.probe_num = 0
            state.current_concept_cumulative_answer = ""  # 清空上题的累积回答

        if res.q_id_and_brief:
            # 你在模型里返回了元组 [q_id, brief]，这里更新题目游标
            self.history_manager.q_id_add(state, res.q_id_and_brief[0], res.q_id_and_brief[1])

        self.history_manager.add_messages(state=state, content=res.reply_speech, role="interviewer",
                                          concept=state.current_concept)

    async def initialize_session(self, req: StartRequest) -> dict:
        #  简历解析与对齐
        resume : ParsedResume = await self.resume_analyzer.analyze_and_align(resume_text=req.resume, job_domain=req.job)
        core_skills = resume.core_skills
        resume_star = resume.projects_star_summary

        # core_skills 对齐为图谱中节点
        align_concepts = await self.chroma_client.async_batch_align_concepts(core_skills)

        # 图谱启动得到题目表单
        final_concepts = await self.neo4j_client.get_icebreaker_concept(resume_concepts=align_concepts, visited_concepts=[])
        question_menu = await self.neo4j_client.get_batch_questions_brief(concept_list=final_concepts)

        start_interview : StartInterview = await self.llm_gen.generate_opening_speech(
            personalization=req.personalization,
            projects_star=resume_star,
            question_menu=question_menu
        )

        # 创建状态
        new_state = AgentState(
            session_id=req.id,
            job=req.job,
            personalization=req.personalization,
            resume_star=resume_star,
            resume_concept_list=align_concepts,
            current_concept=start_interview.selected_node,
            visited_concept=[start_interview.selected_node],
            q_id_list=[],
            new_concept_list=[],
            chat_history=[],
            interview_logs=[],
            candidate_fact_sheet=[],
            current_concept_cumulative_answer="",
            recent_messages=""
        )

        # 添加历史与题目
        self.history_manager.add_messages(state=new_state,
                                          content=start_interview.reply_speech,
                                          role="interviewer",
                                          concept=start_interview.selected_node)

        self.history_manager.q_id_add(state=new_state,
                                      q_id=start_interview.q_id_and_brief[0],
                                      question_brief=start_interview.q_id_and_brief[1])

        session_store.save_state(req.id, new_state)

        return {
            "id": req.id,
            "reply_speech": start_interview.reply_speech
        }
