from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.models.schemas import ParsedResume
from typing import Dict, Any
import os


class ResumeAnalyzer:
    def __init__(self, llm):


        self.llm = llm


        self.structured_llm = self.llm.with_structured_output(ParsedResume)


    async def analyze_and_align(self, resume_text: str, job_domain: str) -> ParsedResume:
        """
        核心方法：解析简历 -> 提取技能 -> 向量图谱对齐
        """
        # 执行非结构化 -> 结构化
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是资深的技术 HR 专家。请阅读候选人的原始简历，执行信息提纯。
                【任务】
                1. 提取出他最熟悉的核心技术点（core_skills）。
                2. 将他冗长的项目经验浓缩为一段极简的 STAR 摘要（projects_star_summary），必须是一个字符串。
                3. 评估其职级（estimated_level）。
                4. 以JSON格式返回结果
                """),

            ("user", "【目标岗位】: {job_domain}\n【原始简历】:\n{resume_text}")
        ])

        # 耗时约 1~1.5 秒
        parsed_resume: ParsedResume = await (prompt | self.structured_llm).ainvoke({
            "job_domain": job_domain,
            "resume_text": resume_text,
        })

        return parsed_resume
