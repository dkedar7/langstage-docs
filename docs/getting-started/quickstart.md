# Quickstart

## 1. Write an agent

A LangStage agent is just a LangGraph `CompiledGraph` exported from a Python
file or module. Nothing LangStage-specific is required.

```python title="my_agent.py"
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

graph = create_deep_agent(
    model="anthropic:claude-sonnet-4-5",
    checkpointer=MemorySaver(),
)
```

## 2. Point any stage at it with one spec string

The **agent spec** is `path/to/file.py:attr` or `module:attr`. Every stage
understands the same form:

```bash
langstage run --agent my_agent.py:graph          # web
langstage-cli --agent my_agent.py:graph          # terminal  (-a for short)
langstage-jupyter --agent my_agent.py:graph      # JupyterLab launcher
```

Prefer not to pass it each time? Set it once in the environment or
`langstage.toml` (see [Configuration](configuration.md)) and every stage picks
it up:

```bash
export LANGSTAGE_AGENT_SPEC="my_agent.py:graph"
```

## 3. Try a stage with no API key

Every surface has a `--demo` flag that swaps in a deterministic, keyless echo
agent — great for a first run or for screenshots/tests:

```bash
langstage run --demo
langstage-cli --demo "ping"
langstage-jupyter --demo
python -m langstage_vscode --demo
```

## 4. See exactly what's configured

When you're not sure which value won, every stage can print the fully resolved
configuration — each value, where it came from, and the env var / TOML key that
sets it:

```bash
langstage config            # web: a subcommand, like `langstage run`
langstage-cli --show-config
langstage-hermes --show-config
```

```text
Resolved config  (value  [source]):

  agent_spec       = my_agent.py:graph          [env:LANGSTAGE_AGENT_SPEC]   (env: LANGSTAGE_AGENT_SPEC, toml: agent.spec)
  workspace_root   = .                          [default]                    (env: LANGSTAGE_WORKSPACE_ROOT, toml: workspace.root)
  port             = 8050                        [default]                    (env: LANGSTAGE_PORT, toml: server.port)
  ...
```

Now pick the stage you want:
[Web](../stages/web.md) ·
[Terminal](../stages/cli.md) ·
[JupyterLab](../stages/jupyter.md) ·
[VS Code](../stages/vscode.md) ·
[Reference agent](../stages/hermes.md)
