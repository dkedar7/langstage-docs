# Troubleshooting

The errors people hit first, what each one means, and the fix. Every LangStage
command prints an error as one line and exits non-zero, so the message you see is
usually the whole story. The examples below come from `langstage-cli`. Other stages
word some of them a little differently, but the causes and fixes are the same.

Before anything else, run the preflight for your stage. It loads your agent and runs
one real turn, so most of the problems on this page show up there first:

<!-- snippet: skip -->
```bash
langstage check --live          # web
langstage-cli --verify          # terminal
langstage-hermes doctor         # reference agent: also checks provider packages and keys
```

[Every stage's preflight](installation.md#preflight-your-own-agent) is listed on the
Installation page.

## No agent specified

<!-- snippet: skip -->
```text
Error: No agent specified.
```

The command doesn't know which graph to run. Pass `-a path/to/agent.py:graph`, set
`LANGSTAGE_AGENT_SPEC`, or put the spec under `[agent] spec` in `langstage.toml`. To
check that the install works before you have an agent, every stage has a keyless
`--demo` ([list](installation.md#check-it-works-no-key-needed)).

The web app is different: with no agent it falls back to a built-in default agent,
which needs an extra:

<!-- snippet: skip -->
```text
Error: The built-in default agent needs the 'deepagents' extra: pip install "langstage[deepagents]".
```

Install the extra and set `ANTHROPIC_API_KEY`, or use `langstage run --demo`, or
point `--agent` at your own graph.

## The agent spec won't load

A spec is `file.py:variable` or `package.module:variable`
([formats](quickstart.md#2-point-any-stage-at-it-with-one-spec-string)). Each part
can fail on its own:

| You see | It means | Fix |
|---|---|---|
| `FileNotFoundError: Agent file not found: …` | The path is resolved against the current directory, or against the TOML file it's written in. | Use a path relative to where you run the command, or an absolute one. `~` works on every platform. |
| `ModuleNotFoundError: No module named 'my_pkg'` | A module spec, and the package isn't importable from this Python. | Install the package into the same environment as LangStage, or use a file path instead. |
| `ModuleNotFoundError: No module named 'langchain_openai'` | The agent file loaded, but one of **its** imports is missing. | Install the agent's own dependencies. LangStage only brings `langgraph`. |
| `AttributeError: Module '…' has no attribute 'graph'` | The file loaded, but the variable isn't called `graph`. | Name it in the spec: `agent.py:agent`. |
| `Invalid agent spec 'agent.py'` (web app) | The web app needs the `:variable` part. | Add it: `agent.py:graph`. |

If loading works but something later fails, re-run with `-v` (or set `LANGSTAGE_DEBUG=1` for the
web app) to see the full traceback.

## A provider package is missing

<!-- snippet: skip -->
```text
Error: ImportError: Initializing ChatAnthropic requires the langchain-anthropic package.
```

`init_chat_model("anthropic:…")`, `"openai:…"` and the like each need that
provider's LangChain package. Install the one the message names
(`pip install langchain-anthropic`). `langstage-hermes doctor` catches this
without running a turn, for any provider LangChain knows.

## No API key (it may say "Connection error")

With no key set, the Anthropic client doesn't say the key is missing. It fails to
send the request, retries for about a minute, then gives up with a connection error.
Since langstage-core 1.0.69 the error names the variable that isn't set:

<!-- snippet: skip -->
```text
Error: AnthropicConnectionError: Connection error. (hint: ANTHROPIC_API_KEY is not set)
```

Set that variable and run again. The hint covers the common providers
(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `GOOGLE_API_KEY`, and
so on). It prints only the variable's name, never a key. With an older core you see
the same line without the hint. Keys are ordinary environment variables: LangStage
doesn't store them, and `--show-config` doesn't print them. A wrong key, as opposed
to a missing one, gives the provider's own `401` / authentication error.

The static `langstage check` (without `--live`) needs no key, so it passes either way.
Add `--live` to prove a real turn works.

## The port is already in use

The web app and the AG-UI server listen on a port (8050 for the web app), and only
one process can hold it:

<!-- snippet: skip -->
```text
Error: port 8050 is already in use on 127.0.0.1; pass --port or set LANGSTAGE_PORT
error: cannot serve at http://localhost:8050/: Only one usage of each socket address …
```

The first line is the web app (since langstage 0.14.3), the second `langstage-agui`.
On Linux and macOS the `langstage-agui` message ends in `Address already in use`
instead. Another LangStage, or anything else, already has the port. Stop it, or
pick another port:

<!-- snippet: skip -->
```bash
langstage run --demo --port 8051
LANGSTAGE_PORT=8051 langstage run --demo     # or [server] port in langstage.toml
```

## Odd characters on Windows

On a classic Windows console you may see `\U0001f600` or `✓` where an emoji or
symbol should be. That's on purpose: LangStage escapes a character the console's code
page can't encode instead of crashing mid-reply. Switch the console to UTF-8 to get
the real characters:

<!-- snippet: skip -->
```bash
$env:PYTHONIOENCODING = "utf-8"   # PowerShell
```

[Windows and console output](../reference/windows.md) has the other shells and the
other Windows behavior.

## A run exits with code 2

Exit code `2` isn't a failure. The agent paused on a human-in-the-loop interrupt (an
approval) and is waiting for an answer. Scripts and CI should treat it as "needs a
human". [Exit codes](../reference/exit-codes.md#tell-a-pause-from-a-failure) shows
how to tell the two apart, and [Human-in-the-loop](../guides/human-in-the-loop.md)
how to answer the pause.

## A setting doesn't take effect

Settings resolve in this order: command-line flags, then environment variables, then
the project `langstage.toml`, then the global `~/.langstage/config.toml`. A value you
set can be overridden by a layer above it. Every stage prints what won and where it
came from:

<!-- snippet: skip -->
```bash
langstage config            # web
langstage-cli --show-config # terminal
```

See [Configuration](configuration.md#see-what-resolved).

## Still stuck

Re-run with `-v` for the full traceback, then
[open an issue](https://github.com/dkedar7/langstage-core/issues) on the package
that printed the error, with the command, the output and `pip list | grep langstage`.
