# Installation

Each LangStage stage is its own PyPI package, so install only the surfaces you
want. They all share [`langstage-core`](../core.md), which is pulled in
automatically.

=== "Web"

    <!-- snippet: run -->

    ```bash
    pip install langstage
    pip install "langstage[deepagents]"   # optional: the built-in default agent
    ```

=== "Terminal"

    <!-- snippet: run -->

    ```bash
    pip install langstage-cli
    ```

=== "JupyterLab"

    <!-- snippet: run -->

    ```bash
    pip install langstage-jupyter
    ```

=== "VS Code"

    <!-- snippet: check -->

    ```bash
    pip install langstage-vscode          # the Python sidecar
    code --install-extension dkedar7.langstage-vscode
    ```

    Or search **LangStage** in the Extensions view. VS Code installs it from the
    [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=dkedar7.langstage-vscode); Cursor, VSCodium and Windsurf install it from
    [Open VSX](https://open-vsx.org/extension/dkedar7/langstage-vscode). The `.vsix` on the
    [latest extension release](https://github.com/dkedar7/langstage-vscode/releases/latest)
    is the fallback (**Extensions: Install from VSIX…**). Its LangStage panel works in
    VS Code without Copilot, Cursor, VSCodium, Windsurf and code-server; see
    [VS Code](../stages/vscode.md#install).

=== "Reference agent"

    <!-- snippet: run -->

    ```bash
    pip install langstage-hermes
    ```

=== "AG-UI server only"

    <!-- snippet: run -->

    ```bash
    pip install "langstage-core[agui]"    # the langstage-agui command
    ```

## Requirements

- **Python 3.11 or newer**, for every package including the core.
- Your agent's own dependencies. Every surface already depends on `langgraph`, so a
  plain LangGraph graph (and every `--demo`) works on a bare install. If your agent
  uses [`deepagents`](https://github.com/langchain-ai/deepagents) or a provider
  package such as `langchain-anthropic`, install those yourself.
- An API key for whatever model your agent calls (for example `ANTHROPIC_API_KEY`).
  Not needed for the demos or the keyless preflights.

!!! note "`langstage run` with no agent"
    With no `--agent` and no configured spec, `langstage run` falls back to a
    built-in default agent. That agent needs `pip install "langstage[deepagents]"`
    and `ANTHROPIC_API_KEY`. Use `--demo` for a zero-setup first run instead.

## Check it works, no key needed

<!-- snippet: run server -->
```bash
langstage run --demo            # web UI at http://localhost:8050
langstage-cli --demo "hello"    # one-shot terminal reply
```

Both run the built-in echo agent (`langstage_core.demo.stub:graph`), so a fresh
install is provably working before you wire up a real agent. Every surface has a
keyless demo:

| Surface | Keyless demo |
|---|---|
| Web | `langstage run --demo` |
| Terminal | `langstage-cli --demo "hello"`, or `langstage-cli -a langstage_core.demo.tools:graph "use a tool"` for tool calls, reasoning and an approval prompt |
| JupyterLab | `langstage-jupyter --demo` |
| VS Code sidecar | `langstage-vscode-sidecar --demo --message "hello"`, or `--demo=tools` |
| Reference agent | `langstage-hermes demo` (a subcommand, not a flag) |
| AG-UI server | `langstage-agui --demo`, or `--demo=tools` |

## Preflight your own agent

Once you point a stage at your agent, each surface has a preflight that loads it and
runs one real turn, so a typo'd spec, a missing key or a broken tool shows up before
the first chat:

| Surface | Preflight |
|---|---|
| Web | `langstage check --live` (drop `--live` for the fast, keyless static checks) |
| Terminal | `langstage-cli --verify` |
| JupyterLab | `langstage-jupyter --verify` (the agent) or `--serve-check` (the HTTP endpoint) |
| VS Code sidecar | `langstage-vscode-sidecar --selfcheck` |
| Reference agent | `langstage-hermes verify` (and `doctor` for the environment) |
| AG-UI server | `langstage-agui --verify` |

They all exit `0` when the agent is healthy and non-zero when it isn't. See
[Exit codes](../reference/exit-codes.md).

Next: [Quickstart](quickstart.md) →
