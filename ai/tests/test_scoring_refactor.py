import asyncio
import unittest

from app.core.history_manager import HistoryManager
from app.models.schemas import AgentState, IntentResult, InterviewRoundLog, ScoreBreakdown
from app.services.Agent_flows import AgentFlow
from app.services.evaluator import Evaluator
from app.services.report_generator import FinalReport


class FakeIntentRouter:
    def __init__(self, results):
        self._results = list(results)

    async def analyze(self, current_topic: str, user_text: str):
        return self._results.pop(0)


class FakeEvaluator:
    def __init__(self, results):
        self._results = list(results)

    def evaluate_mastery(self, user_answer: str, standard_answer: str):
        return self._results.pop(0)


class FakeChromaClient:
    async def async_get_standard_answer(self, q_id: str):
        return "先说原理，再说取舍，再说边界。"

    async def async_batch_align_concepts(self, raw_skills, threshold: float = 0.5):
        return []


class FakeNeo4jClient:
    async def get_action_space_candidates(self, **kwargs):
        return {
            "问题平移": [
                {
                    "concept": "MySQL",
                    "question_info": [{"q_id": "mysql-2", "brief": "介绍一下 MySQL 索引"}],
                }
            ]
        }

    async def get_batch_questions_brief(self, concept_list):
        return [
            {
                "concept": "MySQL",
                "question_info": [{"q_id": "mysql-2", "brief": "介绍一下 MySQL 索引"}],
            }
        ]

    async def verify_and_route_novel_concepts(self, concept_list):
        return ["No result"]

    async def get_icebreaker_concept(self, resume_concepts, visited_concepts):
        return ["MySQL"]


class FakeLLMGenerator:
    def __init__(self, decisions):
        self._decisions = list(decisions)

    async def gen_single_advice(self, **kwargs):
        return "能回答主线，但深度和边界不足。"

    async def decide_tactics_and_generate(self, **kwargs):
        return self._decisions.pop(0)


class NoopResumeAnalyzer:
    async def analyze_and_align(self, resume_text: str, job_domain: str):
        raise AssertionError("resume analyzer should not be called in this test")


class FakeStrategy:
    @staticmethod
    def calculate_quota(mastery_score: float, logic_status: str):
        return 1, 1, 1


class FakeStsModel:
    def predict(self, pairs):
        return [0.1]


class FakeNliModel:
    def __init__(self, logits):
        self._logits = logits

    def predict(self, pairs):
        return [self._logits]


class FakeStructuredLLM:
    def __init__(self, payload):
        self.payload = payload

    async def ainvoke(self, prompt):
        return self.payload


class FakeNarrativeLLM:
    def with_structured_output(self, model_class):
        return FakeStructuredLLM(
            model_class(
                feedback="整体表现中等，能答主线，但深度不稳定。",
                shortcomings=["底层原理不够扎实", "边界条件覆盖不足", "细节展开不够稳定"],
                advice="建议把高频题拆成原理、实现、边界三段式复盘。",
                urls=["MySQL索引详解  https://example.com/mysql"],
            )
        )


class FakeAdvancedNeo4jClient(FakeNeo4jClient):
    async def get_action_space_candidates(self, **kwargs):
        return {
            "问题深入": [
                {
                    "concept": "Redis 事务",
                    "question_info": [{"q_id": "redis-3", "brief": "Redis 事务和 Lua 脚本怎么取舍"}],
                }
            ]
        }


def build_state() -> AgentState:
    state = AgentState(
        session_id="score-state",
        job="backend",
        personalization="",
        resume_star="做过电商交易链路。",
        resume_concept_list=["Redis", "MySQL"],
        q_id_list=[["redis-1", "介绍一下 Redis 持久化机制"]],
        new_concept_list=[],
        chat_history=[],
        current_concept="Redis",
        visited_concept=["Redis"],
        visited_question=[],
        interview_logs=[],
        probe_num=0,
        MAX_probe_num=3,
        current_concept_cumulative_answer="",
        recent_messages="",
        candidate_fact_sheet=[],
    )
    HistoryManager.add_messages(state, "介绍一下 Redis 持久化机制？", "interviewer", "Redis")
    return state


class AgentFlowScoringRefactorTest(unittest.IsolatedAsyncioTestCase):
    async def test_first_answer_cannot_end_entire_interview(self):
        state = build_state()
        flow = AgentFlow(
            intent_router_=FakeIntentRouter(
                [IntentResult(intent="ANSWER", extracted_novel_concepts=[])]
            ),
            evaluator_=FakeEvaluator(
                [
                    {
                        "mastery_score": 66.0,
                        "logic_status": "Entailment",
                        "coverage_raw": 70.0,
                        "coverage_score": 70.0,
                        "consistency_score": 82.0,
                        "completeness_score": 55.0,
                        "nli_probs": {"Entailment": 0.7, "Neutral": 0.2, "Contradiction": 0.1},
                        "missing_points": ["边界条件"],
                        "reason_tags": ["核心方向基本对齐", "逻辑基本自洽", "关键点覆盖不足"],
                    }
                ]
            ),
            chroma_client_=FakeChromaClient(),
            neo4j_client_=FakeNeo4jClient(),
            llm_gen=FakeLLMGenerator(
                [
                    type(
                        "Decision",
                        (),
                        {
                            "action": "END",
                            "reply_speech": "这场面试到这里就可以结束了。",
                            "selected_node": None,
                            "q_id_and_brief": None,
                        },
                    )()
                ]
            ),
            history_manager=HistoryManager(),
            strategy=FakeStrategy(),
            resume_analyzer=NoopResumeAnalyzer(),
        )

        result = await flow.process_turn(state, "Redis 有 RDB 和 AOF，也知道各自优缺点。")
        await asyncio.sleep(0)

        self.assertFalse(result.ending)
        self.assertIn("MySQL", result.reply_speech)
        self.assertEqual(len(state.interview_logs), 1)
        self.assertFalse(state.is_finished)
        self.assertEqual(state.current_concept, "MySQL")
        self.assertEqual(state.q_id_list[-1], ["mysql-2", "介绍一下 MySQL 索引"])

    async def test_repeated_poor_answers_can_end_interview(self):
        state = build_state()
        state.interview_logs = [
            InterviewRoundLog(
                q_id="redis-old-1",
                concept="Redis",
                difficulty_label="basic",
                interviewer="Redis 为什么快？",
                interviewee="没答上来。",
                sts_coverage=20.0,
                nli_logic="Neutral",
                nli_probs={},
                score_breakdown=ScoreBreakdown(coverage_score=20.0, consistency_score=40.0, completeness_score=10.0),
                missing_points=["内存模型"],
                reason_tags=["与标答覆盖偏低"],
                probe_count=1,
                final_score=28.0,
                async_advice="核心原理没有答到。",
            ),
            InterviewRoundLog(
                q_id="redis-old-2",
                concept="MySQL",
                difficulty_label="intermediate",
                interviewer="MySQL 索引什么时候失效？",
                interviewee="也没答上来。",
                sts_coverage=18.0,
                nli_logic="Neutral",
                nli_probs={},
                score_breakdown=ScoreBreakdown(coverage_score=18.0, consistency_score=35.0, completeness_score=12.0),
                missing_points=["最左前缀"],
                reason_tags=["与标答覆盖偏低"],
                probe_count=1,
                final_score=32.0,
                async_advice="索引失效场景没有答到。",
            ),
        ]

        flow = AgentFlow(
            intent_router_=FakeIntentRouter(
                [IntentResult(intent="ANSWER", extracted_novel_concepts=[])]
            ),
            evaluator_=FakeEvaluator(
                [
                    {
                        "mastery_score": 30.0,
                        "logic_status": "Neutral",
                        "coverage_raw": 28.0,
                        "coverage_score": 28.0,
                        "consistency_score": 45.0,
                        "completeness_score": 20.0,
                        "nli_probs": {"Entailment": 0.1, "Neutral": 0.8, "Contradiction": 0.1},
                        "missing_points": ["核心原理"],
                        "reason_tags": ["与标答覆盖偏低", "关键点覆盖不足"],
                    }
                ]
            ),
            chroma_client_=FakeChromaClient(),
            neo4j_client_=FakeNeo4jClient(),
            llm_gen=FakeLLMGenerator(
                [
                    type(
                        "Decision",
                        (),
                        {
                            "action": "END",
                            "reply_speech": "这场面试先到这里。",
                            "selected_node": None,
                            "q_id_and_brief": None,
                        },
                    )()
                ]
            ),
            history_manager=HistoryManager(),
            strategy=FakeStrategy(),
            resume_analyzer=NoopResumeAnalyzer(),
        )

        result = await flow.process_turn(state, "这个我不太会。")
        await asyncio.sleep(0)

        self.assertTrue(result.ending)
        self.assertTrue(state.is_finished)
        self.assertEqual(len(state.interview_logs), 3)

    async def test_high_scores_without_advanced_question_cannot_end(self):
        state = build_state()
        state.interview_logs = [
            InterviewRoundLog(
                q_id="redis-old-1",
                concept="Redis",
                difficulty_label="basic",
                interviewer="Redis 为什么快？",
                interviewee="回答得比较完整。",
                sts_coverage=88.0,
                nli_logic="Entailment",
                nli_probs={},
                score_breakdown=ScoreBreakdown(coverage_score=88.0, consistency_score=90.0, completeness_score=82.0),
                missing_points=[],
                reason_tags=["核心方向基本对齐", "回答较完整"],
                probe_count=1,
                final_score=86.0,
                async_advice="回答完整。",
            ),
            InterviewRoundLog(
                q_id="mysql-old-2",
                concept="MySQL",
                difficulty_label="intermediate",
                interviewer="MySQL 索引原理？",
                interviewee="回答得比较完整。",
                sts_coverage=86.0,
                nli_logic="Entailment",
                nli_probs={},
                score_breakdown=ScoreBreakdown(coverage_score=86.0, consistency_score=89.0, completeness_score=80.0),
                missing_points=[],
                reason_tags=["核心方向基本对齐", "回答较完整"],
                probe_count=1,
                final_score=84.0,
                async_advice="回答完整。",
            ),
        ]
        state.current_question_difficulty = "basic"

        flow = AgentFlow(
            intent_router_=FakeIntentRouter(
                [IntentResult(intent="ANSWER", extracted_novel_concepts=[])]
            ),
            evaluator_=FakeEvaluator(
                [
                    {
                        "mastery_score": 88.0,
                        "logic_status": "Entailment",
                        "coverage_raw": 90.0,
                        "coverage_score": 90.0,
                        "consistency_score": 92.0,
                        "completeness_score": 84.0,
                        "nli_probs": {"Entailment": 0.85, "Neutral": 0.1, "Contradiction": 0.05},
                        "missing_points": [],
                        "reason_tags": ["核心方向基本对齐", "回答较完整"],
                    }
                ]
            ),
            chroma_client_=FakeChromaClient(),
            neo4j_client_=FakeNeo4jClient(),
            llm_gen=FakeLLMGenerator(
                [
                    type(
                        "Decision",
                        (),
                        {
                            "action": "END",
                            "reply_speech": "我觉得已经够了，可以结束。",
                            "selected_node": None,
                            "q_id_and_brief": None,
                        },
                    )()
                ]
            ),
            history_manager=HistoryManager(),
            strategy=FakeStrategy(),
            resume_analyzer=NoopResumeAnalyzer(),
        )

        result = await flow.process_turn(state, "我再补充一下 Redis 的持久化和恢复路径。")
        await asyncio.sleep(0)

        self.assertFalse(result.ending)
        self.assertFalse(state.is_finished)
        self.assertEqual(state.current_concept, "MySQL")
        self.assertEqual(state.q_id_list[-1], ["mysql-2", "介绍一下 MySQL 索引"])

    async def test_question_is_finalized_once_after_probe_chain(self):
        state = build_state()
        flow = AgentFlow(
            intent_router_=FakeIntentRouter(
                [
                    IntentResult(intent="ANSWER", extracted_novel_concepts=[]),
                    IntentResult(intent="ANSWER", extracted_novel_concepts=[]),
                ]
            ),
            evaluator_=FakeEvaluator(
                [
                    {
                        "mastery_score": 58.0,
                        "logic_status": "Neutral",
                        "coverage_raw": 62.0,
                        "coverage_score": 62.0,
                        "consistency_score": 68.0,
                        "completeness_score": 46.0,
                        "nli_probs": {"Entailment": 0.3, "Neutral": 0.6, "Contradiction": 0.1},
                        "missing_points": ["边界条件"],
                        "reason_tags": ["核心方向基本对齐", "关键点覆盖不足"],
                    },
                    {
                        "mastery_score": 74.0,
                        "logic_status": "Entailment",
                        "coverage_raw": 78.0,
                        "coverage_score": 78.0,
                        "consistency_score": 88.0,
                        "completeness_score": 63.0,
                        "nli_probs": {"Entailment": 0.8, "Neutral": 0.15, "Contradiction": 0.05},
                        "missing_points": ["极端场景"],
                        "reason_tags": ["核心方向基本对齐", "逻辑基本自洽", "关键点覆盖不足"],
                    },
                ]
            ),
            chroma_client_=FakeChromaClient(),
            neo4j_client_=FakeNeo4jClient(),
            llm_gen=FakeLLMGenerator(
                [
                    type(
                        "Decision",
                        (),
                        {
                            "action": "PROBE",
                            "reply_speech": "再补一下 AOF 和 RDB 的取舍。",
                            "selected_node": None,
                            "q_id_and_brief": None,
                        },
                    )(),
                    type(
                        "Decision",
                        (),
                        {
                            "action": "TRANSITION",
                            "reply_speech": "这题先到这，我们切到 MySQL 索引。",
                            "selected_node": "MySQL",
                            "q_id_and_brief": ["mysql-2", "介绍一下 MySQL 索引"],
                        },
                    )(),
                ]
            ),
            history_manager=HistoryManager(),
            strategy=FakeStrategy(),
            resume_analyzer=NoopResumeAnalyzer(),
        )

        first = await flow.process_turn(state, "Redis 有 RDB 和 AOF。")
        self.assertEqual(first.reply_speech, "再补一下 AOF 和 RDB 的取舍。")
        self.assertEqual(len(state.interview_logs), 0)
        self.assertEqual(state.probe_num, 1)

        second = await flow.process_turn(state, "RDB 恢复快，AOF 数据更完整。")
        await asyncio.sleep(0)

        self.assertEqual(second.reply_speech, "这题先到这，我们切到 MySQL 索引。")
        self.assertEqual(len(state.interview_logs), 1)
        self.assertEqual(state.current_concept, "MySQL")
        self.assertEqual(state.probe_num, 0)
        self.assertEqual(state.current_concept_cumulative_answer, "")

        log = state.interview_logs[0]
        self.assertEqual(log.q_id, "redis-1")
        self.assertEqual(log.concept, "Redis")
        self.assertEqual(log.final_score, 74.0)
        self.assertEqual(log.probe_count, 2)
        self.assertIn("Redis 有 RDB 和 AOF。", log.interviewee)
        self.assertIn("RDB 恢复快，AOF 数据更完整。", log.interviewee)
        self.assertEqual(log.score_breakdown.coverage_score, 78.0)
        self.assertEqual(log.async_advice, "能回答主线，但深度和边界不足。")


class EvaluatorRefactorTest(unittest.TestCase):
    def test_contradiction_answer_no_longer_collapses_to_zero(self):
        evaluator = Evaluator(
            sts_model=FakeStsModel(),
            nli_model=FakeNliModel([0.2, 0.3, 2.0]),
        )

        result = evaluator.evaluate_mastery(
            user_answer="HashMap 是线程安全的，多线程可以直接用。",
            standard_answer="HashMap 线程不安全，多线程下应该使用 ConcurrentHashMap。",
        )

        self.assertGreater(result["mastery_score"], 0.0)
        self.assertLessEqual(result["mastery_score"], 55.0)
        self.assertIn("存在逻辑冲突", result["reason_tags"])
        self.assertTrue(isinstance(result["missing_points"], list))


class ReportAggregationTest(unittest.IsolatedAsyncioTestCase):
    async def test_report_uses_machine_aggregated_dimension_scores(self):
        state = AgentState(
            session_id="report-state",
            job="backend",
            personalization="",
            resume_star="负责支付链路与缓存治理。",
            resume_concept_list=["Redis", "MySQL", "API"],
            q_id_list=[],
            new_concept_list=[],
            chat_history=[],
            current_concept="API",
            visited_concept=["Redis", "MySQL", "API"],
            visited_question=[],
            interview_logs=[
                InterviewRoundLog(
                    q_id="db-1",
                    concept="MySQL",
                    interviewer="MySQL 索引失效有哪些场景？",
                    interviewee="说到了联合索引和最左前缀，但没有系统展开。",
                    sts_coverage=52.0,
                    nli_logic="Neutral",
                    nli_probs={"Entailment": 0.2, "Neutral": 0.7, "Contradiction": 0.1},
                    score_breakdown=ScoreBreakdown(
                        coverage_score=52.0,
                        consistency_score=68.0,
                        completeness_score=42.0,
                    ),
                    missing_points=["回表代价", "范围查询影响"],
                    reason_tags=["回答偏概念化", "关键点覆盖不足"],
                    probe_count=1,
                    final_score=40.0,
                    async_advice="索引主线提到了，但深度不够。",
                ),
                InterviewRoundLog(
                    q_id="redis-2",
                    concept="Redis 分布式锁",
                    interviewer="如何设计 Redis 分布式锁？",
                    interviewee="能讲出加锁解锁，但边界条件讲得不完整。",
                    sts_coverage=65.0,
                    nli_logic="Entailment",
                    nli_probs={"Entailment": 0.75, "Neutral": 0.2, "Contradiction": 0.05},
                    score_breakdown=ScoreBreakdown(
                        coverage_score=65.0,
                        consistency_score=83.0,
                        completeness_score=58.0,
                    ),
                    missing_points=["续期", "主从切换风险"],
                    reason_tags=["核心方向基本对齐", "关键点覆盖不足"],
                    probe_count=2,
                    final_score=60.0,
                    async_advice="分布式锁主线正确，但极端场景缺失。",
                ),
                InterviewRoundLog(
                    q_id="api-3",
                    concept="API 设计",
                    interviewer="接口幂等一般怎么设计？",
                    interviewee="知道 token 和去重表方案，但没有讲清失败补偿。",
                    sts_coverage=58.0,
                    nli_logic="Entailment",
                    nli_probs={"Entailment": 0.7, "Neutral": 0.2, "Contradiction": 0.1},
                    score_breakdown=ScoreBreakdown(
                        coverage_score=58.0,
                        consistency_score=79.0,
                        completeness_score=54.0,
                    ),
                    missing_points=["重试窗口", "补偿策略"],
                    reason_tags=["核心方向基本对齐", "回答较完整"],
                    probe_count=1,
                    final_score=50.0,
                    async_advice="幂等方案答到了，但补偿链路没展开。",
                ),
            ],
            probe_num=0,
            MAX_probe_num=3,
            current_concept_cumulative_answer="",
            recent_messages="",
            candidate_fact_sheet=[],
        )

        report = await FinalReport(llm=FakeNarrativeLLM()).build_report(state)

        self.assertEqual(report.score, 50.0)
        self.assertAlmostEqual(report.specific["数据库"], 4.0, places=1)
        self.assertAlmostEqual(report.specific["分布式"], 6.0, places=1)
        self.assertAlmostEqual(report.specific["API"], 5.0, places=1)
        self.assertLessEqual(max(report.general.values()), 6.5)
        self.assertLessEqual(max(report.specific.values()), 6.8)
        self.assertEqual(report.reviews[0].concept, "MySQL")
        self.assertTrue(report.reviews[1].reason_tags)
        self.assertEqual(report.resources, ["MySQL索引详解  https://example.com/mysql"])
