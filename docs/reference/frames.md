# AG-UI wire and frame reference

Every LangStage surface streams a turn the same way. The shared core wraps your
compiled graph in the official [`ag-ui-langgraph`](https://github.com/ag-ui-protocol/ag-ui)
adapter and maps the AG-UI events to small, typed Python dicts called **frames**.
There are two mappings of the same information:

- **The event wire**, `iter_event_frames()`. It yields `{"type": …}` frames. The web
  app and the VS Code sidecar use it.
- **The chunk wire**, `iter_chunk_frames()`. It yields `{"status": …}` chunks. The
  terminal and JupyterLab use it.

Both are async generators in `langstage_core.agui` and need the `[agui]` extra
(`pip install "langstage-core[agui]"`), which every surface already installs.

## Frame table

This table is the contract. Keys marked *(additive)* were added after 1.0. A client
must ignore a frame type or a key it doesn't know.

| Event wire | Chunk wire | Meaning |
|---|---|---|
| `{"type": "content", "content", "role", "node", "message_id"}` | `{"status": "streaming", "chunk", "node", "message_id"}` | A delta of assistant text. |
| `{"type": "reasoning", "content", "node"}` | `{"status": "streaming", "reasoning", "node"}` | Chain-of-thought from a reasoning model, kept separate from the answer. |
| `{"type": "tool_start", "id", "name", "args", "node"}` | `{"status": "streaming", "tool_calls": [{"name", "args", "id"}]}` | A tool call. |
| `{"type": "tool_end", "id", "name", "result", "status", "error_message", "duration_ms"}` | `{"status": "streaming", "tool_result", "id", "name", "tool_status", "duration_ms"}` | A tool result, capped at `max_result_len`. |
| `{"type": "extraction", "tool_name", "extracted_type", "data"}` | `{"status": "streaming", "extraction": {"tool_name", "extracted_type", "data"}}` | Structured data an extractor pulled out of a successful tool result. |
| `{"type": "interrupt", "action_requests", "review_configs", "allowed_decisions"}` | `{"status": "interrupt", "interrupt": {…same keys}}` | A human-in-the-loop pause. |
| `{"type": "complete", "outcome"}` | `{"status": "complete", "outcome"}` | The turn ended. |
| `{"type": "error", "error"}` | `{"status": "error", "error"}` | The turn failed. |

### The rules that matter

- **A chunk carries exactly one payload key.** A `streaming` chunk has one of
  `chunk`, `reasoning`, `tool_calls`, `tool_result` or `extraction`. Branch on the
  key, and don't assume `chunk` is present.
- **`message_id` marks message boundaries** *(additive)*. It names the `AIMessage`
  a text delta belongs to. When it changes between two text frames, a new message
  started (for example, a second node's reply). Render a paragraph break, not an
  inline join.
- **Tool status and duration** *(additive)*. `status` (event wire) and
  `tool_status` (chunk wire) are `"success"` or `"error"`. `duration_ms` is how long
  the tool ran. It is `None` when the tool ran outside LangChain's tool runtime,
  such as a hand-written node. On the chunk wire, `id`, `name`, `tool_status` and
  `duration_ms` are additive, and `tool_result` is still the result string.
- **`extraction` only follows a successful tool.** A failed tool never produces
  one. It is emitted after the call's `tool_end`, so match it to its call by id.
- **`complete.outcome`** *(additive)* is `"interrupted"` if the turn paused on an
  interrupt, else `"complete"`. An interrupted turn still ends with `complete`.
  Detect the pause from the `interrupt` frame or from `outcome`, not from whether
  `complete` arrived.
- **`error` is terminal.** Nothing follows it, and there is no `complete`. Content
  that earlier nodes already produced is streamed before it. With
  `LANGSTAGE_DEBUG=1`, the `error` frame also carries a `traceback`.
- **Order.** Frames arrive in message order. A node that returns a finished
  `AIMessage` (no token streaming: `model.invoke()`, a router, a canned reply) is
  emitted when the node finishes, its text before its own tool calls.

The `node` label comes from the step's own update, so it is correct with an async
checkpointer too (core 1.0.37).

## See every frame type without a key

The bundled tool demo, `langstage_core.demo.tools`, is deterministic and offline.
Its trigger phrases produce each frame type: `"use a tool"` (tool call, result,
extraction), `"think"` (reasoning), and `"ask me"` (an interrupt). Anything else is
echoed.

<!-- snippet: run -->
```python
import asyncio
from langstage_core.agui import build_agent, iter_chunk_frames, iter_event_frames
from langstage_core.demo.tools import create_tool_demo_agent, demo_extractors

agent = build_agent(create_tool_demo_agent())

async def main():
    seen = []
    async for frame in iter_event_frames(agent, "use a tool", "t1", extractors=demo_extractors()):
        if frame["type"] not in seen:
            seen.append(frame["type"])
    print("event wire:", seen)    # ['tool_start', 'tool_end', 'extraction', 'content', 'complete']

    keys = []
    async for chunk in iter_chunk_frames(agent, "think about it", "t2"):
        key = next((k for k in ("chunk", "reasoning", "tool_calls", "tool_result", "extraction")
                    if k in chunk), chunk["status"])
        if key not in keys:
            keys.append(key)
    print("chunk wire:", keys)    # ['reasoning', 'chunk', 'complete']

asyncio.run(main())
```

From a shell: `langstage-agui --demo=tools -m "use a tool" --json`,
`langstage-vscode-sidecar --demo=tools --message "think about it" --json`, or
`langstage-cli -a langstage_core.demo.tools:graph "use a tool"`.

## The served AG-UI endpoint

`langstage-agui`, `build_app()` and `serve()` expose the same turn as a standard
AG-UI HTTP endpoint (server-sent AG-UI events such as `RUN_STARTED`,
`TEXT_MESSAGE_*`, `TOOL_CALL_*`, `RUN_FINISHED`). The frames above are built from
exactly those events, so an AG-UI client and an in-process consumer see the same
turn. Differences worth knowing for an AG-UI client:

- An agent failure is a terminal `RUN_ERROR` event, not a dropped stream.
- An interrupt arrives as a `CUSTOM` `on_interrupt` event.
- Resuming uses AG-UI's standard `RunAgentInput.resume` (ag-ui-langgraph 0.0.43 and
  later). The older `forwardedProps.command.resume` is a deprecated fallback.
- Use a new message id for every turn. The adapter dedupes messages by id, so a
  reused id silently drops the later turn.

See [Serve over AG-UI](agui-server.md).

## Surface-specific protocol frames

The VS Code sidecar wraps the event wire in a stdio protocol and adds a few frames
of its own: `ready`, `ack`, `cancelled` and `turn_end`. They are documented on the
[VS Code page](../stages/vscode.md#sidecar-protocol).
