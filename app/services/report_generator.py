import uuid
import httpx
import json
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel,Field
from app.core.config import RECOMMEND_DATA
from app.models.schemas import AgentState,ReviewItem,ReportContent,ReportPushRequest
recommend_data = RECOMMEND_DATA

with open(str(RECOMMEND_DATA), "r", encoding="utf-8") as f:
    data = json.load(f)


class ReportBackend(BaseModel):
    # 通用能力维度
    logical_thinking: float = Field(description="用户的逻辑思维评分")
    communication_skills: float = Field(description="用户的沟通表达评分")
    adaptability: float = Field(description="用户的应变能力评分")
    confidence_level: float = Field(description="用户的自信度评分")
    learning_ability: float = Field(description="用户的学习能力评分")
    team_collaboration: float = Field(description="用户的团队协同评分")

    # 专业能力维度
    design: float = Field(description="用户的设计能力评分")
    performance: float = Field(description="用户的性能把控能力评分")
    engineering_practice: float = Field(description="用户的工程化能力评分")
    componentization: float = Field(description="用户的组件化能力评分")
    data_flow: float = Field(description="用户的数据流把控能力评分")
    security: float = Field(description="用户的安全意识/能力评分")

    # 反馈
    feedback: str = Field(description="给用户的总结反馈")
    shortcomings: List[str] =Field(description="列举用户的明显短板")
    advice : str = Field(description="给用户的总建议")
    urls: List[str] = Field(description="给出你所选择的推荐的内容text和url，url和text必须完全来自所给的data，内容不允许重复"
                                        "例子：C语言教程  https://example.com/video")

class ReportFrontend(BaseModel):
    # 通用能力维度
    logical_thinking: float = Field(description="用户的逻辑思维评分")
    communication_skills: float = Field(description="用户的沟通表达评分")
    adaptability: float = Field(description="用户的应变能力评分")
    confidence_level: float = Field(description="用户的自信度评分")
    learning_ability: float = Field(description="用户的学习能力评分")
    team_collaboration: float = Field(description="用户的团队协同评分")

    # 专业能力维度（按要求定义）
    design: float = Field(description="用户的设计能力评分")
    performance: float = Field(description="用户的性能把控能力评分")
    engineering_practice: float = Field(description="用户的工程化能力评分")
    componentization: float = Field(description="用户的组件化能力评分")
    data_flow: float = Field(description="用户的数据流把控能力评分")
    security: float = Field(description="用户的安全意识/能力评分")

    # 反馈
    feedback: str = Field(description="给用户的总结反馈")
    shortcomings: List[str] = Field(description="列举用户的明显短板")
    advice: str = Field(description="给用户的总建议")
    urls: List[str] = Field(description="给出你所选择的推荐的内容text和url，url和text必须完全来自所给的data，内容不允许重复"
                                        "例子：C语言教程  https://example.com/video")

class FinalReport:
    def __init__(self, llm : ChatOpenAI):
        self.llm = llm

    async def build_report(self, state:AgentState) -> ReportContent:

        if state.interview_logs is None:
            raise ValueError("面试日志不存在")

        # --------------------------------------------------
        # Map 数据提取：组装硬性事实与底层日志
        # --------------------------------------------------
        history_transcript = ""
        final_reviews = []
        final_score = 0

        for log in state.interview_logs:
            history_transcript += (
                f"问题:{log.interviewer}回答{log.interviewee}评分:{log.final_score}\n--------------\n"
            )

            final_reviews.append(ReviewItem(
                interviewer=log.interviewer,
                interviewee=log.interviewee,
                score=log.final_score,
                advice=log.async_advice,
            ))

            final_score += log.final_score
        # --------------------------------------------------
        # Reduce 全局总结：大模型生成高阶软实力与雷达图
        # --------------------------------------------------
        final_score = final_score / len(state.interview_logs)


        prompt_tmp = ChatPromptTemplate.from_messages([
            ("system", """你是技术总监。面试已结束，请根据底层的【机器打分与分题点评记录】，对候选人进行全局复盘，并在最后基于自己先前的判断，从data库中选择适合用户提升的内容，最终给出内容来源的url
            。
                    【候选人背景】: {resume_star}
                    【建议学习资料】:{data}
                    【任务要求】:
                    严格按 JSON 格式输出总分、general(软实力) 
                    1. general纬度按要求给出6个纬度的评分
                    2. specific维度的按要求给出6个纬度的评分
                    3. 评价必须客观犀利，一针见血。
                    4. 根据给出的建议学习资料选出text和url，组装成一个单一的str url格式，例子：C语言教程  https://example.com/video
                    5. 回答必须使用中文"""),
                    ("user", "【分题表现记录汇总】:\n{transcript}")
        ])

        prompt = await prompt_tmp.ainvoke({
            "resume_star":state.resume_star,
            "transcript" : history_transcript,
            "data" : data
        })

        if state.job == "backend":
            llm_with_structure = self.llm.with_structured_output(ReportBackend)
            res : ReportBackend = await llm_with_structure.ainvoke(prompt)
            report = ReportContent(
                score=final_score,
                general={
                    "逻辑思维": res.logical_thinking,
                    "沟通表达": res.communication_skills,
                    "应变能力": res.adaptability,
                    "自信度": res.confidence_level,
                    "学习能力": res.learning_ability,
                    "团队协同": res.team_collaboration
                },
                # 专业能力：中文键名映射 ReportBackend 专业能力字段
                specific={
                    "设计": res.design,
                    "性能": res.performance,
                    "工程化": res.engineering_practice,
                    "组件化": res.componentization,
                    "数据流": res.data_flow,
                    "安全": res.security
                },
                feedback=res.feedback,
                shortcomings=res.shortcomings,
                advice=res.advice,
                reviews=final_reviews,
                resources=["www"]
            )

        elif state.job == "frontend":
            llm_with_structure = self.llm.with_structured_output(ReportFrontend)
            res: ReportFrontend = await llm_with_structure.ainvoke(prompt)
            report = ReportContent(
                score=final_score,
                general={
                    "逻辑思维": res.logical_thinking,
                    "沟通表达": res.communication_skills,
                    "应变能力": res.adaptability,
                    "自信度": res.confidence_level,
                    "学习能力": res.learning_ability,
                    "团队协同": res.team_collaboration
                },
                # 专业能力：中文键名映射 ReportFrontend 专业能力字段
                specific={
                    "设计": res.design,
                    "性能": res.performance,
                    "工程化": res.engineering_practice,
                    "组件化": res.componentization,
                    "数据流": res.data_flow,
                    "安全": res.security
                },
                feedback=res.feedback,
                shortcomings=res.shortcomings,
                advice=res.advice,
                reviews=final_reviews,
                resources=res.urls
            )

        else:
            raise ValueError(f"Invalid job type: {state.job}. Expected 'backend' or 'frontend'.")

        return report

    async def generate_and_push(self, state: AgentState, target_url: str, secret: str):
        """
              【核心业务流】：后台异步生成报告 -> 推送给企业主业务服务器 -> 销毁内存
              """
        try:
            print(f" [Webhook] 正在为会话 {state.session_id} 生成评估报告...")
            # 1. 呼叫大模型生成完整的报告内容 (耗时约 3~5 秒)
            report_content = await self.build_report(state)

            # 2. 按照 OpenAPI 契约组装 RequestBody
            payload = ReportPushRequest(
                secret=secret,
                id=state.session_id,
                report=report_content
            )

            # 3. 发起异步 HTTP PUT 请求推送数据
            print(f" [Webhook] 报告生成完毕，正在推送到主控服务器: {target_url}")
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    target_url,
                    json=payload.model_dump(),
                    timeout=10.0  # 设置合理的超时时间
                )
                response.raise_for_status()  # 如果返回 4xx/5xx 则抛出异常

                resp_data = response.json()
                if resp_data.get("success"):
                    print(f" [Webhook] 报告归档成功！主控返回: {resp_data.get('message')}")
                else:
                    print(f" [Webhook] 报告推送被拒绝: {resp_data}")

        except Exception as e:
            print(f" [Webhook Error] 报告推送失败: {e}")

        finally:
            # 4. 【绝对红线】：不论推送成败，必须清理内存，防止 OOM
            from app.core.state_manager import session_store
            session_store.delete_state(state.session_id)
            print(f"🧹 [System] 会话 {state.session_id} 内存已清理。")





