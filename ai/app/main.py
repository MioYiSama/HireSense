import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入 API 路由
from app.api import endpoints

# 导入底层单例客户端，用于生命周期管理
from app.dependencies import neo4j_client


# ==========================================
# 1. 现代 FastAPI 生命周期管理 (Lifespan)
# 替代已被弃用的 @app.on_event("startup"/"shutdown")
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    控制整个应用从启动到销毁的生命周期。
    """
    # ------------------[启动阶段 Startup] ------------------
    # 由于依赖注入文件 (dependencies.py) 被导入，向量引擎、
    # LLM 评分器和图谱客户端此时已经自动加载到内存中了。
    print("[System] AI 面试智能体后端服务开始启动...")
    print("[System] LLM 评分器与向量引擎已成功挂载入内存。")

    # 可以在这里加入一些数据库连通性自检代码 (Health Check)
    # await neo4j_client.driver.verify_connectivity()

    yield  # 阻断点：此时服务正式对外接收 HTTP 请求

    # ------------------ [销毁阶段 Shutdown] ------------------
    print("[System] 收到终止信号，正在执行优雅停机 (Graceful Shutdown)...")

    # 核心：必须显式关闭 Neo4j 的底层 TCP 长连接池，否则会导致系统资源泄漏
    try:
        await neo4j_client.close()
        print("[System] Neo4j 图数据库连接池已安全释放。")
    except Exception as e:
        print(f"[System] Neo4j 连接池释放异常: {e}")


# ==========================================
# 2. FastAPI 应用实例初始化
# ==========================================
app = FastAPI(
    title="AI Interview Agentic API",
    description="基于 GraphRAG 与双轨认知模型的高拟真 AI 面试官引擎",
    version="1.0.0",
    lifespan=lifespan  # 挂载生命周期管理器
)

# ==========================================
# 3. CORS 跨域中间件配置 (前后端分离刚需)
# ==========================================
# 允许所有的跨域请求。在真实生产上线时，请将 allow_origins 替换为前端实际的域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # 允许 POST, PUT, OPTIONS 等所有方法
    allow_headers=["*"],  # 允许所有 Header (如 JWT Token, Content-Type)
)

# ==========================================
# 4. 挂载业务路由 (Routers)
# ==========================================
app.include_router(endpoints.router, tags=["Interview Core Flow"])

# ==========================================
# 5. 本地调试启动入口
# ==========================================
if __name__ == "__main__":
    # 使用 Uvicorn 作为 ASGI 服务器启动
    # reload=True 支持代码修改后热更新，仅限开发环境使用
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
