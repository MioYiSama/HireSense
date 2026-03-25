from pydantic import BaseModel, Field
from typing import Any, Literal, Optional, List, Dict, Type
from langchain_openai import ChatOpenAI
import json
from langchain_core.prompts import ChatPromptTemplate
from app.models.schemas import AgentState
from app.core.history_manager import HistoryManager


class StartInterview(BaseModel):
    q_id_and_brief: List[str] = Field(
        description="从所提供的题单中选择一道契合的题目考察用户"
                    "填写的内容必须是[所选题目的q_id,题目内容]"
    )
    reply_speech: str = Field(
        description="根据所选的目标题目，根据态度和用户信息发出第一个问题的提问"
    )
    selected_node: str = Field(
        description="必须从提供的【题单选择】中说明你选择的concept考点，必须与提供的内容完全一致"
    )



class SingleAdvice(BaseModel):
    advice : str = Field(description="根据问答给出建议")



class TacticalDecision(BaseModel):
    # 核心动作抉择
    reasoning: str = Field(default="", description="比对用户回答和答案，综合历史记录和用户简历信息，决定是否对用户的回答进行追问，决定更换话题")
    action: Literal["PROBE", "TRANSITION", "END"] = Field(
        description="PROBE: 决定继续在当前题进行追问；TRANSITION: 决定放弃当前题，切换新考点；END: 决定结束整场面试。"
    )
    selected_node: Optional[str] = Field(
        default=None,
        description="如果 action 为 TRANSITION，必须从提供的【图谱菜单】中挑选下一个考点；如果为 PROBE 或 END，填 None。"
    )
    reply_speech: str = Field(
        description="如果 PROBE，输出带有 Hint 的引导话术；如果 TRANSITION，输出对本题的总结并抛出 selected_node 的新问题；如果 END，输出结束面试的收尾话术。"
    )
    q_id_and_brief: Optional[List[str]] = Field(
        default=None,
        description="如果确定更换考点并选择了所要考察的题目，则填入 [题目对应的q_id,题目内容] ；如果为 PROBE 或 END，则填 None"
    )

class Clarify(BaseModel):
    reply_speech : str = Field(description="用来回复用户的一句话")

# ==========================================
# 2. LLM 生成器核心类
# ==========================================
class LLMGenerator:
    def __init__(self ,llm = ChatOpenAI, fast_llm =ChatOpenAI):
        self.llm = llm
        self.fast_llm = fast_llm

    def _validate_model_payload(self, model_class: Type[BaseModel], payload: dict) -> BaseModel:
        """兼容 Pydantic v1/v2 的模型校验入口。"""
        if hasattr(model_class, "model_validate"):
            return model_class.model_validate(payload)
        return model_class.parse_obj(payload)

    def _extract_json_objects(self, text: str) -> List[str]:
        """从混杂文本中提取顶层 JSON 对象，处理额外前后缀或重复输出。"""
        objects = []
        start = None
        depth = 0
        in_string = False
        escape = False

        for index, char in enumerate(text):
            if start is None:
                if char == "{":
                    start = index
                    depth = 1
                    in_string = False
                    escape = False
                continue

            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == "\"":
                    in_string = False
                continue

            if char == "\"":
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    objects.append(text[start:index + 1])
                    start = None

        return objects

    def _recover_structured_generation(self, raw_message: Any, model_class: Type[BaseModel]) -> Optional[BaseModel]:
        """当 LangChain 工具参数解析失败时，尝试从原始响应中恢复合法 JSON。"""
        if raw_message is None:
            return None

        candidate_texts = []

        if isinstance(raw_message, dict):
            tool_calls = raw_message.get("tool_calls") or []
            content = raw_message.get("content")
        else:
            additional_kwargs = getattr(raw_message, "additional_kwargs", {}) or {}
            tool_calls = additional_kwargs.get("tool_calls") or []
            content = getattr(raw_message, "content", None)

        for tool_call in tool_calls:
            function_info = tool_call.get("function") or {}
            arguments = function_info.get("arguments")
            if isinstance(arguments, str) and arguments.strip():
                candidate_texts.append(arguments)

        if isinstance(content, str) and content.strip():
            candidate_texts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text")
                    if isinstance(text, str) and text.strip():
                        candidate_texts.append(text)

        for candidate_text in candidate_texts:
            try:
                return self._validate_model_payload(model_class, json.loads(candidate_text))
            except Exception:
                pass

            for json_blob in self._extract_json_objects(candidate_text):
                try:
                    return self._validate_model_payload(model_class, json.loads(json_blob))
                except Exception:
                    continue

        return None

    async def _retry_structured_generation(self, prompt_template, input_data, model_class, llm, max_retries=3):
        """
        通用的结构化生成重试方法
        如果 LLM 返回的数据不满足结构要求，会自动重试
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                structured_llm = llm.with_structured_output(model_class, include_raw=True)
                result = await (prompt_template | structured_llm).ainvoke(input_data)
                parsed = result.get("parsed")
                if parsed is not None:
                    return parsed

                recovered = self._recover_structured_generation(
                    raw_message=result.get("raw"),
                    model_class=model_class,
                )
                if recovered is not None:
                    print(f"[LLM Fallback] Recovered {model_class.__name__} from malformed structured output.")
                    return recovered

                parsing_error = result.get("parsing_error")
                if parsing_error is not None:
                    raise parsing_error
                raise ValueError(f"{model_class.__name__} structured generation returned no parsed result.")
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    print(f"[LLM Retry] Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying...")
                    continue
                else:
                    print(f"[LLM Error] All {max_retries} attempts failed: {e}")
                    raise last_error


    def _formatted_menu(self, question_menu):
        """
        格式化菜单数据。支持两种输入格式：
        1. 列表格式：[{"concept": "...", "question_info": [...]}, ...]
        2. 字典格式：{"类别": [{"concept": "...", "question_info": [...]}], ...}
        """
        formatted_question_menu = []

        # 如果输入是字典，先转换为列表
        if isinstance(question_menu, dict):
            items_to_process = []
            for category, questions in question_menu.items():
                if isinstance(questions, list):
                    items_to_process.extend(questions)
        else:
            items_to_process = question_menu

        for item in items_to_process:
            try:
                # 添加类型检查
                if not isinstance(item, dict):
                    print(f"[Warning] _formatted_menu received non-dict item: {type(item)}, {item}")
                    continue

                concept = item.get("concept")
                question_info = item.get("question_info") or []

                # 确保 question_info 是列表
                if not isinstance(question_info, list):
                    question_info = []

                formatted_question_menu.append({
                    "concept": concept,
                    "questions": [
                        [q.get("q_id"), q.get("brief")] for q in question_info
                        if isinstance(q, dict) and q.get("q_id") is not None and q.get("brief") is not None
                    ]
                })
            except Exception as e:
                print(f"[Warning] _formatted_menu failed to process item: {e}")
                continue
        return formatted_question_menu

    async def decide_tactics_and_generate(self,
                                          current_topic: str,
                                          question_brief : str,
                                          std_answer: str,
                                          cumulative_answer: str,
                                          mastery_score: float,
                                          completed_rounds: int,
                                          current_turn: int,
                                          max_turn : int,
                                          menu: list,
                                          history: str,
                                          candidate_fact_sheet: List[str],
                                          resume_star: str,
                                          allow_end: bool = True,
                                          ) -> TacticalDecision:
            final_menu = self._formatted_menu(menu)

            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是拥有绝对控制权的技术面试官。当前正在考察【{current_topic}】题目为【{question_brief}】。
                候选人已在该题拉扯了 {current_turn}/{max_turn} 轮。底层评估掌握度为 {mastery_score}/100分。
                候选人累计已完成 {completed_rounds} 轮有效问答。
                当前系统是否允许结束整场面试：{allow_end}。

                【系统硬约束】
                - 如果 allow_end 为 false，你绝对不能选择 END，只能在 PROBE 和 TRANSITION 里二选一。
                - 如果 allow_end 为 true，也只有两种情况可以 END：
                  1. 候选人已经连续多轮表现较差，继续追问价值很低；
                  2. 候选人已经在高难度问题上回答得很好，评估信息已经充分。
                - 除了这两种情况，不要 END；在样本不足或结论不稳时，优先继续采样。

                【你的双重任务】：
                结合【对话历史】和候选人的【累计回答】【简历信息】，决定是继续追问、更换题目，还是结束整场面试。

                选择 A：PROBE (继续追问)
                - 条件：他答对了一部分，且你认为给他一点暗示（Hint），他能答出更多。
                - 动作：对比【标准答案】，找出他遗漏的要点，生成引导式追问。绝对不要直接给答案！

                选择 B：TRANSITION (结束本题，图谱跃迁)
                - 条件：他已经完全答对、完全不会，或者一直在绕圈子毫无进展，或者用户明确表示或者暗示想要更换考点，或者当拉扯轮数大于{max_turn}。
                - 动作：从【图谱菜单】中挑选 1 个最合适的考点,并从考点中的问题列表中挑选一题作为问题，简单点评刚才的表现，并抛出新考点的问题（可以适当润色使得衔接更自然）。

                选择 C：END (结束整场面试)
                - 条件：你已经收集到足够的评估信息，不再需要继续追问或切换新题；或者图谱菜单里已经没有合适的新题；或者候选人的表现已足以做出结论。
                - 动作：给出简短自然的收尾话术，明确这场面试可以结束。不要再提新的问题。

                【资源库】
                - 绝对真理(标答): {std_answer}
                - 图谱候选菜单: {menu_str}
                - 用户简历信息: {resume_star}

                【输出格式要求】
                必须严格输出 JSON 格式，包含以下字段：
                1. reasoning: 你的决策理由（字符串）
                2. action: 必须是 "PROBE"、"TRANSITION" 或 "END"（字符串）
                3. selected_node: 如果 action 是 TRANSITION，填写选中的考点名称；如果是 PROBE 或 END，填 null（字符串或null）
                4. reply_speech: 你对候选人说的话，必须口语化、自然（字符串）
                5. q_id_and_brief: 如果 action 是 TRANSITION 且选择了题目，填写 [题目id, 题目内容]；如果 action 是 PROBE 或 END，填 null（数组或null）

                注意：action 和 reply_speech 是必需字段，不能省略；如果 action 为 END，selected_node 和 q_id_and_brief 必须都是 null。"""),
                ("user", "【近期历史】\n{history}\n【全局历史总结】\n{candidate_fact_sheet}\n【候选人本题累计回答】: {cumulative_answer}")
            ])

            # 使用重试机制
            res: TacticalDecision = await self._retry_structured_generation(
                prompt_template=prompt,
                input_data={
                    "question_brief": question_brief,
                    "current_topic": current_topic,
                    "current_turn": current_turn,
                    "max_turn" : max_turn,
                    "completed_rounds": completed_rounds,
                    "mastery_score": mastery_score,
                    "std_answer": std_answer,
                    "menu_str": final_menu,
                    "resume_star":resume_star,
                    "history": history,
                    "candidate_fact_sheet": candidate_fact_sheet,
                    "cumulative_answer": cumulative_answer,
                    "allow_end": allow_end,
                },
                model_class=TacticalDecision,
                llm=self.llm,
                max_retries=3
            )
            return res

    async def clarify_question(self,
                               user_text : str,
                               current_topic: str,
                               question_brief : str,
                               std_answer: str,
                               history: str
                               ):
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是拥有绝对控制权的技术面试官。当前正在考察【{current_topic}】题目为【{question_brief}】。
                            用户因为没有理解好问题向你请求澄清题目，请根据题目，答案和用户的发言做出回答帮助用户理解考题,注意一定不要泄露答案。
                            {std_answer}

                            【输出格式要求】
                            必须输出标准的 JSON 格式，包含以下字段：
                            1. reply_speech: 你对用户的回复（字符串，必需）

                            输出必须口语化、自然。"""),
                ("user","【近期历史】\n{history}\n【用户发言】\n{user_text}")
            ])

            res : Clarify = await self._retry_structured_generation(
                prompt_template=prompt,
                input_data={
                    "current_topic":current_topic,
                    "question_brief":question_brief,
                    "std_answer":std_answer,
                    "history": history,
                    "user_text": user_text,
                },
                model_class=Clarify,
                llm=self.llm,
                max_retries=3
            )

            return res

    async def gen_single_advice(
        self,
        question: str,
        user_ans: str,
        std_ans: str,
        score: float,
        score_breakdown: Optional[Dict[str, float]] = None,
        missing_points: Optional[List[str]] = None,
        logic_status: str = "",
        reason_tags: Optional[List[str]] = None,
    ):
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """
      你是一个技术评价建议师，以下是一个面试片段的问答
      【题目】: {question}
      【标答】: {std_answer}
      【用户回答】: {user_answer}
      【机器打分】: {score}/100
      【分项得分】: {score_breakdown}
      【逻辑状态】: {logic_status}
      【原因标签】: {reason_tags}
      【缺失点】: {missing_points}

      【输出格式要求】
      必须输出 JSON 格式，包含以下字段：
      1. advice: 你的评价建议（字符串，必需）

      请把 advice 写成对机器分数的解释，而不是重新发明另一套评分。
      如果 score >= 70，必须明确肯定回答方向或核心点；
      如果 40 <= score < 70，必须明确指出“答到了哪些、还缺哪些”；
      如果 score < 40，必须明确说明回答偏离、冲突或关键点缺失；
      绝对不要出现与分数相反的措辞，例如低分却说“回答正确”。
      严格控制在一句话，不超过 50 个字。不要有废话。"""
             )
        ])

        res: SingleAdvice = await self._retry_structured_generation(
            prompt_template=prompt_template,
            input_data={
                "question": question,
                "std_answer": std_ans,
                "user_answer": user_ans,
                "score": score,
                "score_breakdown": json.dumps(score_breakdown or {}, ensure_ascii=False),
                "logic_status": logic_status or "Unknown",
                "reason_tags": json.dumps(reason_tags or [], ensure_ascii=False),
                "missing_points": json.dumps(missing_points or [], ensure_ascii=False),
            },
            model_class=SingleAdvice,
            llm=self.fast_llm,
            max_retries=3
        )
        return res.advice



    async def generate_opening_speech(self, personalization: str, projects_star: str, question_menu: list) -> StartInterview:
            """
            生成带有强烈人设风格的开场白和第一道题
            """
            final_menu = self._formatted_menu(question_menu)
            prompt = ChatPromptTemplate.from_messages([
                ("system", """
            你正在进行一场真实的语音面试。

            【你的绝对人设】
            {personalization}

            【候选人背景】
            {projects_star}

            【题单选择】
            {question_menu}

            【任务】
            你必须且只能从【题单选择】中：
            1. 选择一个 concept，作为 selected_node
            2. 在该 concept 对应的 question_info 中选择一道题
            3. 将所选题目填写到 q_id_and_brief，格式必须严格为：
               ["题目的q_id", "题目的brief"]
            4. 生成一段面试官开场提问，填写到 reply_speech

            【强制要求】
            1. 你的输出必须严格匹配以下字段：
               - q_id_and_brief
               - reply_speech
               - selected_node
            2. 不允许输出 greeting、question、concept、answer 或任何额外字段
            3. selected_node 必须与【题单选择】中的某个 concept 完全一致
            4. q_id_and_brief 必须是长度为 2 的字符串列表，内容依次为 [q_id, brief]
            5. reply_speech 必须基于你选中的那道题自然发问
            6. 不要解释，不要添加注释，不要输出代码块
            7. 以JSON格式返回结果
            """),
            ])

            res : StartInterview = await self._retry_structured_generation(
                prompt_template=prompt,
                input_data={
                    "personalization":personalization,
                    "projects_star":projects_star,
                    "question_menu":final_menu
                },
                model_class=StartInterview,
                llm=self.llm,
                max_retries=3
            )

            return res
