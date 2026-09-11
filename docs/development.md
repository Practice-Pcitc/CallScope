# 本地运行与维护

直接编辑 `D:\Code\02-Projects\CallScope` 中的文件即保存到本地，不需要另存或复制“最终版”。
本次改动位于 `refactor/project-standards` 分支。检查 `git status`、`git diff` 后选择相关文件提交；commit 保存本地版本，push 才上传 GitHub。

后端依赖使用 uv.lock，前端使用 package-lock.json；新环境分别执行 `uv sync --frozen`、`npm ci`。
实际密钥仅放 backend/.env 或系统环境变量。不要上传 .env、数据库、扫描源码副本、缓存、依赖或日志。
前端开发代理访问后端；后端只监听 127.0.0.1。本项目没有公网部署配置，避免误将拥有本机文件读取权限的服务暴露出去。

## 环境问题

Windows PowerShell 执行策略阻止 npm.ps1 时使用 npm.cmd。
如果 pytest 系统临时目录权限异常，可用 `uv run pytest --basetemp=.pytest_cache/local-run`；该路径仅用于测试临时数据，会被 pytest 清理，不要放个人文件。
浏览器测试本机使用 Edge，CI 用 Playwright Chromium；浏览器流程使用模拟 API，不依赖外部模型。

## 常用检查

后端：`uv run ruff check app tests alembic`、`uv run ruff format --check app tests alembic`、`uv run pytest`。
前端：`npm run format:check`、`npm test`、`npm run build`、`npm run test:e2e`。
CI 自动执行这些检查。迁移测试也属于后端测试。

历史阶段交付文档保留用于追溯，当前运行方式以根 README 为准。

## Windows 安装依赖报 EPERM

若 `npm ci` 提示无法 unlink `esbuild.exe`，先在运行本项目 Vite 或测试的终端按 Ctrl+C，再重新安装。Windows 上运行中的可执行文件可能无法删除；`npm ci` 会重新创建依赖目录，因此不能与开发服务器同时运行。若停止后仍报错，再检查文件权限或安全软件占用。

项目通过 `frontend/.npmrc` 将 npm 缓存设为 `.npm-cache`，避免继承本机不可写的全局缓存位置；此目录已经被 Git 忽略。

依赖安装成功后，日常启动只需在 frontend 目录运行 `npm.cmd run dev`，不必每次都执行 `npm ci`。


## 可选配置与数据保留

默认运行无需创建 .env。需要调整配置时，首次可将 `backend/.env.example` 复制为 `backend/.env`；已有文件直接编辑，避免覆盖。
系统环境变量优先级最高，其次是 `backend/.env`，根目录 `.env` 作为兼容回退。
前端配置模板为 `frontend/.env.example`，其中只能放公开配置，不能放模型密钥。

默认 `CALLSCOPE_AI_PROVIDER=local` 根据已扫描证据生成分析，不调用外部模型。接入外部模型时，在 `backend/.env` 设置：

```dotenv
CALLSCOPE_AI_PROVIDER=openai-compatible
CALLSCOPE_AI_MODEL=your-model-name
CALLSCOPE_AI_API_KEY=
CALLSCOPE_AI_BASE_URL=https://your-provider.example/v1
```

将占位模型名和服务地址替换为实际值，并在本地填入密钥；这些配置文件禁止提交。启用后，所选拓扑及启用的源码片段会发送给模型服务。

原始 Prompt 和模型原始响应不持久化；结构化分析结果可能包含业务信息。启动时清理超过 `CALLSCOPE_AI_RETENTION_DAYS`（默认 30 天）的分析记录。
删除项目会级联移除数据库中的扫描与分析记录，不删除目标源码。

扫描更新后旧分析会标记过期。外部模型分析使用后台任务和状态查询，支持失败后重试；客户端取消等待不会取消服务器任务。
测试使用合成样例、本地证据 Provider 或 Fake 模型，默认不调用付费真实模型。完整规范核对记录见 [standards-review.md](standards-review.md)。
