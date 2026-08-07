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

扫描成功后可通过 Swagger 验证接口首层图、节点按需展开、上下游、合并拓扑和
源码证据。分析过程只读取源码，不会 import 或执行目标项目。
