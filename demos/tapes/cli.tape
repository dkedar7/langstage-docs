# langstage-cli against the keyless rich-frame demo agent: a streamed tool call,
# reasoning, and the human-in-the-loop approval menu.
# Render from the repo root:  vhs demos/tapes/cli.tape

Output docs/assets/demos/cli.gif
Output docs/assets/demos/cli.webm

Require langstage-cli

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

Type "langstage-cli -a langstage_core.demo.tools:graph --no-persist" Sleep 600ms Enter
Sleep 3s

Type "use a tool to look up the answer" Sleep 400ms Enter
Sleep 3s

Type "think it through first" Sleep 400ms Enter
Sleep 3s

Type "ask me before you act" Sleep 400ms Enter
Sleep 2.5s
# The approval menu is arrow-key driven; the first option is "Approve all actions".
Enter
Sleep 3s

Type "/q" Sleep 300ms Enter
Sleep 1s
