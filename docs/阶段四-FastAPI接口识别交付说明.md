# 阶段四：FastAPI 接口识别交付说明

## 1. 本阶段目标

使用 Tree-sitter Python 读取阶段三发现的源码文件，识别项目中实际挂载到
`FastAPI` 应用的 HTTP 接口，保存结构化接口元数据，并在前端展示可搜索、筛选和
多选的接口列表。

本阶段不分析普通函数调用关系，也不生成调用拓扑节点和边。

## 2. 分析方式

Tree-sitter 是源码结构分析的主入口：

1. 将 Python 源码解析为 Tree-sitter 语法树；
2. 从语法树提取 import、常量、赋值、类、装饰器、函数参数和调用表达式；
3. 建立模块 import alias 映射；
4. 识别 FastAPI app 与 router 变量；
5. 建立 router include 有向图；
6. 从每个 `FastAPI()` 根节点传播 prefix 与 tags；
7. 只生成可从 app 根节点到达的接口；
8. 将接口写入当前扫描 revision。

`ast.literal_eval` 只用于安全解码字符串、列表等字面量，不用于解析程序结构，也不会
执行源码。

## 3. 当前支持范围

### FastAPI 对象

- `FastAPI()`；
- `APIRouter()`；
- 从 `fastapi` 直接导入和 alias 导入；
- `import fastapi` 后的属性调用。

### 路由

- `@app.get/post/put/delete/patch/options/head()`；
- `@router.get/post/put/delete/patch/options/head()`；
- `@router.api_route(..., methods=[...])`；
- 同一函数多个路由装饰器；
- `include_router()`；
- 跨文件 router import；
- 相对 import；
- 多层 router 嵌套；
- router prefix；
- include prefix；
- 路由 tags、router tags 和 include tags 合并；
- router include 循环检测。

### 接口元数据

- HTTP 方法；
- 最终完整路径；
- 函数名和 qualified name；
- 模块和相对文件路径；
- 装饰器开始行和函数结束行；
- `summary`；
- docstring 首行回退；
- `response_model` 或返回类型；
- tags；
- 参数名称、类型、位置、默认值和必填状态；
- `Depends` provider 与解析置信度。

### 参数位置

- 路径模板参数 → `PATH`；
- `Query/Path/Body/Header/Cookie/Form/File`；
- `Depends` → `DEPENDENCY`；
- Pydantic `BaseModel` → `BODY`；
- 其他普通参数 → `QUERY`。

## 4. Prefix 解析

示例：

```python
app.include_router(api_router, prefix="/api")
api_router = APIRouter(prefix="/v1")
api_router.include_router(user_router, prefix="/accounts")
user_router = APIRouter(prefix="/users")

@user_router.get("/{user_id}")
def get_user(user_id: int):
    ...
```

最终接口路径：

```text
GET /api/v1/accounts/users/{user_id}
```

同一个 router 被多个父 router 挂载时，会为每个实际挂载路径生成接口；相同方法、
路径和函数会去重。

## 5. 数据库变化

新增 `api_endpoints`：

```text
id, project_id, scan_revision_id,
http_method, path,
function_name, qualified_name, module_name,
file_path, start_line, end_line,
summary, tags, parameters, response_type,
dependencies, metadata, created_at
```

对应迁移：

```text
backend/alembic/versions/20260805_0003_api_endpoints.py
```

查询接口只读取项目的 `active_revision_id`，重新扫描期间不会读取半成品。

## 6. 新增主要文件

```text
backend/app/
├── analyzers/
│   ├── tree_sitter_parser.py
│   └── fastapi_analyzer.py
├── api/routes/endpoints.py
├── models/api_endpoint.py
├── repositories/endpoint_repository.py
├── schemas/endpoint.py
└── services/endpoint_service.py

backend/tests/
├── fixtures/fastapi_sample/
├── test_fastapi_analyzer.py
└── test_endpoints.py

frontend/src/
├── api/endpointApi.ts
├── stores/endpointStore.ts
└── types/endpoint.ts
```

同时更新了接口列表、详情面板、扫描阶段、图画布空状态和全局样式。

## 7. API

### 接口列表

```http
GET /api/projects/{project_id}/endpoints
```

查询参数：

```text
search
httpMethod
module
tag
page
pageSize
```

### 接口详情

```http
GET /api/projects/{project_id}/endpoints/{endpoint_id}
```

## 8. 前端交互

- 按路径或函数名搜索；
- 按 HTTP 方法筛选；
- 按模块筛选；
- 单选、多选、全选和清空；
- 方法、路径、摘要、文件和行号展示；
- 右侧展示接口信息、参数、返回类型和 Depends；
- 重新扫描成功后自动切换 revision 并刷新接口列表；
- 中间画布明确提示调用拓扑将在阶段七接入。

## 9. 验证结果

| 验证项 | 结果 |
| --- | --- |
| 三个 Alembic 迁移 | 通过 |
| 后端 pytest | 9 个测试通过 |
| Tree-sitter API 与字节范围 | 通过 |
| 跨文件相对 import | 通过 |
| 两层 include_router | 通过 |
| 多段 prefix 合并 | 通过 |
| GET/POST 路由 | 通过 |
| PATH/QUERY/BODY/DEPENDENCY | 通过 |
| Pydantic 请求模型 | 通过 |
| tags 与 Depends | 通过 |
| 接口列表和详情 API | 通过 |
| Ruff | 通过 |
| TypeScript 严格检查 | 通过 |
| Vite 生产构建 | 通过 |

## 10. 当前限制

- 尚不支持在复杂 app factory 局部作用域中创建并返回 app/router；
- 动态拼接的 path/prefix 会标记为动态表达式，不能保证最终运行时值；
- 不执行 Python，因此运行时条件路由、反射和 monkey patch 无法确认；
- Pydantic 参数识别优先覆盖直接模型类型和 import alias；
- 接口数量统计只包含可从已识别 `FastAPI()` 根节点到达的 router；
- 旧扫描 revision 暂时保留，后续加入清理策略；
- 尚未创建 API、函数和调用关系图节点。

## 11. 下一阶段

阶段五只实现函数与方法事实：

1. 提取函数、类和类方法；
2. 提取 import；
3. 提取函数调用点；
4. 创建 `code_nodes`；
5. 创建 `code_relations`；
6. 保存定义和调用源码证据；
7. 建立 `API → ROUTE_FUNCTION`；
8. 为后续符号解析保留未解析调用。

跨文件对象类型推断和完整符号解析属于阶段六。

