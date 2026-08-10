# CallScope Codex Prompt Hook

This module records four Codex lifecycle events:

- `SessionStart`: creates a local session record.
- `UserPromptSubmit`: stores the original textual Prompt.
- `PostToolUse`: stores tool name, status, duration and non-sensitive identifiers.
- `SessionEnd`: closes the session and records the end reason when available.

Prompt text is stored in `prompt_records`, session summaries in
`codex_sessions`, and minimal tool audit events in `codex_tool_events`.

## Privacy and failure behavior

- Records are stored only in `backend/prompt_history.db` by default.
- The Prompt is treated only as a string and is never executed.
- The hook does not call a network service or an LLM.
- It writes no Prompt text to logs.
- Tool inputs and tool outputs are deliberately not persisted.
- Every exception is caught and the process exits with code `0` without stdout,
  so audit failures do not intentionally block Codex.
- Set `PROMPT_HOOK_ENABLED=false` to disable recording.
- Set `PROMPT_REDACTION_ENABLED=true` to redact common token/password forms in
  the stored copy. The Prompt sent to Codex is not changed.

## Install on Windows

Run:

```powershell
.\codex-hooks\install_hook.ps1
```

Then open `/hooks` in Codex and trust the new hook definition. The installer
preserves other hook event groups but replaces the user-level groups for
`SessionStart`, `UserPromptSubmit`, `PostToolUse`, and `SessionEnd` with the
CallScope recorder. Each handler uses a 3-second timeout so it stays within
Codex's stricter `SessionEnd` lifecycle limit.

Configuration can be overridden with:

```text
PROMPT_HOOK_ENABLED
PROMPT_REDACTION_ENABLED
PROMPT_HISTORY_DB
PROMPT_HOOK_LOG
CALLSCOPE_PROJECT_DB
```
