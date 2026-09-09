> 历史交付记录：接口、配置和验证命令以当前 README 和 architecture.md 为准。

# CallScope 基础拓扑 MVP 最终交付说明

## 交付范围

本次完成阶段五至阶段十，并与既有阶段一至阶段四整合为可运行 MVP：

1. 函数、类、方法、Service、Repository 和资源节点提取；
2. import、变量实例化、类型注解和 Depends 基础符号解析；
3. 图节点、图关系、接口入口映射的数据库持久化；
4. 接口首层拓扑和节点按需展开 API；
5. D3.js SVG 拓扑渲染及交互；
6. 节点展开、折叠、去重和重新布局；
7. 多接口合并、公共节点识别与链路高亮；
8. 节点详情、上下游、源码和关系证据；
9. 循环调用、错误文件和中等规模项目测试；
10. README、启动和验收说明。

## 静态分析结果

分析器不会 import、编译、运行或安装被扫描项目。Python 分析主要基于
Tree-sitter AST，Java/Spring 分析基于安全词法扫描与静态符号索引：

- `ROUTES_TO`：HTTP API 到路由函数；
- `CALLS`：函数或方法调用；
- `DEPENDS_ON`：FastAPI Depends；
- `VALIDATES` / `RETURNS`：Pydantic 输入输出；
- `QUERIES` / `WRITES`：SQLAlchemy 数据库操作；
- `USES_REDIS`：Redis 操作；
- `REQUESTS_EXTERNAL_API`：httpx / requests 调用；
- `CONTAINS`：类、方法和数据库表结构关系。

符号无法唯一确认时会保存 `UNRESOLVED` 节点，并降低置信度，不会伪装成确定结果。

## 图加载策略

第一次选择接口只返回 API 节点和路由函数。双击某个节点后，前端调用
`/children` 获取下一层增量节点和关系。折叠只修改前端可见集合，不删除后端结果。

多接口模式先合并多个入口的第一层图。继续展开时，前端继承入口标识并合并节点；
同一节点属于两个或更多入口时标记为公共节点。

## 数据库变更

Alembic 修订 `20260805_0004` 新增：

- `code_nodes`；
- `code_relations`；
- `endpoint_nodes`；
- 项目、修订版本、稳定键和方向查询索引。

重新扫描生成新的 `scan_revision_id`。只有完整扫描成功后才切换
`projects.active_revision_id`，扫描失败不会暴露半成品图。

## 自动验收结果

- Alembic 从空数据库升级至最新版本：通过；
- Ruff 后端静态检查：通过；
- pytest：17 个测试通过；
- 循环调用与单文件失败容错：通过；
- 120 文件、240 节点的规模分析预算测试：通过；
- 图首层、逐层展开、关系详情、源码和合并 API：通过；
- TypeScript 类型检查：通过；
- Vite 生产构建：通过。

生产构建存在第三方依赖包体积提示，但不影响运行。大型真实项目仍建议通过
分页、置信度筛选和按层展开控制前端节点量。

## 已知边界

- 当前支持 Python FastAPI 与 Java Spring Boot/Spring MVC 常见写法；
- Java 重载、运行时代理、反射和复杂泛型调用可能只能解析到部分链路；
- 动态反射、运行时注入、猴子补丁和复杂工厂模式可能生成低置信度或未解析节点；
- 数据库表推断依赖可静态识别的 `__tablename__`；
- 外部 URL 为动态表达式时只保留表达式证据；
- 没有执行目标项目，因此不会提供动态调用链；
- 未实现 MCP、AI Agent、RAG、代码问答、权限、多租户和云部署。

## 验收操作

启动前后端后，可导入 `backend/tests/fixtures/fastapi_sample` 或
`backend/tests/fixtures/spring_sample`。扫描完成后应看到 GET 与 POST 两个接口。
展开接口链路，可继续看到 Service、Repository 等节点；点击节点或关系可查看
源码和证据。
