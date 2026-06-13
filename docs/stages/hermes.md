# Reference agent — `langstage-hermes`

Not a surface but an **agent** — the family's reference implementation, and a
faithful reproduction of Nous Research's Hermes Agent on top of LangGraph +
deepagents. It's the agent you can drop into *any* stage to see a rich,
real-world agent in action.

[:material-github: dkedar7/langstage-hermes](https://github.com/dkedar7/langstage-hermes){ .md-button }
[:material-package: PyPI](https://pypi.org/project/langstage-hermes/){ .md-button }

## What it is

A `deepagents`-built agent with a **closed reflection → skill-creation loop**:

- After ~10 tool-using iterations, a review subagent writes/patches a `SKILL.md`
  capturing the pattern it just exercised, and ships it to a skill library.
- Next session, the agent reads the library at startup and can `skill_view(name)`
  to load a skill on demand (progressive disclosure).
- A weekly **curator** consolidates skills and archives stale ones.
- **Frozen-snapshot memory** (`MEMORY.md` + `USER.md`) preserves prefix-cache
  hits; **FTS5 session search** indexes every past conversation locally.

## Run it standalone

```bash
pip install langstage-hermes
langstage-hermes --show-config        # resolved config + sources
langstage-hermes chat                  # interactive REPL (needs a model key)
langstage-hermes verify                # one live round-trip; confirms setup
```

## Run it on any stage

Because it's just a `CompiledGraph`, point any LangStage surface at its graph:

```bash
# Terminal
LANGSTAGE_AGENT_SPEC="langstage_hermes.agent:graph" langstage-cli

# Web
langstage run --agent langstage_hermes.agent:graph

# JupyterLab — or set the same in langstage.toml under [agent]
langstage-jupyter -a langstage_hermes.agent:graph
```

## Picking a model

Defaults to Anthropic (`ANTHROPIC_API_KEY`). For OpenAI / OpenRouter:

```bash
pip install "langstage-hermes[openai]"
export OPENAI_API_KEY=sk-…            # or OPENROUTER_API_KEY=sk-or-v1-…
export OPENAI_BASE_URL=https://openrouter.ai/api/v1   # OpenRouter only
langstage-hermes chat --model openai:openai/gpt-4o-mini
```

Hermes-specific settings use the `LANGSTAGE_HERMES_*` env prefix and a
`langstage-hermes.toml` file; run `langstage-hermes --show-config` for the full
list.
