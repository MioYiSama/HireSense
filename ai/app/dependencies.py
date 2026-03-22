import os
from functools import lru_cache
from app.core.config import NLI,EMBEDDING_MODEL,NEO4J_DATA,CHROMA_DATA,BGE_RERANKER
from chromadb.utils import embedding_functions
from langchain_openai import ChatOpenAI
from sentence_transformers import CrossEncoder

from app.core.history_manager import HistoryManager
# 引入之前写好的所有底层设施和服务
from app.db.neo4j_client import Neo4jClient
from app.db.chroma_client import ChromaClient
from app.services.evaluator import Evaluator,PruningStrategy
from app.services.intent_router import IntentGateway
from app.services.llm_generator import LLMGenerator
from app.services.resume_analyzer import ResumeAnalyzer
from app.services.Agent_flows import AgentFlow
from app.services.report_generator import FinalReport
from app.core.config import settings


os.environ["DASHSCOPE_API_KEY"] = settings.LLM_API_KEY
os.environ["DASHSCOPE_BASE_URL"] = settings.LLM_BASE_URL
# ==========================================
# 1. 核心基础设施：全局单例 (Singletons)
# 绝对保证只在 FastAPI 启动时加载一次！
# ==========================================


def _normalize_neo4j_uri(uri: str) -> str:
    """
    Windows 本地 Neo4j 使用 localhost 时会触发明显的回环解析延迟，优先固定到 IPv4。
    """
    if "://localhost" in uri:
        return uri.replace("://localhost", "://127.0.0.1", 1)
    return uri


#  Embedding 模型
bge_embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=str(EMBEDDING_MODEL),
            device="cpu"  # 如果服务器有显卡，请务必改为 "cuda" 以获得 10 倍以上加速
        )


# sts 模型
sts_model = CrossEncoder(str(BGE_RERANKER), device="cpu")

# NLI 模型
nli_model = CrossEncoder(str(NLI), device="cpu")

# 数据库客户端
neo4j_client = Neo4jClient(
    uri=_normalize_neo4j_uri(settings.NEO4J_URI),
    user=settings.NEO4J_USER,
    password=settings.NEO4J_PASSWORD
)
chroma_client = ChromaClient(persist_directory=str(CHROMA_DATA), bge_embedding_function=bge_embedding_function)

# 本地打分小模型（加载极其耗时，必须全局唯一）
# 如果有独立显卡，务必将 device 改为 "cuda"
evaluator = Evaluator(sts_model=sts_model,nli_model=nli_model)

# . 大语言模型实例
# 极速小模型（用于意图识别，追求 200ms 的极致低延迟，Temperature 锁死 0）
fast_llm = ChatOpenAI(
    model=settings.FAST_LLM_MODEL,
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
    temperature=0.1
)

# 聪明大模型（用于聊天生成、简历解析、出表总结，需要强大的逻辑推理能力）
smart_llm = ChatOpenAI(
    model=settings.SMART_LLM_MODEL,
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
    temperature=0.1
)

llm_plus = ChatOpenAI(
    model=settings.REPORT_LLM_MODEL,
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
    temperature=0.1
)

# ==========================================
# 2. 领域服务组装 (Domain Services)
# ==========================================
intent_gateway = IntentGateway(fast_llm=fast_llm)
llm_generator = LLMGenerator(llm=smart_llm, fast_llm=fast_llm)
resume_analyzer = ResumeAnalyzer(llm=smart_llm)
report_generator = FinalReport(llm=llm_plus)
history_manager = HistoryManager()
strategy        = PruningStrategy()


# ==========================================
# 3. 暴露给 FastAPI 的依赖注入函数 (Dependency Providers)
# ==========================================

def get_neo4j_client() -> Neo4jClient:
    return neo4j_client

def get_resume_analyzer() -> ResumeAnalyzer:
    return resume_analyzer

def get_report_generator():
    return report_generator

def get_agent_workflow() -> AgentFlow:
    """
    【终极缝合】：组装 AgentWorkflow 所需的所有零部件。
    当 API 路由调用 Depends(get_agent_workflow) 时，FastAPI 会自动执行此函数，
    将组装好的完整机器递给 API。
    """
    return AgentFlow(
        intent_router_=intent_gateway,
        evaluator_=evaluator,
        neo4j_client_=neo4j_client,
        chroma_client_=chroma_client,
        llm_gen=llm_generator,
        history_manager=history_manager,
        strategy= strategy,
        resume_analyzer=resume_analyzer,
    )
