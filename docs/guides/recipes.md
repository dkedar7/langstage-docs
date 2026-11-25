# Recipes

Short answers to common tasks, each one you can copy. Each recipe links to the page
with the details.

## Use any model through OpenRouter

LangStage runs whatever model your graph calls, so this is a change to your agent,
not to LangStage. OpenRouter speaks the OpenAI API, so point `ChatOpenAI` at it
(`pip install langchain-openai`):

<!-- snippet: check -->
```python
import os
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="anthropic/claude-sonnet-5",            # any OpenRouter model id
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
graph = create_agent(model, tools=[])
```

Then run it on any stage: `langstage-cli -a agent.py "hello"`,
`langstage run --agent agent.py:graph`, and so on. The same pattern works for any
OpenAI-compatible endpoint (a local vLLM or Ollama server, a gateway): change
`base_url`. A missing key can show up as a connection error, see
[Troubleshooting](../getting-started/troubleshooting.md#no-api-key-it-may-say-connection-error).

## Ask before a tool runs

Add LangChain's `HumanInTheLoopMiddleware` and name the tools that need a yes:

<!-- snippet: check -->
```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware

def send_email(to: str, body: str) -> str:
    """Send an email."""
    return f"sent to {to}"

graph = create_agent(
    "anthropic:claude-sonnet-5",
    tools=[send_email],
    middleware=[HumanInTheLoopMiddleware(interrupt_on={"send_email": True})],
)
```

Every stage shows the pause and collects the decision: an approval card in the web
app, JupyterLab and VS Code, and a menu in the terminal. You don't need a
checkpointer for this. The stages attach one. To limit the choices, pass
`{"send_email": {"allowed_decisions": ["approve", "reject"]}}` instead of `True`.
[Human-in-the-loop](human-in-the-loop.md) covers the decision verbs and resuming
from your own code.

## Run a prompt on a schedule

Pick the one that matches where the agent lives:

- **Web app:** the **Schedules** tab runs a prompt on a cron expression and puts each
  run on the task board. Cron times are UTC.
  [Details](../stages/web.md#schedules).
- **Hermes:** `langstage-hermes cron create --prompt "…" --schedule "0 18 * * MON-FRI"`,
  then run `langstage-hermes cron daemon`.
  [Details](../stages/hermes.md#scheduled-runs-cron).
- **Any agent, from your OS scheduler:** run one turn with `langstage-cli` and keep
  the reply:

<!-- snippet: skip -->
```bash
# crontab: weekdays at 09:00
0 9 * * 1-5  cd /srv/agent && langstage-cli -a agent.py "Summarize yesterday's tickets" >> digest.log 2>> errors.log
```

The reply goes to stdout and errors go to stderr. The exit code tells you what
happened: `0` replied, `1` failed, `2` paused on an approval nobody can answer. A
scheduled run has no one to answer, so either keep approval-gated tools out of it or
pass `--no-interactive`, which approves every pending action automatically.
[Exit codes](../reference/exit-codes.md) lists them for every command.

## Serve the web app behind a reverse proxy

The web app answers only to local host names by default. Behind a proxy that
forwards the public host name (Caddy and Traefik do), allow that name:

<!-- snippet: check -->
```toml
[server]
allowed_hosts = ["agent.example.com"]
```

or `LANGSTAGE_ALLOWED_HOSTS=agent.example.com`. nginx's plain `proxy_pass` sends
`127.0.0.1:<port>` and needs nothing. Add a password with `--auth-password` before
you expose it, and see [Web: Host names](../stages/web.md#host-names) and
[CORS](../stages/web.md#cors). Codraft has its own proxy settings for serving under
a path prefix: see [Documents](../stages/codraft.md).

## Serve your agent to your own frontend

`langstage-agui` serves any LangGraph agent over the AG-UI protocol, so a CopilotKit
or other AG-UI client can talk to it:

<!-- snippet: check -->
```bash
langstage-agui -a agent.py:graph --port 8123
```

[Serve over AG-UI](../reference/agui-server.md) covers the endpoints, CORS and the
event stream.
