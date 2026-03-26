from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# ==================================
# POST /api/interview/start
# ==================================
class StartRequest(BaseModel):
    id: str = Field(description="面试会议唯一id")
    job: Literal["backend", "frontend"] = Field(
        description="可选类 只有backend和frontend"
    )
    mode: Literal["single", "panel_trio"] = Field(
        default="single",
        description="面试模式，single 为单面试官，panel_trio 为 HR+技术主管+大老板 群面",
    )
    personalization: Optional[str] = Field(
        default=None,
        description="用户倾向风格",
    )
    resume: Optional[str] = Field(
        default=None,
        description="简历信息",
    )


class StartPayload(BaseModel):
    reply: str = Field(description="Agent生成的首轮回复话术")
    mode: Literal["single", "panel_trio"] = Field(default="single")
    speaker_role: Literal["ai", "hr", "tech_lead", "executive"] = Field(
        default="ai"
    )


class StartResponse(BaseModel):
    success: bool
    data: StartPayload


# ==========================================
# 2. /api/interview/reply 接口模型 (多模态输入适配)
# ==========================================
class TextInput(BaseModel):
    type: Literal["text"]
    content: str = Field(description="用户回答")


class SingleWord(BaseModel):
    word: str = Field(description="后端传来的单个字解析")
    start: float = Field(description="说出该单字的开始时间")
    end: float = Field(description="该字的结束时间")


class Segments(BaseModel):
    start: float = Field(description="该段文字切片的开始时间")
    end: float = Field(description="该段文字切片的结束时间")
    text: str = Field(description="该段文字切片的内容")
    words: List[SingleWord]


class TranscriptContent(BaseModel):
    duration: float = Field(description="用户说完回答的总时间")
    text: str = Field(description="用户的回答内容")
    segments: List[Segments]


class TranscriptInput(BaseModel):
    type: Literal["transcript"]
    content: TranscriptContent


class ReplyRequest(BaseModel):
    id: str
    input: Union[TranscriptInput, TextInput] = Field(discriminator="type")


class ReplyResponse(BaseModel):
    reply: str = Field(description="Agent生成的回复话术")
    ending: bool = Field(description="面试官是否认为本场面试已经可以结束")
    mode: Literal["single", "panel_trio"] = Field(default="single")
    speaker_role: Literal["ai", "hr", "tech_lead", "executive"] = Field(
        default="ai"
    )


# ==========================================
# 3. /api/interview/stop
# ==========================================
class StopRequest(BaseModel):
    id: str


class StopResponse(BaseModel):
    success: bool


# ==========================================
# 4. /api/interview/report
# ==========================================
class ScoreBreakdown(BaseModel):
    coverage_score: float = 0.0
    consistency_score: float = 0.0
    completeness_score: float = 0.0


class DimensionDetail(BaseModel):
    score: float = 0.0
    summary: str = ""
    strength_points: List[str] = Field(default_factory=list)
    missing_points: List[str] = Field(default_factory=list)


class ReviewItem(BaseModel):
    interviewer: str = Field(description="面试官问题")
    interviewer_role: Literal["ai", "hr", "tech_lead", "executive"] = Field(
        default="ai", description="发起该题的面试官角色"
    )
    interviewee: str = Field(description="用户回答")
    score: float = Field(description="大模型评估与本地聚合后的最终评分")
    advice: str
    concept: Optional[str] = Field(default=None, description="当前题目的考点")
    difficulty_label: str = Field(default="unknown", description="当前题目的难度标签")
    score_breakdown: ScoreBreakdown = Field(
        default_factory=ScoreBreakdown, description="题级分项得分"
    )
    reason_tags: List[str] = Field(
        default_factory=list, description="支持该分数的机器标签"
    )
    strength_points: List[str] = Field(
        default_factory=list, description="本题回答中做得好的点"
    )
    missing_points: List[str] = Field(
        default_factory=list, description="本题回答中缺失的点"
    )
    score_rationale: str = Field(
        default="", description="对题级分数的结构化解释"
    )


class ReportContent(BaseModel):
    job: Literal["backend", "frontend"]
    mode: Literal["single", "panel_trio"] = Field(default="single")
    score: float
    general: Dict[str, float]
    general_details: Dict[str, DimensionDetail] = Field(default_factory=dict)
    specific: Dict[str, float]
    specific_details: Dict[str, DimensionDetail] = Field(default_factory=dict)
    feedback: str
    shortcomings: List[str]
    advice: str
    resources: List[str]
    reviews: List[ReviewItem]


class ReportPushRequest(BaseModel):
    id: str
    secret: str
    report: ReportContent


# ==========================================
# Agent State
# ==========================================


class InterviewRoundLog(BaseModel):
    q_id: str = ""  # 当前题目的唯一标识
    question_type: Literal["technical", "behavioral", "executive"] = "technical"
    concept: str = ""  # 当前题目考察的核心概念
    difficulty_label: str = "unknown"  # 当前题目的难度标签
    interviewer_role: Literal["ai", "hr", "tech_lead", "executive"] = "ai"
    interviewer: str  # 考官提问
    interviewee: str  # 用户的回答
    sts_coverage: float  # CrossEncoder 算出的覆盖率
    nli_logic: str  # NLI 算出的逻辑状态 (Entailment/Contradiction/Neutral)
    nli_probs: Dict[str, float] = Field(default_factory=dict)  # NLI 全量概率
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    strength_points: List[str] = Field(default_factory=list)  # 回答中的亮点
    missing_points: List[str] = Field(default_factory=list)  # 未覆盖的关键点
    reason_tags: List[str] = Field(default_factory=list)  # 机器标签，用于解释分数
    score_rationale: str = ""  # 题级得分解释
    probe_count: int = 1  # 同一题被追问的轮数
    final_score: float  # 融合打分公式算出的本题最终得分
    async_advice: str = ""  # 【后台异步写入】LLM 对这一轮的评价


class ChatMessage(BaseModel):
    role: Literal[
        "ai", "hr", "tech_lead", "executive", "interviewer", "interviewee"
    ]
    content: str
    concept: Optional[str]
    num_token: int


class AgentState(BaseModel):
    # 基础信息区
    session_id: str
    job: str
    mode: Literal["single", "panel_trio"] = "single"
    personalization: str
    resume_star: str = ""  # 从 start 接口异步提取出的 STAR 简历信息
    resume_concept_list: List[str]  # 从简历中分析出来的用户擅长的领域 实现个性化处理

    # 对话历史区
    q_id_list: List[List[str]]  # 提出的所有问题的id和内容
    new_concept_list: List[str]  # 用户回答中带有的新的概念 用于深层追问
    chat_history: List[ChatMessage]

    # 图谱路由控制区
    current_concept: Optional[str] = None
    current_interviewer_role: Literal["ai", "hr", "tech_lead", "executive"] = "ai"
    current_question_type: Literal["technical", "behavioral", "executive"] = (
        "technical"
    )
    current_question_standard_answer: str = ""
    visited_concept: List[str] = []
    visited_question: List[str] = []  # q_id 作为识别标签
    panel_turn_index: int = 0
    panel_round_counts: Dict[str, int] = Field(default_factory=dict)

    # 全局评分路由控制区
    interview_logs: List[InterviewRoundLog]

    # 同问题追问控制区
    probe_num: int = 0
    MAX_probe_num: int = 3
    current_question_difficulty: str = "unknown"
    current_concept_cumulative_answer: (
        str  # 用于对于多次追问时 答案的拼接 用来最终形成准确答案
    )

    # 历史管理区
    recent_messages: str  # 最近几期的回答(如果concept相同，则一定提取，若concept更换，则只提取1000tokens）
    candidate_fact_sheet: List[str]  # 全局历史概要收集

    # 面试状态控制
    is_finished: bool = False  # 面试是否已结束


# 意图识别数据模型区
class IntentResult(BaseModel):
    # 1. 核心动作分类 (Action Classification)
    intent: Literal["ANSWER", "SHIFT", "CLARIFY", "THINKING"] = Field(
        description="""判定用户当前发言的核心意图：
        - ANSWER: 正常答题（无论答得对错）。
        - SHIFT: 明确表示不会、忘了，或者要求转移话题。
        - CLARIFY: 请求面试官重复问题或解释题意。
        - THINKING: 仅使用语气词拖延时间（如'让我想想'、'呃...'）。"""
    )

    # 2. 新知识点雷达 (Novel Concept Sniffing)
    extracted_novel_concepts: List[str] = Field(
        default_factory=list,
        description="""【极其关键】：从用户的话中，提取出脱离当前考点范畴的【新技术名词】。
        - 如果是学霸扩展（如聊HashMap时提到了'红黑树'），提取 ['红黑树']。
        - 如果是转移话题（如'我想聊聊MySQL索引'），提取 ['MySQL索引']。
        - 如果没有提及新概念，严格返回空列表[]。""",
    )


# 简历信息提取数据模型区
class ParsedResume(BaseModel):
    core_skills: List[str] = Field(
        description="从简历中提取出的核心专业技术名词（如 'Redis分布式锁', 'JVM调优', 'Kafka'）。排除日常用语，提纯为短语，最多提取 8 个。"
    )
    projects_star_summary: str = Field(
        description="将候选人的项目经历，浓缩为一段高度精炼的 STAR（情境、任务、行动、结果）总结，用字符串表示。字数控制在 150 字以内，供后续面试官参考。"
    )
    estimated_level: str = Field(
        description="根据简历评估候选人的职级深度（入门/应届, 初级, 中级, 高级/资深, 专家）。"
    )
