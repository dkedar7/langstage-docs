# Shared core — `langgraph-stream-parser`

Every stage is thin because the hard parts live in one shared package:
`langgraph-stream-parser`. It keeps its descriptive name (it's useful on its own,
outside the family) and is the dependency that visibly ties LangStage to
LangGraph.

[:material-github: dkedar7/langgraph-stream-parser](https://github.com/dkedar7/langgraph-stream-parser){ .md-button }
[:material-package: PyPI](https://pypi.org/project/langgraph-stream-parser/){ .md-button }

## What it provides

- **Typed stream events.** Normalizes the variable shapes from `graph.stream()`
  / `graph.astream()` into consistent dataclass events (`ContentEvent`,
  `ToolCallStartEvent`, `InterruptEvent`, `CompleteEvent`, …) with a single
  `event_to_dict()` wire vocabulary every stage emits.
- **`load_agent_spec()`** — the `module:attr` / `path/to/file.py:attr` loader
  behind every stage's agent spec.
- **`HostConfig`** — the layered config resolver
  (`defaults < langstage.toml < LANGSTAGE_* env < overrides`) with per-field
  source tracking. Each stage subclasses it to add its own keys.
- **The keyless stub agent** — `langgraph_stream_parser.demo.stub:graph`, the
  deterministic echo agent behind every stage's `--demo` mode.

## Parse a stream yourself

```python
from langgraph_stream_parser import StreamParser
from langgraph_stream_parser.events import ContentEvent, ToolCallStartEvent, InterruptEvent

parser = StreamParser()
for event in parser.parse(graph.stream(input_data, stream_mode="updates")):
    match event:
        case ContentEvent(content=text):
            print(text, end="")
        case ToolCallStartEvent(name=name):
            print(f"\nCalling {name}…")
        case InterruptEvent(action_requests=actions):
            ...  # human-in-the-loop
```

## Inspect the shared config

```bash
python -m langgraph_stream_parser.host
```

prints every shared `LANGSTAGE_*` value, where it resolved from, and the env var
/ TOML key that sets it — the same machinery behind each stage's `--show-config`.

See [Configuration](getting-started/configuration.md) for the resolution chain.
