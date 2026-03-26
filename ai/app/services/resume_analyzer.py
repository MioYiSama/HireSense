import json
import re
from datetime import datetime, timezone

from app.models.schemas import (
    ParsedResume,
    ResumeAnalysis,
    ResumeAnalysisBlock,
    ResumeAnalysisBlockDraft,
    ResumeAnalysisCallout,
    ResumeAnalysisDraft,
    ResumeAnalysisHighlightPhrase,
)
from langchain_core.prompts import ChatPromptTemplate


class ResumeAnalyzer:
    def __init__(self, llm):
        self.llm = llm
        self.structured_llm = self.llm.with_structured_output(ParsedResume)
        self.resume_analysis_llm = self.llm.with_structured_output(ResumeAnalysisDraft)

    async def analyze_and_align(self, resume_text: str, job_domain: str) -> ParsedResume:
        """
        核心方法：解析简历 -> 提取技能 -> 向量图谱对齐
        """
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是资深的技术 HR 专家。请阅读候选人的原始简历，执行信息提纯。
                【任务】
                1. 提取出他最熟悉的核心技术点（core_skills）。
                2. 将他冗长的项目经验浓缩为一段极简的 STAR 摘要（projects_star_summary），必须是一个字符串。
                3. 评估其职级（estimated_level）。
                4. 以JSON格式返回结果
                """,
                ),
                ("user", "【目标岗位】: {job_domain}\n【原始简历】:\n{resume_text}"),
            ]
        )

        parsed_resume: ParsedResume = await (prompt | self.structured_llm).ainvoke(
            {
                "job_domain": job_domain,
                "resume_text": resume_text,
            }
        )

        return parsed_resume

    async def analyze_highlight_resume(
        self, resume_text: str, job_domain: str
    ) -> ResumeAnalysis:
        blocks = self.split_resume_blocks(resume_text)
        if not blocks:
            raise ValueError("resume text is empty")

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是一个毒舌但专业的技术面试教练，负责把候选人简历标成“彩色高亮版”。

【输出要求】
1. 你只分析用户给出的 blocks，不能新增、删除或改写 block 文本。
2. 每个 block 必须返回原样 id。
3. label 只能是：
   - strength: 明确亮点，值得候选人在面试里主动展开
   - probe: 有经验痕迹，但值得继续深挖 ownership、规模、指标、边界
   - risk: 措辞过满、结论过大、明显可能被追着打
   - neutral: 信息性段落，不需要重点标注
4. highlight_phrases 中的 text 必须逐字摘自对应 block 原文，最多 3 个。
5. risk 段落优先圈出夸张词、绝对化结论、空泛大词；callout 要尖锐、有压迫感，但不能粗俗。
6. 如果某段没有足够证据支持亮点或风险，优先返回 probe 或 neutral，不要乱判 strength。
7. summary 用 1 句话总结整份简历的可打程度；overall_tone 用 1 到 2 个英文词概括整体气质。
""",
                ),
                (
                    "user",
                    "【目标岗位】\n{job_domain}\n\n【逐段简历 blocks】\n{blocks_json}",
                ),
            ]
        )

        analysis_draft: ResumeAnalysisDraft = await (
            prompt | self.resume_analysis_llm
        ).ainvoke(
            {
                "job_domain": job_domain,
                "blocks_json": json.dumps(blocks, ensure_ascii=False, indent=2),
            }
        )

        return self.normalize_analysis(job_domain, blocks, analysis_draft)

    @staticmethod
    def split_resume_blocks(resume_text: str) -> list[dict[str, str]]:
        normalized = resume_text.replace("\r\n", "\n")
        lines = normalized.split("\n")
        blocks: list[str] = []
        current: list[str] = []

        def flush() -> None:
            if not current:
                return

            block = "\n".join(current).strip()
            current.clear()
            if not block:
                return

            for chunk in ResumeAnalyzer._split_long_block(block):
                if chunk:
                    blocks.append(chunk)

        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped:
                flush()
                continue

            if ResumeAnalyzer._is_bullet_line(stripped) and current:
                flush()

            current.append(stripped)

        flush()

        if not blocks and resume_text.strip():
            blocks = [resume_text.strip()]

        return [
            {"id": f"block-{index + 1}", "text": text}
            for index, text in enumerate(blocks)
        ]

    @staticmethod
    def _is_bullet_line(line: str) -> bool:
        bullet_prefixes = ("- ", "* ", "• ", "1.", "2.", "3.", "4.", "5.", "6.")
        return line.startswith(bullet_prefixes)

    @staticmethod
    def _split_long_block(block: str, max_length: int = 260) -> list[str]:
        if len(block) <= max_length:
            return [block]

        parts = re.split(r"(?<=[。！？；;.!?])\s*", block)
        chunks: list[str] = []
        current = ""

        for part in parts:
            segment = part.strip()
            if not segment:
                continue

            candidate = f"{current}{segment}" if current else segment
            if len(candidate) <= max_length:
                current = candidate
                continue

            if current:
                chunks.append(current)
                current = segment
                continue

            chunks.append(segment[:max_length].strip())
            current = segment[max_length:].strip()

        if current:
            chunks.append(current)

        return chunks or [block]

    @staticmethod
    def _normalize_label(label: str | None) -> str:
        if label in {"strength", "probe", "risk", "neutral"}:
            return label
        return "neutral"

    @staticmethod
    def _normalize_phrase_text(block_text: str, phrase_text: str) -> str:
        candidate = str(phrase_text or "").strip().strip("“”\"'")
        if not candidate:
            return ""
        if candidate in block_text:
            return candidate
        return ""

    @staticmethod
    def _fallback_reason(label: str) -> str:
        if label == "strength":
            return "这段有明确动作和结果，适合当作面试亮点展开。"
        if label == "probe":
            return "这里有经验痕迹，但还需要补 ownership、规模或指标。"
        if label == "risk":
            return "这段结论下得过满，如果没有证据支撑很容易被追问。"
        return "这段更偏信息陈列，目前不构成重点攻防位。"

    @staticmethod
    def _fallback_callout(block_text: str) -> ResumeAnalysisCallout:
        risk_phrase = "高风险措辞"
        for keyword in ("精通", "高并发", "架构师", "业内领先", "全栈专家", "性能极致"):
            if keyword in block_text:
                risk_phrase = keyword
                break

        return ResumeAnalysisCallout(
            title="高危吹牛词",
            body=(
                f"⚠️ 此处你写了“{risk_phrase}”，已被系统锁定为高危吹牛词，"
                "下一轮大概率会被连续追问规模、瓶颈、压测数据和故障复盘。"
            ),
        )

    @classmethod
    def normalize_analysis(
        cls,
        job_domain: str,
        blocks: list[dict[str, str]],
        analysis_draft: ResumeAnalysisDraft,
    ) -> ResumeAnalysis:
        draft_by_id = {block.id: block for block in analysis_draft.blocks}
        normalized_blocks: list[ResumeAnalysisBlock] = []

        strength_count = 0
        probe_count = 0
        risk_count = 0

        for source_block in blocks:
            draft_block: ResumeAnalysisBlockDraft | None = draft_by_id.get(
                source_block["id"]
            )
            label = cls._normalize_label(draft_block.label if draft_block else None)
            if label == "strength":
                strength_count += 1
            elif label == "probe":
                probe_count += 1
            elif label == "risk":
                risk_count += 1

            seen_phrases: set[str] = set()
            highlight_phrases: list[ResumeAnalysisHighlightPhrase] = []
            for phrase in (draft_block.highlight_phrases if draft_block else []):
                text = cls._normalize_phrase_text(source_block["text"], phrase.text)
                if not text or text in seen_phrases:
                    continue

                seen_phrases.add(text)
                highlight_phrases.append(
                    ResumeAnalysisHighlightPhrase(
                        text=text,
                        label=cls._normalize_label(phrase.label),
                        comment=str(phrase.comment or "").strip(),
                    )
                )
                if len(highlight_phrases) >= 3:
                    break

            callout = None
            if label == "risk":
                if draft_block and draft_block.callout and draft_block.callout.body.strip():
                    callout = ResumeAnalysisCallout(
                        title=draft_block.callout.title.strip(),
                        body=draft_block.callout.body.strip(),
                    )
                else:
                    callout = cls._fallback_callout(source_block["text"])

            normalized_blocks.append(
                ResumeAnalysisBlock(
                    id=source_block["id"],
                    text=source_block["text"],
                    label=label,
                    reason=(
                        str(draft_block.reason or "").strip()
                        if draft_block and str(draft_block.reason or "").strip()
                        else cls._fallback_reason(label)
                    ),
                    highlight_phrases=highlight_phrases,
                    callout=callout,
                )
            )

        summary = analysis_draft.summary.strip()
        if not summary:
            summary = (
                f"共识别 {strength_count} 处亮点、{probe_count} 处可深挖段落、"
                f"{risk_count} 处高风险措辞。"
            )

        overall_tone = analysis_draft.overall_tone.strip() or "sharp"

        return ResumeAnalysis(
            version="v1",
            job=job_domain,
            generated_at=datetime.now(timezone.utc),
            summary=summary,
            overall_tone=overall_tone,
            blocks=normalized_blocks,
        )
