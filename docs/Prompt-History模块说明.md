# Codex Prompt History 模块

CallScope 现在使用 Codex 原生 `UserPromptSubmit` 生命周期 Hook，在文本 Prompt
发送给模型前将其保存到本机 SQLite。原有接口扫描、拓扑图和 AI 业务分析不受影响。

## 数据流

```text
用户提交 Prompt
  -> Codex UserPromptSubmit
  -> codex-hooks/prompt_hook.py
  -> backend/prompt_history.db
  -> FastAPI /api/prompt-history
  -> Vue3 Prompt Viewer
```

Hook 从 stdin JSON 读取 `prompt`、`cwd`、`session_id`、`turn_id`、`model` 和
`permission_mode`。项目 ID 通过 cwd 与现有 `callscope.db` 中的
`projects.root_path` 做最长路径匹配得到；Git 根目录、分支和提交均从当前 cwd
本地读取。获取不到的字段保存为 null。

## 安装 Hook

项目已提供 Windows 安装脚本：

```powershell
.\codex-hooks\install_hook.ps1
```

脚本更新 `C:\Users\当前用户\.codex\hooks.json`，并将旧配置备份为
`hooks.json.bak`。Codex 会要求审核新 Hook；打开 `/hooks` 后信任该定义。

关闭记录：

```text
PROMPT_HOOK_ENABLED=false
```

只对数据库副本做基础脱敏：

```text
PROMPT_REDACTION_ENABLED=true
```

Hook 不读取 `.env`、不执行 Prompt、不调用网络和 LLM，也不把 Prompt 写入日志。
所有异常都会在脚本内部捕获并以退出码 0 放行。

## 启动

后端：

```powershell
Set-Location backend
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

原 React 拓扑平台：

```powershell
Set-Location frontend
npm.cmd run dev
```

Vue3 Prompt Viewer：

```powershell
Set-Location prompt-viewer
npm.cmd run dev
```

访问地址：

```text
CallScope:      http://localhost:5173
Prompt Viewer:  http://localhost:5174/prompt-history
FastAPI Docs:   http://127.0.0.1:8000/docs
```

## API

```text
GET /api/prompt-history
GET /api/prompt-history/{id}
GET /api/prompt-history/stats
GET /api/prompt-history/projects
GET /api/projects/{project_id}/prompt-history
```

列表接口支持 `page`、`pageSize`、`projectId`、`projectName`、`keyword`、
`sessionId`、`startTime`、`endTime`。

## 数据与隐私

- Prompt 数据库：`backend/prompt_history.db`
- Hook 日志：`logs/prompt-hook.log`
- Prompt 数据库和日志均被 `.gitignore` 排除
- 不向远程服务器上传 Prompt
- `endpoint_ids` 和 `node_ids` 已预留，当前默认保存空数组
