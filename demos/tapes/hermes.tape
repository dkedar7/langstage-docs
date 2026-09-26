# langstage-hermes keyless flow: the scripted demo closes the reflection -> skill
# loop, then `search` finds the recorded session and `skills list` shows the library.
# HERMES_HOME points at a throwaway temp dir so nothing touches a real home.
# Render from the repo root:  vhs demos/tapes/hermes.tape

Output docs/assets/demos/hermes.gif
Output docs/assets/demos/hermes.webm

Require langstage-hermes

Set Shell "bash"
Set FontFamily "JetBrains Mono"
Set FontSize 15
Set Width 1200
Set Height 760
Set Padding 24
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms
Set Framerate 24
Set CursorBlink false
Env PYTHONIOENCODING "utf-8"
Env LANGSTAGE_SUPPRESS_LEGACY_NOTICE "1"

Hide
Type "export HERMES_HOME=$(mktemp -d) && cd $HERMES_HOME && clear" Enter
Show

Type "langstage-hermes demo" Sleep 400ms Enter
# Wait for the shell prompt to come back (the demo builds a real agent first).
Wait@120s
Sleep 3s

Type "clear" Enter
Type "langstage-hermes search 'python'" Sleep 400ms Enter
Sleep 3.5s

Type "langstage-hermes skills list | head -n 12" Sleep 400ms Enter
Sleep 4s
