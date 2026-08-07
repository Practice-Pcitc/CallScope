# CallScope Backend

## 开发启动

```powershell
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

服务默认运行在 `http://127.0.0.1:8000`，Swagger 文档位于
`http://127.0.0.1:8000/docs`。

## 测试

```powershell
uv run pytest
uv run ruff check .
```

扫描成功后可通过 Swagger 验证接口图、节点展开、合并拓扑、源码证据，以及
单接口/联合接口/节点影响 AI 分析。分析过程只读取源码，不会 import 或执行
目标项目。默认 `CALLSCOPE_AI_PROVIDER=local` 可离线运行；也可配置
`openai-compatible` Provider。
