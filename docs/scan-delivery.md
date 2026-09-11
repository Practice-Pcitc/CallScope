> 历史交付记录：接口、配置和验证命令以当前 README 和 architecture.md 为准。

# 阶段三：项目导入与安全文件扫描交付说明

## 1. 本阶段目标

实现本地项目导入、路径安全校验、Python 文件受限遍历、扫描任务持久化，以及前端
扫描进度展示。扫描过程只发现文件，不读取、导入或执行用户项目代码。

## 2. 已完成功能

### 项目管理

- 创建本地项目；
- 查询项目列表和详情；
- 按项目名称搜索；
- 拒绝相对路径、文件路径和不存在的目录；
- 使用规范化绝对路径去重；
- 删除项目记录但不删除磁盘源码；
- 扫描进行中禁止删除项目。

### 安全文件发现

- 只发现 `.py` 文件；
- 不读取、import 或执行源码；
- 不安装目标项目依赖；
- 不跟随文件或目录符号链接；
- 每个候选文件确认仍位于项目根目录内；
- 限制最大 Python 文件数、单文件大小和目录项数量；
- 单文件或目录失败不会终止其他文件；
- 错误摘要数量受限；
- 默认忽略：

```text
.git .idea .vscode node_modules venv .venv __pycache__
dist build coverage .pytest_cache .mypy_cache
```

### 扫描任务

- `PENDING → RUNNING → SUCCEEDED/FAILED` 状态；
- `DISCOVERY → VALIDATE → PERSIST → COMPLETED` 阶段；
- 进度、当前文件、发现/处理/跳过/失败数量；
- 文件级错误代码与消息；
- 项目总文件数和扫描状态更新；
- 每次扫描生成独立 revision ID；
- 成功后更新项目 active revision；
- 服务重启时将遗留任务标记失败；
- 同一项目禁止同时启动多个扫描任务。

### 前端

- 真实项目导入表单；
- 绝对路径输入与安全说明；
- 项目列表、搜索、状态和文件数量；
- 项目删除确认；
- 启动扫描和重新扫描；
- 扫描状态轮询；
- 进度、当前文件和统计指标；
- 跳过与失败记录查看；
- 明确提示 FastAPI 接口识别将在阶段四实现。

## 3. 数据库变化

新增 `projects`：

```text
id, name, root_path, language, framework, scan_status,
active_revision_id, total_files, total_endpoints,
created_at, updated_at
```

新增 `scan_tasks`：

```text
id, project_id, revision_id, status, stage, progress,
current_file, discovered_files, processed_files,
skipped_files, failed_files, error_message, error_summary,
started_at, finished_at, created_at
```

对应迁移：

```text
backend/alembic/versions/20260805_0002_projects_and_scan_tasks.py
```

## 4. 新增主要文件

```text
backend/app/
├── api/routes/
│   ├── projects.py
│   └── scans.py
├── analyzers/file_scanner.py
├── core/enums.py
├── models/
│   ├── project.py
│   └── scan_task.py
├── repositories/
│   ├── project_repository.py
│   └── scan_repository.py
├── schemas/
│   ├── project.py
│   └── scan.py
└── services/
    ├── project_service.py
    └── scan_service.py

backend/tests/
├── conftest.py
├── test_projects.py
└── test_scans.py

frontend/src/
├── api/
│   ├── projectApi.ts
│   └── scanApi.ts
├── components/project/
│   ├── ProjectImportModal.tsx
│   └── ScanStatusBanner.tsx
├── hooks/useScanPolling.ts
└── types/scan.ts
```

同时更新了项目页、工作台、Zustand store、数据库配置和全局样式。

## 5. API

```text
POST   /api/projects
GET    /api/projects?search=user&page=1&pageSize=20
GET    /api/projects/{project_id}
DELETE /api/projects/{project_id}
POST   /api/projects/{project_id}/scan
GET    /api/projects/{project_id}/scan-status
```

创建项目请求：

```json
{
  "name": "用户中心",
  "rootPath": "D:/work/user-service"
}
```

## 6. 配置

```text
CALLSCOPE_MAX_SCAN_FILES=10000
CALLSCOPE_MAX_FILE_SIZE_BYTES=2097152
CALLSCOPE_MAX_DIRECTORY_ENTRIES=50000
CALLSCOPE_SCAN_ERROR_LIMIT=100
```

这些限制可在 `.env` 中调整。

## 7. 验证结果

| 验证项 | 结果 |
| --- | --- |
| 两个 Alembic 迁移 | 通过 |
| 后端 pytest | 7 个测试通过 |
| 项目 CRUD | 通过 |
| 非法与重复路径 | 通过 |
| 忽略目录和文件大小限制 | 通过 |
| 后端 Ruff | 通过 |
| 前端 TypeScript 严格检查 | 通过 |
| 前端 Vite 生产构建 | 通过 |

测试使用临时真实目录和文件，但不会执行其中的 Python 内容。

## 8. 当前限制

- 扫描任务使用 FastAPI 应用内后台任务；服务重启时会标记失败，尚不自动恢复；
- 小项目扫描可能很快完成，轮询页面会直接看到完成状态；
- 尚未保存逐文件实体，只保存任务统计；
- 尚未读取源码或使用 Tree-sitter；
- 尚未识别 FastAPI 接口。

## 9. 下一阶段

阶段四只实现 FastAPI 接口识别：

1. Tree-sitter Python 初始化；
2. `FastAPI()`、`APIRouter()`；
3. 路由装饰器；
4. `include_router()` 与 prefix 合并；
5. 方法、路径、函数、参数、返回类型、tags、Depends；
6. `api_endpoints` 持久化；
7. 前端接口列表。

阶段四不提前实现跨文件函数调用图；调用关系属于阶段五、六。

