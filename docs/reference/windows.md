# Windows and console output

LangStage runs on Windows, macOS and Linux. Windows consoles have a couple of
quirks that the family handles for you. This page says what to expect.

## Output never crashes on an unencodable character

A classic Windows console uses a legacy code page (cp1252 on Western systems), which
can't encode emoji, CJK text or many accented characters. A plain `print()` of such
text raises `UnicodeEncodeError`, and a CLI that crashes mid-reply loses the answer.

Every LangStage command prints user- and agent-supplied text (replies, tool
previews, approval prompts, config values, error lines) through
`langstage_core.console`. A character the console can't encode is written as a
backslash escape (`✓`, `\U0001f600`), and the rest of the line prints normally. This
covers `--show-config`, `python -m langstage_core.host`, `langstage-agui -m`,
`langstage config`, `langstage-cli`, and the `langstage-jupyter` preflights.

To get the real characters instead of escapes, switch the console to UTF-8:

<!-- snippet: skip -->
```bash
set PYTHONIOENCODING=utf-8        # cmd.exe
$env:PYTHONIOENCODING = "utf-8"   # PowerShell
export PYTHONIOENCODING=utf-8     # Git Bash
```

Windows Terminal with a UTF-8 profile, or Python's UTF-8 mode (`PYTHONUTF8=1`),
works too.

### In your own tools

If you build a surface or a script on top of core, use the same helpers:

<!-- snippet: run -->
```python
import sys
from langstage_core.console import safe_print, safe_write

safe_print("résumé ✓ 😀")                        # print() that escapes what the console can't encode
safe_write("note: done ✓\n", file=sys.stderr)    # the same for a raw write to any text stream
```

On a cp1252 console the first line prints as `résumé ✓ \U0001f600`.

## Other Windows behavior

- **Piped stdin in Git Bash.** `langstage-cli` treats a mintty / Git Bash terminal as a
  terminal (you get the interactive REPL), even though its stdin is technically a
  pipe. A real pipe (`echo hi | langstage-cli`) is still one single-shot message, and
  `<NUL` counts as empty stdin (an error), not a terminal.
- **Prompt files in "ANSI" encoding.** `langstage-cli -f prompt.txt` reads UTF-8 (a
  BOM is dropped), then falls back to the locale's legacy encoding, then cp1252.
- **VS Code sidecar input.** The sidecar reads its stdio commands as UTF-8 whatever
  the system locale, so non-ASCII chat input reaches your agent intact.
- **Paths.** A leading `~` in an agent spec or workspace root is expanded on every
  platform. Windows paths in `langstage.toml` work in single-quoted TOML strings
  (`root = 'C:\work\project'`) or with forward slashes.
- **Hermes' terminal tool** uses Git Bash on Windows (`langstage-hermes doctor`
  reports which `bash` it found).
- **Virtual environments.** Activate with `.venv\Scripts\activate` (cmd / PowerShell)
  or `. .venv/Scripts/activate` (Git Bash).
