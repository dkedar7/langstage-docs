# Gallery examples

The agents behind the docs' [Gallery](https://dkedar7.github.io/langstage-docs/gallery/):
small LangGraph agents doing real work on a LangStage stage, each with the data it
works on.

| Example | Stage | Run it (from the example's folder) |
|---|---|---|
| [`support-triage/`](support-triage/) | Web app: Board, human-in-the-loop | `langstage run --agent agent.py:graph --workspace workspace` |
| [`sales-analyst/`](sales-analyst/) | Web app: Python, inline charts, Canvas | `langstage run --agent agent.py:graph --workspace workspace` |
| [`incident-investigator/`](incident-investigator/) | Terminal: approval menu | `cd workspace && langstage-cli --agent ../agent.py:graph` |

Each agent uses Claude Sonnet 5: directly with `ANTHROPIC_API_KEY`
(`pip install langchain-anthropic`), or through OpenRouter when `OPENROUTER_API_KEY`
is set (`pip install langchain-openai`). Change `make_model()` to use another model.

The data is fictional. The sales CSV and the incident logs are generated from a fixed
seed by `make_data.py` and `make_logs.py`; rerun them to regenerate the files.

The recordings on the docs site were made with the scripts in
[`demos/gallery/`](../demos/gallery/), against a real model, once, by hand. CI never
re-records them.
