# AI 面试智能体

基于知识图谱和向量检索的 AI 面试系统，支持自动化技术面试和报告生成。

## 环境要求

- `uv`
- Python `3.12`
- 可用的 Neo4j 实例
- 阿里云 DashScope API Key 或兼容 OpenAI API 的 Key
- 本地模型文件和数据库目录

## 快速启动

### 1. 配置环境变量

先根据 `.env.example` 生成 `.env`，再补齐实际配置：

```bash
cp .env.example .env
```

关键字段示例：

```env
LLM_API_KEY=sk-your-api-key-here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
FAST_LLM_MODEL=qwen-turbo
SMART_LLM_MODEL=qwen-max
REPORT_LLM_MODEL=qwen-plus

NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password_here

CHROMA_PERSIST_DIR=./chroma_db_data
TARGET_SERVER_URL=http://127.0.0.1:8000/api/interview/report
INTERNAL_SECRET=your-secret-key
```

### 2. 同步 Python 3.12 环境

```bash
uv python install 3.12
uv sync --python 3.12
```

如果目录里已有旧的 `.venv`，`uv sync --python 3.12` 会把环境切到 Python 3.12。

### 3. 准备 Neo4j

确保一个可用的 Neo4j 实例，并让 `.env` 中的连接信息与之匹配。默认端口是 `7687`。

### 4. 启动服务

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
```

访问 `http://localhost:8081/docs` 查看 API 文档。

### 5. 运行测试

```bash
uv run python -m unittest discover -s tests
```

如需使用 `pytest`，可以执行：

```bash
uv run pytest
```

## 使用说明

### API 接口

- `POST /api/interview/start` - 开始面试
- `POST /api/interview/answer` - 提交答案
- `GET /api/interview/report/{session_id}` - 获取面试报告

### 切换模型

如需使用 OpenAI、千问或其他兼容 OpenAI API 的模型，直接修改 `.env` 里的
`FAST_LLM_MODEL`、`SMART_LLM_MODEL`、`REPORT_LLM_MODEL` 即可，无需改源码。
其中 `FAST_LLM_MODEL` 同时承担意图识别与题级评分。

## 目录结构

```text
├── app/               # FastAPI 应用
│   ├── api/           # API 路由
│   ├── core/          # 核心逻辑
│   ├── db/            # Neo4j / Chroma 访问层
│   ├── models/        # 请求与状态模型
│   ├── services/      # 业务服务
│   └── main.py        # 入口文件
├── chroma_db_data/    # 向量库数据
├── data_source/       # 题库与数据源
├── tests/             # 回归测试
├── .python-version    # Python 版本固定到 3.12
└── pyproject.toml     # uv 项目配置
```

## 常见问题

**Q: Neo4j 连接失败？**
A: 确认 Neo4j 已启动，并检查 `.env` 中的 `NEO4J_URI`、账号和密码是否正确。

**Q: 旧 `.venv` 还是 Python 3.10？**
A: 在 `ai/` 目录重新执行 `uv sync --python 3.12`，让 uv 重新建立环境。

**Q: API Key 无效？**
A: 检查 `.env` 文件中的 `LLM_API_KEY` 和 `LLM_BASE_URL` 是否正确。
