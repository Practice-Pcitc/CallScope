# CallScope（调用视界）

CallScope 是一个面向 FastAPI 与 Spring Boot 项目的接口调用拓扑静态分析平台。它从 HTTP
接口入口出发，按需展示路由函数、Service、Repository、数据库、Redis 和外部
HTTP 调用，并为每条关系保留源码位置、调用证据与分析置信度。

当前基础拓扑 MVP 已完成。本版本不包含 MCP、AI Agent、RAG 和云端部署。

## 已实现能力

- 导入、查询和移除本地项目；移除记录不会删除用户源码；
- 自动识别 Python/FastAPI 与 Java/Spring 项目；
- 安全遍历 Python、Java 文件，限制文件数量、目录项和单文件大小；
- 忽略虚拟环境、构建目录、缓存目录和版本控制目录；
- 扫描任务、实时进度、错误摘要与重新扫描；
- 基于 Tree-sitter AST 识别 FastAPI、APIRouter、路由装饰器和多层
  `include_router()`；
- 提取请求方法、完整路径、参数、返回模型、tags、Depends 和源码位置；
- 识别 Spring `@RestController`、类/方法级映射、请求参数和返回类型；
- 解析 Java Controller → Service → Mapper/Repository 的基础调用关系；
- 提取函数、类、类方法、Service、Repository 和 Pydantic Model；
- 基于 import、类型注解、变量实例化和 Depends 做基础符号解析；
- 识别普通调用、依赖、校验、返回、数据库读写、Redis 和外部 HTTP 调用；
- 无法确定的目标保存为 `UNRESOLVED`，并按
  `CONFIRMED / HIGH / MEDIUM / LOW` 标记置信度；
- 使用 SQLAlchemy 2 持久化带扫描修订版本的节点、关系和接口入口映射；
- 使用 NetworkX 进行图层级和循环安全处理；
- D3.js SVG 分层拓扑、箭头、缩放、平移和节点拖拽；
- 双击节点逐层加载，前端折叠后代节点，避免一次加载整张图；
- 多接口选择、图合并、节点和边去重、公共节点标识；
- 节点邻接高亮、无关节点弱化；
- 查看节点上下游、函数签名、源码片段和关系证据；
- 默认只展示 `CONFIRMED` 与 `HIGH`，可切换显示较低置信度关系。

## 技术栈

- 后端：Python 3.11+、FastAPI、SQLAlchemy 2、Pydantic 2、Alembic、
  Tree-sitter、NetworkX；
- 数据库：开发环境默认 SQLite，已预留 PostgreSQL 驱动；
- 前端：React 19、TypeScript、Vite、D3.js、Zustand、Axios、
  React Router、Ant Design。

## 启动

后端：

```powershell
Set-Location backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

前端（另一个终端）：

```powershell
Set-Location frontend
npm.cmd install
npm.cmd run dev
```

打开 `http://localhost:5173`。Swagger 位于
`http://127.0.0.1:8000/docs`。

如果依赖已经安装在仓库自带环境中，也可以使用：

```powershell
Set-Location backend
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

## 使用流程

1. 在项目页点击“导入本地项目”；
2. 填写名称和 FastAPI 或 Spring Boot 项目的绝对路径；
3. 启动扫描并等待状态变为“扫描完成”；
4. 在左侧单选或多选接口；
5. 中间画布显示接口到路由函数的第一层关系；
6. 双击带 `+数量` 的节点继续展开，双击已展开节点进行折叠；
7. 点击节点或关系，在右侧查看上下游、源码和调用证据；
8. 需要排查不确定关系时，打开“全部置信度”。

## 验证

后端：

```powershell
Set-Location backend
uv run alembic upgrade head
uv run ruff check app tests
uv run pytest
```

前端：

```powershell
Set-Location frontend
npm.cmd run typecheck
npm.cmd run build
```

## 主要 API

```text
POST   /api/projects
GET    /api/projects
GET    /api/projects/{project_id}
DELETE /api/projects/{project_id}

POST   /api/projects/{project_id}/scan
GET    /api/projects/{project_id}/scan-status

GET    /api/projects/{project_id}/endpoints
GET    /api/projects/{project_id}/endpoints/{endpoint_id}

GET    /api/projects/{project_id}/endpoints/{endpoint_id}/graph
POST   /api/projects/{project_id}/graph/combined
GET    /api/projects/{project_id}/nodes/{node_id}/children
GET    /api/projects/{project_id}/nodes/{node_id}/upstream
GET    /api/projects/{project_id}/nodes/{node_id}/downstream
GET    /api/projects/{project_id}/nodes/{node_id}
GET    /api/projects/{project_id}/nodes/{node_id}/source
GET    /api/projects/{project_id}/relations/{relation_id}
```

## 配置

复制根目录 `.env.example` 为 `.env`。默认数据库：

```text
sqlite:///./callscope.db
```

PostgreSQL 示例：

```text
postgresql+psycopg://user:password@localhost:5432/callscope
```

## 文档

- [需求与架构方案](docs/阶段一-需求与架构方案.md)
- [项目骨架交付说明](docs/阶段二-项目骨架交付说明.md)
- [项目导入与文件扫描](docs/阶段三-项目导入与文件扫描交付说明.md)
- [FastAPI 接口识别](docs/阶段四-FastAPI接口识别交付说明.md)
- [Java Spring 支持说明](docs/Java-Spring支持说明.md)
- [MVP 最终交付说明](docs/MVP-最终交付说明.md)
