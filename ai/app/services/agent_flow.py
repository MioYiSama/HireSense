import asyncio
from typing import Tuple, Optional, Dict
from app.models.schemas import AgentState, IntentResult, InterviewRoundLog
from app.core.history_manager import HistoryManager
from app.db import chroma_client,neo4j_client
from app.services import intent_router
from app.services import llm_generator
from app.services import evaluator
from app.services.llm_generator import Clarify,TacticalDecision


class AgentFlow:
    def __init__(self):
        self.intent_router = intent_router.IntentGateway()
        self.evaluator    = evaluator.Evaluator()
        self.chroma_client = chroma_client.ChromaClient()
        self.neo4j_client = neo4j_client.Neo4jClient("bolt://localhost:7687", "neo4j", "password")
        self.llm_gen     = llm_generator.LLMGenerator()
        self.history_manager = HistoryManager()
        self.strategy = evaluator.PruningStrategy()

    async def _async_generate_and_save_advice(self, state: AgentState, round_index: int, question: str,
                                              user_answer: str, std_answer: str, score: float):
        try:
            # 呼叫 LLM 拿到单题点评
            advice = await self.llm_gen.gen_single_advice(question=question,
                                                          user_ans=user_answer,
                                                          std_ans=std_answer,
                                                          score=score)  # 或者专属的 advice 提示词
            # 写回状态机
            state.score_logs[round_index].advice = advice
        except Exception as e:
            print(f"[Async Advice Error] 第 {round_index} 题点评生成失败: {e}")
            state.score_logs[round_index].advice = "暂无点评"

    async def process_turn(self, state : AgentState, user_text : str) -> str:
        #  记忆更新与切片 (Memory Management)
        self.history_manager.add_messages(state = state, content = user_text, role="interviewee", concept=state.current_concept)
        #  更新state中的recent_memory
        self.history_manager.add_track_memory(state=state)

        # 获取意图
        intent_res : IntentResult = await self.intent_router.analyze(current_topic=state.current_concept, user_text=user_text)
        # 获取当前的问题
        q_id, question_brief = self.history_manager.q_id_get(state=state)
        std_ans        = await self.chroma_client.async_get_standard_answer(q_id=q_id)

        # ---------------------------------------------------------
        # 分支 A:意图拦截 (非正常答题)
        # ---------------------------------------------------------
        if intent_res.intent == "Thinking":
            reply_speech = "没关系，你可以慢慢理一下思路。"
            self.history_manager.add_messages(state = state, content = reply_speech, role="interviewer", concept=state.current_concept)
            return reply_speech

        if intent_res.intent == "CLARIFY":
            res : Clarify = await self.llm_gen.clarify_question(user_text=user_text,current_topic=state.current_concept,
                                                                question_brief=question_brief,std_answer=std_ans,history=state.recent_messages)
            reply_speech = res.reply_speech
            self.history_manager.add_messages(state=state, content=reply_speech, role="interviewer",concept=state.current_concept)
            return reply_speech

        # ---------------------------------------------------------
        # 分支 B: 话题跃迁/追问问题
        # ---------------------------------------------------------
        align_concepts = await self.chroma_client.async_batch_align_concepts(raw_skills=intent_res.extracted_novel_concepts)
        final_concepts = await self.neo4j_client.verify_and_route_novel_concepts(concept_list=align_concepts)

        # 话题跃迁
        if intent_res.intent =="SHIFT":
            if final_concepts[0] == "No result":
                final_concepts = self.neo4j_client.get_icebreaker_concept(resume_concepts=state.resume_concept_list,
                                                                          visited_concepts=state.visited_concept)

            question_menu = await self.neo4j_client.get_batch_questions_brief(concept_list=final_concepts)

            res : TacticalDecision = await self.llm_gen.decide_tactics_and_generate(
                current_topic=state.current_concept,
                question_brief=question_brief,
                std_answer=std_ans,
                cumulative_answer=user_text,
                mastery_score=0.0,
                completed_rounds=len(state.interview_logs),
                current_turn=0,
                menu=question_menu,
                history=state.recent_messages,
                candidate_fact_sheet=state.candidate_fact_sheet,
                resume_star=state.resume_star,
                max_turn = state.MAX_probe_num
            )

            if res.action == "END":
                state.is_finished = True
                reply_speech = res.reply_speech
                self.history_manager.add_messages(state=state, content=reply_speech, role="interviewer",
                                                  concept=state.current_concept)
                return reply_speech

            if res.selected_node :
                state.current_concept = res.selected_node
                state.visited_concept.append(res.selected_node)
                state.probe_num = 0

            if res.q_id_and_brief:
                self.history_manager.q_id_add(state,res.q_id_and_brief[0],res.q_id_and_brief[1])

            reply_speech = res.reply_speech
            self.history_manager.add_messages(state=state, content=reply_speech, role="interviewer",concept=state.current_concept)
            return reply_speech

        # 正常回答
        if intent_res.intent =="ANSWER":
            menu_extend = []
            if final_concepts[0] != "No result":
                menu_extend = await self.neo4j_client.get_batch_questions_brief(concept_list=final_concepts)

            state.current_concept_cumulative_answer+= f" {user_text}"
            score_res = self.evaluator.evaluate_mastery(state.cumulative_answer, std_ans)
            m_score = score_res["mastery_score"]
            l_status = score_res["logic_status"]
            c_score = score_res["coverage_raw"]

            # 日志状态记录
            round_log = InterviewRoundLog(
                interviewer = question_brief,
                interviewee = user_text,
                standard_answer = std_ans or "",
                sts_coverage = c_score,
                nli_logic =  l_status,
                final_score =  m_score,
                async_advice = ""
            )

            state.interview_logs.append(round_log)
            current_round_index = len(state.interview_logs) - 1

            # 使用 asyncio.create_task 把任务丢进事件循环后台跑
            await asyncio.create_task(
                self._async_generate_and_save_advice(
                    state, current_round_index, state.current_topic, user_text, std_ans, m_score
                )
            )

            limit_fwd, limit_sib, limit_bwd = self.strategy.calculate_quota(m_score,l_status)

            menu = await self.neo4j_client.get_action_space_candidates(current_concept=state.current_concept,
                                                                 visited=state.visited_concept,
                                                                 resume_concepts=state.resume_concept_list,
                                                                 limit_fwd=limit_fwd,
                                                                 limit_bwd=limit_bwd,
                                                                 limit_sib=limit_sib
                                                                 )

            menu["扩展"]=menu_extend

            res: TacticalDecision = await self.llm_gen.decide_tactics_and_generate(
                current_topic=state.current_concept,
                question_brief=question_brief,
                std_answer=std_ans,
                cumulative_answer=state.current_concept_cumulative_answer,
                mastery_score=0.0,
                completed_rounds=len(state.interview_logs),
                current_turn=0,
                menu=menu,
                history=state.recent_messages,
                candidate_fact_sheet=state.candidate_fact_sheet,
                resume_star=state.resume_star,
                max_turn=state.MAX_probe_num
            )


            if res.action == "END":
                state.is_finished = True
                reply_speech = res.reply_speech
                self.history_manager.add_messages(state=state, content=reply_speech, role="interviewer",
                                                  concept=state.current_concept)
                return reply_speech

            if res.action == "TRANSITION":
                # 更新节点 追问归0
                if res.selected_node:
                    state.current_concept = res.selected_node
                    state.visited_concept.append(res.selected_node)
                    state.probe_num = 0
                # 更新题目
                if res.q_id_and_brief:
                    self.history_manager.q_id_add(state, res.q_id_and_brief[0], res.q_id_and_brief[1])
                # 更新历史,答案记录
                reply_speech = res.reply_speech
                state.current_concept_cumulative_answer = ""
                self.history_manager.add_messages(state=state, content=reply_speech, role="interviewer",
                                                  concept=state.current_concept)
                return reply_speech

            if res.action == "PROBE" :

                # 追问增加
                state.probe_num += 1
                # 更新历史
                reply_speech = res.reply_speech
                self.history_manager.add_messages(state=state, content=reply_speech, role="interviewer",
                                                  concept=state.current_concept)
                return reply_speech
























