import asyncio
import unittest

from app.core.history_manager import HistoryManager
from app.core.state_manager import session_store
from app.models.schemas import ParsedResume, StartRequest
from app.services.Agent_flows import AgentFlow


class BlockingResumeAnalyzer:
    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.completed = False

    async def analyze_and_align(
        self, resume_text: str, job_domain: str
    ) -> ParsedResume:
        self.started.set()
        await self.release.wait()
        self.completed = True
        return ParsedResume(
            core_skills=["Redis"],
            projects_star_summary="主导过高并发缓存与消息队列治理。",
            estimated_level="中级",
        )


class ImmediateResumeAnalyzer:
    async def analyze_and_align(
        self, resume_text: str, job_domain: str
    ) -> ParsedResume:
        return ParsedResume(
            core_skills=["Redis"],
            projects_star_summary="主导过高并发缓存与消息队列治理。",
            estimated_level="中级",
        )


class FakeChromaClient:
    async def async_batch_align_concepts(self, raw_skills, threshold: float = 0.5):
        return ["Redis"]


class FakeNeo4jClient:
    def __init__(self, basic_question=None):
        self.basic_question = basic_question
        self.random_basic_question_called = False
        self.random_basic_question_root_name = None
        self.icebreaker_called = False
        self.batch_called = False

    async def get_random_basic_question(self, root_name: str = "basis"):
        self.random_basic_question_called = True
        self.random_basic_question_root_name = root_name
        return self.basic_question

    async def get_icebreaker_concept(self, resume_concepts, visited_concepts):
        self.icebreaker_called = True
        return ["Redis"]

    async def get_batch_questions_brief(self, concept_list):
        self.batch_called = True
        return [
            {
                "concept": "Redis",
                "question_info": [
                    {"q_id": "redis-1", "brief": "介绍一下 Redis 的持久化机制"}
                ],
            }
        ]


class GuardLLMGenerator:
    async def generate_opening_speech(self, *args, **kwargs):
        raise AssertionError("fast start should not call generate_opening_speech")


class AgentFlowFastStartTest(unittest.IsolatedAsyncioTestCase):
    async def test_initialize_session_returns_before_resume_warmup_finishes(self):
        session_id = "fast-start-session"
        session_store.delete_state(session_id)

        resume_analyzer = BlockingResumeAnalyzer()
        neo4j_client = FakeNeo4jClient(
            basic_question={
                "concept": "Redis",
                "q_id": "redis-1",
                "brief": "介绍一下 Redis 的持久化机制",
            }
        )
        flow = AgentFlow(
            intent_router_=object(),
            evaluator_=object(),
            chroma_client_=FakeChromaClient(),
            neo4j_client_=neo4j_client,
            llm_gen=GuardLLMGenerator(),
            history_manager=HistoryManager(),
            strategy=object(),
            resume_analyzer=resume_analyzer,
        )

        try:
            result = await flow.initialize_session(
                StartRequest(
                    id=session_id,
                    job="backend",
                    personalization="偏简洁直接",
                    resume="熟悉 Redis、Kafka 与 MySQL。",
                )
            )

            self.assertEqual(
                result["reply_speech"],
                "我们按你偏好的节奏来，先从Redis开始。介绍一下 Redis 的持久化机制？",
            )
            self.assertFalse(resume_analyzer.completed)
            self.assertTrue(neo4j_client.random_basic_question_called)
            self.assertEqual(neo4j_client.random_basic_question_root_name, "basis")
            self.assertFalse(neo4j_client.icebreaker_called)
            self.assertFalse(neo4j_client.batch_called)

            state = session_store.get_state(session_id)
            self.assertEqual(state.resume_star, "")
            self.assertEqual(state.resume_concept_list, [])
            self.assertEqual(state.current_concept, "Redis")
            self.assertEqual(
                state.q_id_list,
                [["redis-1", "介绍一下 Redis 的持久化机制"]],
            )

            await asyncio.wait_for(resume_analyzer.started.wait(), timeout=1)
            resume_analyzer.release.set()
            await asyncio.wait_for(self._wait_for_resume_warmup(state), timeout=1)

            self.assertEqual(state.resume_star, "主导过高并发缓存与消息队列治理。")
            self.assertEqual(state.resume_concept_list, ["Redis"])
        finally:
            session_store.delete_state(session_id)

    async def test_initialize_session_falls_back_when_basic_question_pool_is_empty(
        self,
    ):
        session_id = "fast-start-fallback-session"
        session_store.delete_state(session_id)

        neo4j_client = FakeNeo4jClient(basic_question=None)
        flow = AgentFlow(
            intent_router_=object(),
            evaluator_=object(),
            chroma_client_=FakeChromaClient(),
            neo4j_client_=neo4j_client,
            llm_gen=GuardLLMGenerator(),
            history_manager=HistoryManager(),
            strategy=object(),
            resume_analyzer=ImmediateResumeAnalyzer(),
        )

        try:
            result = await flow.initialize_session(
                StartRequest(
                    id=session_id,
                    job="backend",
                    personalization="偏简洁直接",
                    resume="熟悉 Redis、Kafka 与 MySQL。",
                )
            )

            self.assertEqual(
                result["reply_speech"],
                "我们按你偏好的节奏来，先从Redis开始。介绍一下 Redis 的持久化机制？",
            )
            self.assertTrue(neo4j_client.random_basic_question_called)
            self.assertEqual(neo4j_client.random_basic_question_root_name, "basis")
            self.assertTrue(neo4j_client.icebreaker_called)
            self.assertTrue(neo4j_client.batch_called)

            state = session_store.get_state(session_id)
            self.assertEqual(state.current_concept, "Redis")
            self.assertEqual(
                state.q_id_list,
                [["redis-1", "介绍一下 Redis 的持久化机制"]],
            )
        finally:
            session_store.delete_state(session_id)

    async def test_initialize_session_uses_frontend_root_name_for_basic_question(self):
        session_id = "fast-start-frontend-session"
        session_store.delete_state(session_id)

        neo4j_client = FakeNeo4jClient(
            basic_question={
                "concept": "闭包",
                "q_id": "js-1",
                "brief": "说一下 JavaScript 闭包",
            }
        )
        flow = AgentFlow(
            intent_router_=object(),
            evaluator_=object(),
            chroma_client_=FakeChromaClient(),
            neo4j_client_=neo4j_client,
            llm_gen=GuardLLMGenerator(),
            history_manager=HistoryManager(),
            strategy=object(),
            resume_analyzer=ImmediateResumeAnalyzer(),
        )

        try:
            await flow.initialize_session(
                StartRequest(
                    id=session_id,
                    job="frontend",
                    personalization="偏简洁直接",
                    resume="熟悉 JavaScript、React 与工程化。",
                )
            )

            self.assertTrue(neo4j_client.random_basic_question_called)
            self.assertEqual(
                neo4j_client.random_basic_question_root_name, "04-JavaScript基础"
            )
        finally:
            session_store.delete_state(session_id)

    async def _wait_for_resume_warmup(self, state):
        while state.resume_star == "":
            await asyncio.sleep(0)
