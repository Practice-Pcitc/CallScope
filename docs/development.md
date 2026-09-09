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
