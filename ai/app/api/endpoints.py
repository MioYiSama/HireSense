import traceback
from pathlib import Path

from app.core.config import settings
from app.core.state_manager import session_store

# 假设你已经定义了获取工作流引擎和报告引擎的依赖注入函数
from app.dependencies import get_agent_workflow, get_report_generator
from app.models.schemas import (
    ReplyRequest,
    ReplyResponse,
    ReportPushRequest,  # 这里的 ReportPushRequest 实际上就是最终生成的报告外壳
    StartPayload,
    StartRequest,
    StartResponse,
    StopRequest,
    StopResponse,
)
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

FRONTEND_DEFAULT_RESUME = (
    Path(__file__)
    .parent.joinpath("frontend_default_resume.md")
    .read_text(encoding="utf-8")
)
BACKEND_DEFAULT_RESUME = (
    Path(__file__)
    .parent.joinpath("backend_default_resume.md")
    .read_text(encoding="utf-8")
)


router = APIRouter()


# ==========================================
# 1. 面试初始化接口 (Start)
# ==========================================
@router.post("/api/interview/start", response_model=StartResponse)
async def start_interview(req: StartRequest, workflow=Depends(get_agent_workflow)):
    """
    接收前端发来的简历和人设，初始化整个状态机。
    """
    try:
        # Fallback to default resume

        match req.job:
            case "backend":
                if req.resume is None or len(req.resume.strip()) == 0:
                    req.resume = BACKEND_DEFAULT_RESUME
            case "frontend":
                if req.resume is None or len(req.resume.strip()) == 0:
                    req.resume = FRONTEND_DEFAULT_RESUME
            case _:
                # Unreachable
                raise Exception(f"Unexpected job: {req.job}")

        # 呼叫业务总管完成极其复杂的冷启动（简历解析、实体对齐、图谱冷启动、状态落盘）
        res = await workflow.initialize_session(req)

        # 严格遵守 API 契约，仅返回 success 和 data
        return StartResponse(
            success=True,
            data=StartPayload(
                reply=res["reply_speech"],
                mode=res.get("mode", "single"),
                speaker_role=res.get("speaker_role", "ai"),
            ),
        )

    except Exception as e:
        print(f"[Start API Error]: {e}")
        return StartResponse(success=False, data="服务器连接失败")


# ==========================================
# 2. 面试对话接口 (Reply - 高频交互)
# ==========================================
@router.post("/api/interview/reply", response_model=ReplyResponse)
async def reply_interview(req: ReplyRequest, workflow=Depends(get_agent_workflow)):
    """
    处理用户的多模态输入，驱动 Agent 状态机流转并生成回复
    """
    # 1. 拦截非法会话
    state = session_store.get_state(req.id)
    if not state:
        raise HTTPException(
            status_code=404, detail="Interview session not found or expired."
        )
    if state.is_finished:
        raise HTTPException(
            status_code=409, detail="Interview session already finished."
        )

    # 2. 多模态数据解包 (Unpacking)
    user_text = ""
    duration = 0.0

    if req.input.type == "text":
        # 纯文本模式
        user_text = req.input.content
        duration = 0.0
    elif req.input.type == "transcript":
        # 语音转录模式，提取文本和真实说话耗时
        user_text = req.input.content.text
        duration = req.input.content.duration

    try:
        # 3. 呼叫业务总管推进一轮对话（打分、剪枝、LLM 生成话术全在里面）
        # 内部会通过 asyncio.create_task() 触发生成 advice 的后台异步任务
        turn_result = await workflow.process_turn(state, user_text)

        # 4. 组装返回契约
        return ReplyResponse(
            reply=turn_result.reply_speech,
            ending=turn_result.ending,
            mode=getattr(turn_result, "mode", "single"),
            speaker_role=getattr(turn_result, "speaker_role", "ai"),
        )
    except Exception as e:
        print(f"[Reply API Error]: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to process interview turn.")


# ==========================================
# 3. 面试终止接口 (Stop)
# ==========================================
@router.post("/api/interview/stop", response_model=StopResponse)
async def stop_interview(
    req: StopRequest,
    bg_tasks: BackgroundTasks,
    report_generator=Depends(get_report_generator),
):
    """
    前端通知面试结束。系统立即返回 success，并在后台启动【生成+推送】流水线。
    """
    state = session_store.get_state(req.id)
    if not state:
        return StopResponse(success=False)

    # 冻结状态，阻止后续聊天
    state.is_finished = True

    # 获取目标主控服务器的 URL 和 密钥 (生产环境应放在 .env 中)
    TARGET_SERVER_URL = settings.TARGET_SERVER_URL  # 测试阶段先推给自己
    INTERNAL_SECRET = settings.INTERNAL_SECRET

    # 将耗时的生成与推送任务加入 FastAPI 后台队列，当前接口瞬间返回！
    bg_tasks.add_task(
        report_generator.generate_and_push,
        state=state,
        target_url=TARGET_SERVER_URL,
        secret=INTERNAL_SECRET,
    )

    return StopResponse(success=True)


# ==========================================
# 4. 用于测试report 接口
# ==========================================
@router.put("/api/interview/report")
async def mock_main_server_receive_report(req: ReportPushRequest):
    """
    【Mock 接口】：模拟企业主服务器接收 AI Agent 推送过来的报告
    """
    # 1. 校验内部通信密钥
    if req.secret != "internal-super-secret-key":
        raise HTTPException(status_code=403, detail="Forbidden: Invalid Secret")

    # 2. 模拟入库操作
    print(f"\n📥 [Mock 主服务器] 收到来自 AI Agent 的报告！面试ID: {req.id}")
    print(f"📊 [Mock 主服务器] 综合得分: {req.report.score}")
    print(f"🗣️ [Mock 主服务器] 短板分析: {req.report.shortcomings}")
    print(
        f"💾 [Mock 主服务器] 正在将雷达图数据和 15 道题的问答明细落入 MySQL 数据库...\n"
    )

    # 3. 返回规定的契约格式
    return {"success": True, "info": "报告归档并生成成功", "req": req}
