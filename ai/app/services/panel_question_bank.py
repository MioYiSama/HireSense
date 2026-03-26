from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class PanelQuestion:
    question_id: str
    interviewer_role: str
    question_type: str
    question_brief: str
    standard_answer: str
    difficulty_label: str
    concept: str
    focus_tags: List[str]


_SHARED_HR_QUESTIONS: List[PanelQuestion] = [
    PanelQuestion(
        question_id="hr_intro_strength",
        interviewer_role="hr",
        question_type="behavioral",
        question_brief="先做个简短自我介绍，再讲一个最能代表你优势的项目经历。",
        standard_answer="回答应包含清晰的个人定位、与岗位匹配的核心优势、项目背景、本人承担的职责、关键行动和可量化结果。",
        difficulty_label="basic",
        concept="自我介绍与岗位匹配",
        focus_tags=["表达", "岗位匹配", "项目经历"],
    ),
    PanelQuestion(
        question_id="hr_conflict",
        interviewer_role="hr",
        question_type="behavioral",
        question_brief="讲一个你和同事或协作方有分歧的经历，你是怎么推进的？",
        standard_answer="回答应说明分歧背景、各方诉求、本人如何澄清目标和事实、如何协调方案、最终结果以及复盘收获，避免只强调对方问题。",
        difficulty_label="intermediate",
        concept="冲突处理与团队协作",
        focus_tags=["协作", "沟通", "复盘"],
    ),
    PanelQuestion(
        question_id="hr_growth",
        interviewer_role="hr",
        question_type="behavioral",
        question_brief="过去一年你成长最快的点是什么？你是怎么把它学会并真正用起来的？",
        standard_answer="回答应覆盖成长目标、学习路径、落地场景、遇到的阻力、结果验证和对后续工作的具体影响。",
        difficulty_label="intermediate",
        concept="学习能力与成长",
        focus_tags=["学习能力", "成长", "落地"],
    ),
    PanelQuestion(
        question_id="hr_motivation",
        interviewer_role="hr",
        question_type="behavioral",
        question_brief="你为什么想来我们这样的团队？你下一阶段最在意什么？",
        standard_answer="回答应体现对岗位和团队特点的理解、个人职业目标、匹配原因、期望成长方向和稳定性判断，避免泛泛而谈。",
        difficulty_label="basic",
        concept="求职动机与稳定性",
        focus_tags=["动机", "稳定性", "职业规划"],
    ),
]

_BACKEND_EXECUTIVE_QUESTIONS: List[PanelQuestion] = [
    PanelQuestion(
        question_id="exec_backend_tradeoff",
        interviewer_role="executive",
        question_type="executive",
        question_brief="如果一个核心后端需求必须两周上线，但稳定性风险明显，你会怎么做取舍？",
        standard_answer="回答应说明先明确业务目标和不可妥协指标，拆分最小可交付范围，识别主要技术风险，给出灰度/回滚/监控方案，并与业务方同步成本和边界。",
        difficulty_label="advanced",
        concept="业务取舍与风险管理",
        focus_tags=["业务判断", "风险控制", "Owner意识"],
    ),
    PanelQuestion(
        question_id="exec_backend_impact",
        interviewer_role="executive",
        question_type="executive",
        question_brief="讲一个你做的技术决策真正影响了业务结果的例子。",
        standard_answer="回答应包含业务背景、决策目标、候选方案、本人决策依据、跨团队推动方式、量化结果和后续反思。",
        difficulty_label="advanced",
        concept="业务影响与技术决策",
        focus_tags=["业务结果", "决策", "推动"],
    ),
]

_FRONTEND_EXECUTIVE_QUESTIONS: List[PanelQuestion] = [
    PanelQuestion(
        question_id="exec_frontend_tradeoff",
        interviewer_role="executive",
        question_type="executive",
        question_brief="如果一个关键前端项目时间很紧，但体验质量和发布风险都不低，你会怎么取舍？",
        standard_answer="回答应说明先对齐业务目标和核心体验指标，拆分范围，优先保障主路径体验，明确降级方案、监控与回滚，并主动管理预期。",
        difficulty_label="advanced",
        concept="业务取舍与交付判断",
        focus_tags=["取舍", "交付", "风险管理"],
    ),
    PanelQuestion(
        question_id="exec_frontend_impact",
        interviewer_role="executive",
        question_type="executive",
        question_brief="讲一个你做的前端方案最终对业务指标产生明显影响的例子。",
        standard_answer="回答应包含业务背景、体验或效率问题、方案选择、跨角色协同、上线后的指标变化和复盘。",
        difficulty_label="advanced",
        concept="业务影响与方案推动",
        focus_tags=["业务结果", "推动", "复盘"],
    ),
]

_ROLE_QUESTION_BANK: Dict[str, Dict[str, List[PanelQuestion]]] = {
    "hr": {
        "backend": _SHARED_HR_QUESTIONS,
        "frontend": _SHARED_HR_QUESTIONS,
    },
    "executive": {
        "backend": _BACKEND_EXECUTIVE_QUESTIONS,
        "frontend": _FRONTEND_EXECUTIVE_QUESTIONS,
    },
}


def get_panel_question_candidates(job: str, role: str) -> List[PanelQuestion]:
    return list(_ROLE_QUESTION_BANK.get(role, {}).get(job, []))
