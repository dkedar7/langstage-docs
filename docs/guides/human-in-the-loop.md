# Human-in-the-loop

When your graph calls LangGraph's `interrupt(...)`, or uses LangChain's
`HumanInTheLoopMiddleware` (deepagents' `interrupt_on=...` uses it), the turn
pauses and waits for a person. Every LangStage surface shows the pause, collects a
decision, and resumes the same thread with it. This page covers the shared
vocabulary and how each surface presents it.

## Decision verbs

LangStage uses one vocabulary, the `HumanInTheLoopMiddleware` verbs. The legacy
LangGraph `HumanInterrupt` spellings are accepted as aliases, in any case.

| Verb | What it does | Payload | Accepted alias |
|---|---|---|---|
| `approve` | Run the action as proposed. | `{"type": "approve"}` | `accept` |
| `edit` | Run it with changed arguments. | `{"type": "edit", "edited_action": {"name": "…", "args": {…}}}` | none |
| `reject` | Don't run it, optionally with a reason. | `{"type": "reject", "message": "…"}` (`message` optional) | `ignore` |
| `respond` | Answer with text instead of running it. | `{"type": "respond", "message": "…"}` | `response` |

- **What the interrupt allows.** An `interrupt` frame carries `allowed_decisions`,
  always in the canonical verbs. It comes from the interrupt's own configuration
  (the middleware's `review_configs[*].allowed_decisions`, or a legacy
  `HumanInterrupt`'s `config`), so an approve-only interrupt advertises exactly
  `["approve"]`. All four are listed only when the interrupt says nothing.
- **Aliases are translated only where needed.** When the pending interrupt is a
  `HumanInTheLoopMiddleware` request, core rewrites an alias (`accept`) to its
  canonical verb (`approve`) before resuming, because the middleware rejects the
  alias. Any other interrupt, such as your own `interrupt(...)` or a legacy
  `HumanInterrupt`, gets the payload exactly as sent.
- **One decision per action.** An interrupt can ask about several actions at once
  (`action_requests`). Send one decision per action, in order.

## Checking a verb before you resume

Core doesn't refuse a disallowed verb on resume, so a surface (or your code)
should check first. The helpers are top-level in `langstage_core`:

```python
from langstage_core import DECISION_ALIASES, DECISION_VERBS, is_allowed_decision, normalize_decision

allowed = ["reject", "approve"]              # frame["allowed_decisions"]
print(normalize_decision("accept", allowed)) # approve   (alias -> canonical)
print(normalize_decision("edit", allowed))   # None      (not allowed here: refuse it)
print(is_allowed_decision("ignore", allowed))# True      (ignore == reject)
print(DECISION_VERBS, DECISION_ALIASES)
```

`normalize_decision(verb)` with no `allowed` list just maps an alias to its
canonical verb.

## Resuming from Python

Resume by running the next turn on the **same `thread_id`** with `resume=`. It takes
the `{"decisions": [...]}` envelope, or a `Command` from `create_resume_input(...)`.
This example uses the keyless tool demo, whose `"ask me"` interrupt allows
`respond` and `approve`:

```python
import asyncio
from langstage_core import create_resume_input
from langstage_core.agui import build_agent, iter_event_frames
from langstage_core.demo.tools import create_tool_demo_agent

agent = build_agent(create_tool_demo_agent())   # build once, reuse across turns

async def main():
    async for frame in iter_event_frames(agent, "ask me", thread_id="s1"):
        if frame["type"] == "interrupt":
            print("allowed:", frame["allowed_decisions"])
        if frame["type"] == "complete":
            print("outcome:", frame["outcome"])            # interrupted

    decision = create_resume_input(decisions=[{"type": "approve"}])
    async for frame in iter_event_frames(agent, "", thread_id="s1", resume=decision):
        if frame["type"] == "content":
            print(frame["content"], end="")
        if frame["type"] == "complete":
            print("\noutcome:", frame["outcome"])          # complete

asyncio.run(main())
```

`build_agent` attaches an in-memory checkpointer when your graph has none, so the
paused thread is still there for the resume. Keep the same `agent` object: a new
in-memory checkpointer would not know the thread.

The task engine takes the same decisions: a delegated task that interrupts parks
in `review_needed` until you call `await runner.resume(task_id, [{"type": "approve"}])`.
See [Shared core](../core.md#delegate-work-to-a-background-task).

Over HTTP, an AG-UI client resumes with `RunAgentInput.resume` (ag-ui-langgraph
0.0.43 and later). See [Serve over AG-UI](../reference/agui-server.md#notes-for-ag-ui-client-authors).

## How each surface presents a pause

| Surface | What you see | How you answer |
|---|---|---|
| **Web** (`langstage`) | An "Action Requires Approval" dialog listing each action, its description and arguments. | **Approve**, **Reject**, and **Edit** (per action, arguments as JSON). Each button appears only if the interrupt allows that verb. On the task board, a paused task sits in **review**; open it to approve or reject. |
| **Terminal** (`langstage-cli`) | Each action with **every** argument as `name=value`. Control characters are escaped, so an argument can't forge prompt text. | An arrow-key menu: approve all, reject all, or type a custom decision as JSON. A plain `interrupt("What is your name?")` asks for a free-text value and resumes with exactly that value. |
| **JupyterLab** (`langstage-jupyter`) | The action inline in the chat sidebar. | **Approve**, **Reject** and **Edit** buttons, shown per `allowed_decisions`. |
| **VS Code** (`langstage-vscode`) | Each action (name, description, arguments) in the chat response. | **Approve**, **Reject**, **Respond…**, **Edit…** buttons, or `@langstage /approve`, `/reject [reason]`, `/respond <text>`, `/edit <json>`. See [VS Code](../stages/vscode.md#answering-an-interrupt). |
| **`langstage-agui -m`**, **`langstage chat`**, **`langstage-jupyter --ask`**, **`langstage-vscode-sidecar --message`** | The pending action on stderr. | These are one-shot runs, so they exit `2` ("paused"; see [Exit codes](../reference/exit-codes.md)). Resume from Python, a UI, or the sidecar's `--repl`. |
| **`langstage-vscode-sidecar --repl`** | The action and its allowed verbs. | Type `:decision <verb>` or just the bare verb: `approve`, `reject [<text>]`, `respond <text>`, `edit <json>`. |

In scripts, the terminal needs a person at the keyboard to approve. If stdin
isn't a terminal, `langstage-cli` stops rather than approve something nobody saw
(exit `2`, "paused", from 0.6.36). Pass `--no-interactive` to auto-approve on
purpose.

!!! tip "Try it without an agent or key"
    `langstage-cli -a langstage_core.demo.tools:graph "ask me"` in a terminal, or
    `langstage run --agent langstage_core.demo.tools:graph` and type "ask me", or
    `langstage-vscode-sidecar --demo=tools --repl` and type `ask me`, then `approve`.
