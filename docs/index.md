# LangStage

**Every stage for your LangGraph agent.**

Write your agent once — any LangGraph `CompiledGraph`, from a single ReAct agent
to a **multi-agent supervisor** — and run it on every surface with the *same*
spec string, the *same* `langstage.toml` config, and the *same* `LANGSTAGE_*`
environment variables. The web, your terminal, JupyterLab, and VS Code all
become stages your agent can perform on.

<figure markdown="span">
  ![The LangStage web app](assets/screenshots/hero.png){ width="760" }
  <figcaption>Your agent on the web stage — streaming, tool calls, a file browser, and a canvas.</figcaption>
</figure>

!!! tip "Multi-agent? It already works."
    A supervisor, swarm, or crew compiles to the same `CompiledStateGraph`
    LangStage loads — so multi-agent routing and hand-offs run and stream exactly
    like a single agent, with no extra setup. See
    [Running a multi-agent supervisor](guides/multi-agent-supervisor.md).

## 30-second quickstart

No agent or API key yet? See a stage working with the built-in keyless demo
agent:

```bash
pip install langstage
langstage run --demo
```

Then point it at *your* agent — a Python file (or module) that exports a
LangGraph `CompiledGraph`:

```bash
langstage run --agent my_agent.py:graph
```

That same `my_agent.py:graph` spec runs unchanged on every other stage below.

## The family

| Stage | Package | Try it |
|---|---|---|
| :material-web: Web app | [`langstage`](stages/web.md) | `langstage run --agent my_agent.py:graph` |
| :material-console: Terminal | [`langstage-cli`](stages/cli.md) | `langstage-cli -a my_agent.py:graph` |
| :material-notebook: JupyterLab | [`langstage-jupyter`](stages/jupyter.md) | `pip install langstage-jupyter`, then the chat sidebar |
| :material-microsoft-visual-studio-code: VS Code | [`langstage-vscode`](stages/vscode.md) | the `@langstage` chat participant |
| :material-robot: Reference agent | [`langstage-hermes`](stages/hermes.md) | `LANGSTAGE_AGENT_SPEC=langstage_hermes.agent:graph` |
| :material-cog: Shared core | [`langgraph-stream-parser`](core.md) | typed events + config resolver behind every stage |

## Why LangStage

- **Write once, run anywhere.** A single `module:attr` / `path/to/file.py:attr`
  spec string is understood identically by every stage.
- **Keyless demo on every stage.** Each surface ships a `--demo` mode backed by
  a deterministic echo agent, so you can see it work before configuring keys.
- **One config story.** `defaults < langstage.toml < LANGSTAGE_* env < flags` —
  inspect the resolved values anywhere with `--show-config`.
- **Built on the standard.** Pure [LangGraph](https://github.com/langchain-ai/langgraph) /
  [deepagents](https://github.com/langchain-ai/deepagents); the shared core is
  just a typed parser for `graph.stream()` output.

!!! tip "Coming from `deepagent-*` or `cowork-dash`?"
    Every package was renamed into the LangStage family. Your old `pip install`s,
    imports, and commands still work — see [Migrating](migrating.md).

Start with [Installation](getting-started/installation.md) →
