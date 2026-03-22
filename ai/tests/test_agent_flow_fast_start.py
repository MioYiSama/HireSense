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

    async def analyze_and_align(self, resume_text: str, job_domain: str) -> ParsedResume:
        self.started.set()
        await self.release.wait()
        self.completed = True
        return ParsedResume(
            core_skills=["Redis"],
            projects_star_summary="主导过高并发缓存与消息队列治理。",
            estimated_level="中级",
        )


class FakeChromaClient:
    async def async_batch_align_concepts(self, raw_skills, threshold: float = 0.5):
        return ["Redis"]


class FakeNeo4jClient:
    async def get_icebreaker_concept(self, resume_concepts, visited_concepts):
        return ["Redis"]

    async def get_batch_questions_brief(self, concept_list):
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
        flow = AgentFlow(
            intent_router_=object(),
            evaluator_=object(),
            chroma_client_=FakeChromaClient(),
            neo4j_client_=FakeNeo4jClient(),
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

    async def _wait_for_resume_warmup(self, state):
        while state.resume_star == "":
            await asyncio.sleep(0)
