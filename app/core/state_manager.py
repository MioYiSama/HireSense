import time
from typing import Dict, Optional
from fastapi import HTTPException
from app.models.schemas import AgentState


class StateManager:
    """
    全局面试状态机管理器。
    当前采用基于内存的单例模式（In-memory Singleton）。
    在生产环境（多进程部署）下，应将底层 self._store 替换为 Redis 连接池。
    """

    def __init__(self):
        self._store: Dict[str, AgentState] = {}
        # 记录最后活跃时间，用于清理僵尸 Session
        self._last_active: Dict[str, float] = {}
        # 会话超时时间：默认 60 分钟无操作即视为废弃
        self.session_timeout_sec = 3600

    def save_state(self, session_id: str, state: AgentState) -> None:
        """
        新建或覆盖存储一个状态机
        """
        self._store[session_id] = state
        self._last_active[session_id] = time.time()

    def get_state(self, session_id: str) -> AgentState:
        """
        安全获取状态机。如果不存在则直接抛出 404 异常，阻断 API 往下执行。
        """
        state = self._store.get(session_id)
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"面试会话 {session_id} 不存在或已超时失效。"
            )

        # 刷新活跃时间
        self._last_active[session_id] = time.time()
        return state

    def delete_state(self, session_id: str) -> None:
        """
        面试结束出表后，主动销毁内存状态
        """
        self._store.pop(session_id, None)
        self._last_active.pop(session_id, None)

    def clean_expired_sessions(self):
        """
        【内存防泄漏机制】：清理超时的僵尸会话。
        可由 FastAPI 的 @app.on_event("startup") 配合 asyncio 开启后台定时任务调用。
        """
        now = time.time()
        expired_keys = [
            sid for sid, last_act in self._last_active.items()
            if now - last_act > self.session_timeout_sec
        ]
        for sid in expired_keys:
            self.delete_state(sid)


# ==========================================
# 暴露出全局单例对象
# ==========================================
session_store = StateManager()