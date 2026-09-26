# LangStage vs LangSmith

A common question when you have a LangGraph agent and want a place to *run* it:
**do I reach for LangSmith, or something like LangStage?** They overlap less than
the names suggest — and they compose well. This page is an honest map of where
each fits.

!!! abstract "TL;DR"
    - **LangStage** is a **self-hosted, MIT-licensed, code-first console** — a UI
      that operates a LangGraph agent *you already wrote*, on the web, terminal,
      JupyterLab, and VS Code. You bring the `CompiledGraph`; your keys and data
      stay on your box.
    - **LangSmith** is LangChain's **cloud platform for observability, evaluation,
      and prompt management** — plus **LangSmith Fleet**, a **no-code, hosted**
      workspace for *building* agents from templates and managed integrations.
    - They're **complementary, not either/or**: run your agent's UI in LangStage
      and still send traces to LangSmith. Reach for LangStage when you want to
      **self-host a console for code you own**; reach for LangSmith when you want
      **managed tracing/eval** or a **no-code hosted agent builder**.

## At a glance

The closest LangSmith analog to LangStage's "operate my agent" job is **LangSmith
Fleet**, so that's the fair column to compare against for the console/UI role.
LangSmith's tracing/eval platform is a *different* job (see [below](#what-langstage-is-not)).

| | **LangStage** | **LangSmith Fleet** |
|---|---|---|
| **What it is** | A console/UI to operate a LangGraph agent you wrote | A no-code workspace to build & run agents from templates |
| **License** | MIT, open source | Proprietary (commercial SaaS) |
| **Hosting** | Self-hosted by default (your machine, your VPC, Docker/k8s) | Managed cloud, first-party |
| **How you build the agent** | Code-first — any LangGraph `CompiledGraph` (bring your own) | No-code — templates + "describe your goal", managed tools |
| **Where keys & data live** | On your infrastructure | On LangChain's cloud |
| **Human-in-the-loop** | Yes — interrupt/approve gate, review board | Yes — built-in approvals |
| **Surfaces** | Web, terminal, JupyterLab, VS Code, and an AG-UI endpoint for your own frontend — one spec, every stage | Hosted web workspace |
| **Auth / deploy story** | Basic Auth, `--host`/`--port`, `/api/health` liveness and `?ready=1` readiness probes, CORS allowlist; put your own proxy in front | Managed |
| **Best for** | Owning the whole stack around a graph you control | Getting an agent live fast with zero infra, no code |

Both keep a human in control; the split is **self-hosted + code-first + MIT**
vs **hosted + no-code + managed**.

## What LangStage is *not*

Being honest about the boundary matters more than winning a table:

- **LangStage is not an observability or evaluation platform.** It doesn't do
  trace storage, dataset eval, or prompt versioning. For that, LangSmith (or
  Langfuse, or Phoenix) is the right tool — and LangStage doesn't try to replace it.
- **LangStage is not a managed cloud.** There's no hosted tier; you run it.
- **LangStage is not a no-code builder.** You write the agent in LangGraph. That's
  the point — it's for people who already have (or want to write) the graph.

## They compose

Because LangStage runs your agent as **plain LangGraph**, first-party LangChain
tooling keeps working underneath it. Set the standard tracing env vars and every
turn your agent takes in LangStage shows up in LangSmith:

<!-- snippet: check -->
```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=ls-...
langstage run --agent my_agent.py:graph
```

So a realistic setup is **LangStage as the self-hosted operator console +
LangSmith for tracing/eval** — you don't have to choose.

## Which should you pick?

**Pick LangStage if you want to…**

- self-host the UI/console for a LangGraph agent **you own the code for**;
- keep API keys and conversation data **on your own infrastructure**;
- run the *same* agent across the **web, terminal, JupyterLab, and VS Code**;
- stay on a **permissive MIT** license with no vendor lock-in.

**Pick LangSmith / Fleet if you want to…**

- **observe, trace, and evaluate** LLM apps (LangSmith's core strength);
- build an agent **without writing code**, from templates + managed integrations (Fleet);
- have LangChain **host and manage** it for you.

**Use both** when you want a self-hosted console *and* managed tracing/eval.

---

Ready to try the self-hosted path? It's a keyless 30 seconds:

<!-- snippet: run server -->
```bash
pip install langstage
langstage run --demo
```

See [Installation](getting-started/installation.md) and [Quickstart](getting-started/quickstart.md).
