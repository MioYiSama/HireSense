# AI 面试智能体

基于知识图谱和向量检索的 AI 面试系统，支持自动化技术面试和报告生成。

## 环境要求

- Python 3.8+
- Docker & Docker Compose
- 阿里云 DashScope API Key（或 OpenAI API Key）
- 模型文件，本地数据库都在项目目录下（因为文件过大所以使用qq传输）

## 快速启动

### 0. 设置环境信息
根据.env.example 的要求 设置.env

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 Neo4j 数据库

```bash
docker-compose up -d
```

访问 http://localhost:7474 验证 Neo4j 是否启动成功（账号: neo4j, 密码: password）

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要配置：

```env
# 大模型 API（必填）
LLM_API_KEY=sk-your-api-key-here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# Neo4j 数据库（使用 docker-compose 默认配置）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# 向量库路径
CHROMA_PERSIST_DIR=./chroma_db_data

# 报告推送地址（可选）
TARGET_SERVER_URL=http://127.0.0.1:8000/api/interview/report
INTERNAL_SECRET=your-secret-key
```

### 4. 构建知识图谱

将面试题库文件放入 `data_source/` 目录，然后运行：

```bash
python GraphRag_Builder.py
```

### 5. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

访问 http://localhost:8000/docs 查看 API 文档

## 使用说明

### API 接口

- `POST /api/interview/start` - 开始面试
- `POST /api/interview/answer` - 提交答案
- `GET /api/interview/report/{session_id}` - 获取面试报告

### 切换模型

如需使用 OpenAI 或其他模型，修改 `app/dependencies.py` 中的模型配置。

## 目录结构

```
├── app/                # FastAPI 应用
│   ├── api/           # API 路由
│   ├── core/          # 核心逻辑
│   ├── services/      # 业务服务
│   └── main.py        # 入口文件
├── data_source/       # 面试题库数据
├── neo4j_data/        # Neo4j 数据持久化
├── chroma_db_data/    # 向量库数据
└── GraphRag_Builder.py # 知识图谱构建脚本
```

## 常见问题

**Q: Neo4j 连接失败？**
A: 确保 Docker 容器已启动，检查端口 7687 是否被占用

**Q: API Key 无效？**
A: 检查 `.env` 文件中的 `LLM_API_KEY` 是否正确填写

**Q: 知识图谱为空？**
A: 确保 `data_source/` 目录有数据文件，重新运行 `GraphRag_Builder.py`
