# API 与版本迁移

所有业务接口使用 `/api/v1`；OpenAPI 页面 `/docs` 不属于业务资源。
该次整理同步更新前端，旧 `/api` 路径不再提供，请前后端一起更新。若原环境设置了 CALLSCOPE_API_PREFIX=/api，请移除或改为 /api/v1。
错误格式为 `{ "error": { "code": "...", "message": "...", "details": null, "requestId": "..." } }`。
Python 字段使用 snake_case，JSON 保留 camelCase 约定。所有输出时间为 UTC ISO 8601（含时区）。
列表返回 `data.items` 和 `data.pagination`（page、pageSize、total）；图邻接关系属于一个图资源，返回 nodes/edges，不套用列表分页。

| 方法 | `/api/v1` 后的路径 | 用途 |
| --- | --- | --- |
| GET | /health | 健康检查 |
| GET / POST | /projects | 分页项目列表 / 导入 |
| GET / DELETE | /projects/{project_id} | 项目详情 / 删除记录 |
| POST | /projects/{project_id}/scans | 启动后台扫描 |
| GET | /projects/{project_id}/scans/latest | 最新扫描状态 |
| GET | /projects/{project_id}/endpoints | 分页接口列表 |
| GET | /projects/{project_id}/endpoints/{endpoint_id} | 接口详情 |
| GET | /projects/{project_id}/endpoints/{endpoint_id}/graphs | 第一层图 |
| POST | /projects/{project_id}/graphs/combined | 合并图 |
| GET | /projects/{project_id}/nodes/{node_id} | 节点详情 |
| GET | /projects/{project_id}/nodes/{node_id}/children | 下游邻接图 |
| GET | /projects/{project_id}/nodes/{node_id}/upstream | 上游邻接图 |
| GET | /projects/{project_id}/nodes/{node_id}/downstream | 下游邻接图 |
| GET | /projects/{project_id}/nodes/{node_id}/source | 源码 |
| GET | /projects/{project_id}/relations/{relation_id} | 关系证据 |
| POST | /projects/{project_id}/endpoints/{endpoint_id}/ai-analyses | 单接口分析 |
| POST | /projects/{project_id}/endpoints/combined-ai-analyses | 联合分析 |
| POST | /projects/{project_id}/nodes/{node_id}/impact-ai-analyses | 节点影响分析 |
| GET | /ai-analyses/{analysis_id} | 查询分析状态与结果 |
| POST | /ai-analyses/{analysis_id}/regenerate | 再生成 |

外部模型返回 ANALYZING 后每秒查询一次，直到 COMPLETED、FAILED 或 STALE；客户端离开页面会取消等待，不会取消服务器任务。服务端每次调用有超时与有限重试，重启后任务可重试。

原 scan、scan-status、graph、ai-analysis、ai-combined-analysis、ai-impact-analysis 路径分别迁移为上表中的复数资源路径。
