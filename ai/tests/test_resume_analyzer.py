from app.models.schemas import ResumeAnalysisBlockDraft, ResumeAnalysisDraft
from app.services.resume_analyzer import ResumeAnalyzer


def test_split_resume_blocks_keeps_sections_and_bullets_stable():
    resume = """
    张三

    工作经历
    负责支付系统重构，接口成功率提升到 99.98%。
    - 精通高并发系统设计
    - 主导 Redis 热点缓存治理
    """.strip()

    blocks = ResumeAnalyzer.split_resume_blocks(resume)

    assert [block["id"] for block in blocks] == ["block-1", "block-2", "block-3", "block-4"]
    assert blocks[0]["text"] == "张三"
    assert "负责支付系统重构" in blocks[1]["text"]
    assert blocks[2]["text"] == "- 精通高并发系统设计"
    assert blocks[3]["text"] == "- 主导 Redis 热点缓存治理"


def test_normalize_analysis_falls_back_for_missing_callout_and_invalid_phrase():
    blocks = [
        {"id": "block-1", "text": "精通高并发系统设计，负责核心链路优化。"},
        {"id": "block-2", "text": "参与需求评审与上线支持。"},
    ]
    draft = ResumeAnalysisDraft(
        summary="",
        overall_tone="",
        blocks=[
            ResumeAnalysisBlockDraft(
                id="block-1",
                label="risk",
                reason="",
                highlight_phrases=[
                    {"text": "精通高并发", "label": "risk", "comment": "措辞过满"},
                    {"text": "不存在的短语", "label": "risk", "comment": "应被过滤"},
                ],
                callout=None,
            )
        ],
    )

    analysis = ResumeAnalyzer.normalize_analysis("backend", blocks, draft)

    assert analysis.version == "v1"
    assert analysis.job == "backend"
    assert analysis.overall_tone == "sharp"
    assert analysis.summary == "共识别 0 处亮点、0 处可深挖段落、1 处高风险措辞。"
    assert analysis.blocks[0].label == "risk"
    assert analysis.blocks[0].highlight_phrases[0].text == "精通高并发"
    assert len(analysis.blocks[0].highlight_phrases) == 1
    assert analysis.blocks[0].callout is not None
    assert "高危吹牛词" in analysis.blocks[0].callout.title
    assert analysis.blocks[1].label == "neutral"
