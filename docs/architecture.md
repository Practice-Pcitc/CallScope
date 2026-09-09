# 架构与规范适配

CallScope 使用单仓库管理，正式工作目录为 `D:\Code\02-Projects\CallScope`。
已有项目保留仓库名称大小写、React 技术栈、`alembic/` 迁移目录。
这是对 RULES_IN.md 第 19 节“已有项目逐步调整”的应用。

## 调用方向

`api/routes → services → repositories → models`；分析服务组合 `analyzers`、`llm`、`prompts`。

| 目录 | 职责 |
| --- | --- |
| backend/app/api | HTTP 路由、请求依赖、响应 Schema |
| backend/app/services | 业务用例、事务、扫描和 AI 后台任务 |
| backend/app/repositories | 查询、flush、持久化；不 commit |
| backend/app/models | ORM 与稳定主键、审计时间 |
| backend/app/schemas | 请求、响应及模型上下文的明确类型 |
| backend/app/analyzers | 安全文件遍历、Python/Java 静态解析 |
| backend/app/llm | Provider、输出解析、引用校验、上下文预算 |
| backend/app/prompts | 独立版本化的系统提示、任务与模板 |
| backend/app/core | 环境配置、数据库、错误、结构化日志 |
| backend/tests | unit、api、integration；共享合成 fixtures |
| frontend/src/api | 唯一 HTTP 客户端、分析任务轮询 |
| frontend/src/hooks | React 复用逻辑，对应规范的 composables |
| frontend/src/pages | 路由页面，对应规范的 views |
| frontend/src/stores | Zustand 业务状态，对应 Pinia 职责 |
| frontend/src/components/layout | 公共页面布局 |
| frontend/tests | 单元与浏览器流程测试 |

未引入 Vue 的 script setup、Pinia、Vue Router；分别采用 TypeScript React 函数组件、Zustand、React Router。
没有登录、上传、RAG、MCP、Agent 工具循环，因此相关密码、上传、记忆和工具授权条目暂不适用。
模型调用只生成分析结果，不执行被扫描代码或模型生成代码。

外部模型任务提交后返回 ANALYZING，前端查询分析 ID。独立后台 Session 保存结果；进程重启将遗留任务标记 FAILED，支持重新生成。
当前后台任务运行在单个应用进程内，运行时不要开启多个 worker。持久队列和多用户部署属于后续功能。

每个 HTTP 请求产生独立 request_id，分析 ID 同时作为 run_id。日志只记录事件、状态、模型、Token、耗时与异常类型，省略请求正文、源码和异常文本。
