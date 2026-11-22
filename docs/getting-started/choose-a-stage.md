# Which stage should I use?

Pick the stage that fits the job in front of you. You aren't locked in: every stage
loads the same agent spec (`my_agent.py:graph`) and reads the same `langstage.toml`,
so you can run one agent on several stages and switch whenever you like.

| If you want to… | Use | Start with | See it working |
|---|---|---|---|
| Chat with your agent in a browser, with a file browser, background tasks, schedules and reports | [Web](../stages/web.md) | `langstage run --demo` | [Support triage](../gallery/support-triage.md), [Sales analyst](../gallery/sales-analyst.md) |
| Work in a terminal, script a turn, or check an agent in CI | [Terminal](../stages/cli.md) | `langstage-cli --demo "hello"` | [Incident investigator](../gallery/incident-investigator.md) |
| Do data work next to your notebooks, with an agent that can read and edit cells | [JupyterLab](../stages/jupyter.md) | `langstage-jupyter --demo` | [Demo](../stages/jupyter.md#demo) |
| Keep the agent in your editor: VS Code, Cursor, VSCodium, Windsurf or code-server | [VS Code](../stages/vscode.md) | the LangStage panel ([Install](../stages/vscode.md#install)) | [Demo](../stages/vscode.md) |
| Write a document with the agent as co-author, approve each change it suggests, and export a PDF | [Documents](../stages/codraft.md) | `langstage-codraft run --demo` | [Launch video](../stages/codraft.md) |
| Run a ready-made agent that remembers you and learns skills across sessions | [Hermes](../stages/hermes.md) | `langstage-hermes demo` | [Demo](../stages/hermes.md#demo) |
| Build your own frontend, or run an agent with no UI at all | [Shared core](../core.md) | `pip install "langstage-core[agui]"` | [Stream a turn](../core.md#stream-a-turn) |

Hermes is an agent rather than a surface, so it also runs on any stage above:
`-a langstage_hermes.agent:graph`.

## Still not sure?

- **New to LangStage?** Start with the web app and the keyless tool demo agent,
  `langstage run -a langstage_core.demo.tools:graph`. It shows streaming, a tool call,
  reasoning and the Board in one screen, and needs no API key. Then follow the
  [Quickstart](quickstart.md) to put your own agent on it.
- **Need a human to approve some actions?** Every stage can do it, with the same
  decisions: approve, edit, reject or respond. See
  [Human-in-the-loop](../guides/human-in-the-loop.md).
- **Running several agents together?** A supervisor or swarm is still one graph, so
  any stage runs it. See [Multi-agent supervisor](../guides/multi-agent-supervisor.md).

Next: [Installation](installation.md) shows the install line for each stage.
