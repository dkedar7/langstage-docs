# Quickstart

## 1. Write an agent

A LangStage agent is a LangGraph `CompiledGraph` exported from a Python file or
module. Nothing LangStage-specific is required.

=== "No model, no key"

    A plain LangGraph graph. It needs only `langgraph`, which every surface already
    installs, so it runs as-is:

    ```python title="my_agent.py"
    from langchain_core.messages import AIMessage
    from langgraph.graph import END, START, MessagesState, StateGraph

    def respond(state):
        last = state["messages"][-1].content
        return {"messages": [AIMessage(content=f"You said: {last}")]}

    g = StateGraph(MessagesState)
    g.add_node("respond", respond)
    g.add_edge(START, "respond")
    g.add_edge("respond", END)
    graph = g.compile()
    ```

    `langstage-cli init` writes this same file, plus a `langstage.toml` that points
    at it.

=== "A real model (deepagents + Anthropic)"

    !!! warning "Needs extra packages and an API key"
        `pip install deepagents langchain-anthropic` and set `ANTHROPIC_API_KEY`.
        The surfaces don't install `deepagents` for you (except the web app's
        `langstage[deepagents]` extra).

    ```python title="my_agent.py"
    from deepagents import create_deep_agent

    graph = create_deep_agent(model="anthropic:claude-sonnet-4-6")
    ```

    You don't need to compile in a checkpointer: every surface attaches one when
    the graph has none (the web app's is durable SQLite; see
    [Web](../stages/web.md#bring-your-own-agent)).

## 2. Point any stage at it with one spec string

The **agent spec** is `path/to/file.py:attr` or `module:attr`. Every stage
understands the same form:

```bash
langstage run --agent my_agent.py:graph          # web
langstage-cli --agent my_agent.py:graph          # terminal  (-a for short)
langstage-jupyter --agent my_agent.py:graph      # JupyterLab launcher (-a too)
langstage-agui --agent my_agent.py:graph         # AG-UI endpoint
```

Prefer not to pass it each time? Set it once in the environment or in
`langstage.toml` (see [Configuration](configuration.md)), and every stage picks it
up:

```bash
export LANGSTAGE_AGENT_SPEC="my_agent.py:graph"
```

```toml title="langstage.toml"
[agent]
spec = "my_agent.py:graph"   # relative to this file, so it works from any subdirectory
```

## 3. Check it before you chat

Three questions, in order:

```bash
langstage-cli --show-config                        # does the config resolve my agent?
langstage-cli --verify                             # does it load and run one turn?
langstage-cli "What can you do?"                   # what does it say?
```

The same trio exists on each surface (`--show-config`, then `langstage check --live`
/ `--verify` / `--selfcheck`, then a one-shot message). See
[Installation](installation.md#preflight-your-own-agent) for the full list.

The resolved-config table shows each value, where it came from, and the env var and
TOML key that set it:

```text
Resolved config  (value  [source]):

  agent_spec       = /home/you/project/my_agent.py:graph [toml (langstage.toml)]   (env: LANGSTAGE_AGENT_SPEC (legacy DEEPAGENT_AGENT_SPEC), toml: agent.spec)
  workspace_root   = .                          [default]   (env: LANGSTAGE_WORKSPACE_ROOT (legacy DEEPAGENT_WORKSPACE_ROOT), toml: workspace.root)
  graph_name       = graph                      [default]   (toml: agent.graph_name)
  verbose          = False                      [default]   (toml: ui.verbose)
  (not used by this surface, so not shown: host, port, debug, title, stream_mode, async_mode)

  TOML read from: /home/you/project/langstage.toml
  ...
```

## 4. Try a stage with no API key

Every surface has a keyless demo, good for a first look, a screenshot or a test:

```bash
langstage run --demo
langstage-cli --demo "ping"
langstage-jupyter --demo
langstage-vscode-sidecar --demo --message "ping"
langstage-hermes demo
langstage-agui --demo
```

To see tool calls, reasoning and an approval prompt without a key, use the tool
demo: `langstage-cli -a langstage_core.demo.tools:graph "use a tool"` (or
`"think about it"`, or `"ask me"`).

On the web stage, the empty screen offers a few **starter-prompt chips**. Click one
to begin without typing.

Now pick the stage you want:
[Web](../stages/web.md) ·
[Terminal](../stages/cli.md) ·
[JupyterLab](../stages/jupyter.md) ·
[VS Code](../stages/vscode.md) ·
[Reference agent](../stages/hermes.md)
