# Installation

Each LangStage stage is its own PyPI package — install only the surfaces you
want. They all share the [`langgraph-stream-parser`](../core.md) core, which is
pulled in automatically.

=== "Web"

    ```bash
    pip install langstage
    ```

=== "Terminal"

    ```bash
    pip install langstage-cli
    ```

=== "JupyterLab"

    ```bash
    pip install langstage-jupyter
    ```

=== "VS Code"

    ```bash
    pip install langstage-vscode   # the Python sidecar
    # + install the extension (see the VS Code stage page)
    ```

=== "Reference agent"

    ```bash
    pip install langstage-hermes
    ```

## Requirements

- **Python 3.11+** (the core supports 3.10+).
- Your agent's own dependencies — typically
  [`langgraph`](https://github.com/langchain-ai/langgraph) and, if you use it,
  [`deepagents`](https://github.com/langchain-ai/deepagents). Real surfaces
  already depend on `langgraph`, so the keyless `--demo` works on a bare install.
- An API key for whatever model your agent uses (e.g. `ANTHROPIC_API_KEY`) —
  **not** required for `--demo`.

## Verify it works — no key needed

```bash
langstage run --demo          # web UI at http://localhost:8050
langstage-cli --demo "hello"  # one-shot terminal reply
```

Both launch against a built-in deterministic echo agent
(`langgraph_stream_parser.demo.stub:graph`), so a fresh install is provably
working before you wire up a real agent.

Next: [Quickstart](quickstart.md) →
