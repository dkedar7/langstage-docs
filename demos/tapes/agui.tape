# langstage-agui one-shots against the keyless rich-frame demo agent:
# preflight, a tool-using turn, the typed --json result, and a HITL pause (exit 2).
# Render from the repo root:  vhs demos/tapes/agui.tape

Output docs/assets/demos/agui.gif
Output docs/assets/demos/agui.webm

Require langstage-agui
Require jq

Set Shell "bash"
Set FontFamily "JetBrains Mono"
Set FontSize 18
Set Width 1100
Set Height 640
Set Padding 24
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms
Set Framerate 24
Set CursorBlink false
Env PYTHONIOENCODING "utf-8"
Env LANGSTAGE_SUPPRESS_LEGACY_NOTICE "1"

Hide
Type "cd $(mktemp -d) && clear" Enter
Show

Type "langstage-agui --demo=tools --verify" Sleep 400ms Enter
Sleep 3s

Type "langstage-agui --demo=tools -m 'use a tool'" Sleep 400ms Enter
Sleep 3.5s

Type "langstage-agui --demo=tools -m 'use a tool' --json | jq '{outcome, tool_calls}'" Sleep 400ms Enter
Sleep 4.5s

Type "clear" Enter
Type "langstage-agui --demo=tools -m 'ask me first'; echo \"exit code: $?\"" Sleep 400ms Enter
Sleep 4s
