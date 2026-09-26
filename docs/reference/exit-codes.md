# Exit codes

Every LangStage command line uses the same four exit codes, so a script or CI step
reads them the same way on every surface.

| Code | Meaning | Typical causes |
|---|---|---|
| **`0`** | Success | The turn completed, the preflight passed, the config is clean. |
| **`1`** | Failure | No agent configured; the agent failed to load or import; the turn errored; a `--verify` / `--selfcheck` / `check` / `doctor` failed; `config --strict` found issues; the command can't start (including a busy port). |
| **`2`** | Paused on a human-in-the-loop interrupt | The agent ran and stopped at an `interrupt(...)`, waiting for a decision. Nothing failed, but a person needs to answer. |
| **`64`** | Usage error | An unknown flag, a bad value, a missing argument, or flags that can't be combined (such as `--demo` with `--agent`). The command didn't run. |

**`2` means only "paused".** Nothing else exits `2`, so a script that treats `2` as
"fine, needs a human" can never mistake a broken setup for a pause. That's why
usage errors are `64` (`EX_USAGE` from BSD `sysexits.h`) rather than the `2` that
Python's `argparse` and Click use by default.

The decision is recorded in
[ADR 0007 — one exit-code scheme for every LangStage command line](https://github.com/dkedar7/langstage-core/blob/main/docs/adr/0007-family-exit-codes.md).

!!! warning "Which releases follow it"
    The scheme was adopted on 2026-09-25 in `langstage-core` 1.0.38, `langstage`
    0.13.42, `langstage-cli` 0.6.36, `langstage-jupyter` 0.6.35, the
    `langstage-vscode` sidecar 0.5.33 and `langstage-hermes` 0.4.36. Older releases
    differ in a few places:

    - Usage errors exit `2` (the `argparse` / Click default), and some flag
      conflicts exit `1`, instead of `64`.
    - `langstage-agui` exits `2` when it can't start serving (no spec, a busy port);
      `langstage-hermes verify` / `doctor` exit `2` on a failed check.
    - `langstage chat` exits `1` on an interrupt, and `langstage-cli` exits `1` when an
      approval is needed but stdin isn't a terminal.

    A script that has to work across versions should treat any non-zero code as
    "not OK" and check for `2` only on the one-shot commands below.

## Tell a pause from a failure

A CI job that runs an approval-gated agent needs to tell "paused" from "broken":

<!-- snippet: run no-errexit -->
```bash
langstage-agui --demo=tools -m "ask me"
case $? in
  0)  echo "answered" ;;
  2)  echo "paused: waiting for a human decision" ;;
  64) echo "bad arguments" ;;
  *)  echo "failed" ;;
esac
```

The bundled tool demo interrupts on "ask me", so this prints
`paused: waiting for a human decision`. See
[Human-in-the-loop](../guides/human-in-the-loop.md) for how to answer a pause.

## What each command returns

The commands that run one turn, or one check, and exit are the ones to use in
scripts. Any of them exits `64` on a usage error.

| Command | `0` | `1` | `2` |
|---|---|---|---|
| `langstage-agui -m "…"` | reply printed | error, or no agent | paused |
| `langstage-agui --verify` | the agent ran (a clean pause counts as healthy) | failed to load or run, or an empty turn | — |
| `langstage-agui` (serving) | clean shutdown | can't start: no agent, load error, busy port | — |
| `langstage run` | clean shutdown | can't start: no agent, load error, busy port | — |
| `langstage check [--live]` | the agent loads (and the live turn ran) | load or live-turn failure | — |
| `langstage chat "…"` | reply printed | error, or no agent | paused |
| `langstage config --strict` | the config is clean | any entry in `issues` | — |
| `langstage-cli "…"` (single-shot) | reply printed | error, empty turn, no agent | an approval is needed but stdin isn't a terminal, or you chose **Exit** at the prompt |
| `langstage-cli --verify` | the agent ran | failed | — |
| `langstage-jupyter --ask "…"` | reply printed | error | paused |
| `langstage-jupyter --verify` / `--serve-check` / `--check-connection` | passed (a clean pause counts as healthy) | failed | — |
| `langstage-vscode-sidecar --message "…"` | reply printed | error | paused |
| `langstage-vscode-sidecar --selfcheck` | healthy | failed | the probe turn paused |
| `langstage-vscode-sidecar --repl` | clean session | the agent couldn't start | the session ended with an unanswered interrupt |
| `langstage-hermes verify` / `doctor` | all checks passed | a check failed | — |

A `—` means the command doesn't exit `2`: the preflights treat a clean interrupt as
a sign the agent works. `langstage-hermes` reserves `2` but no command uses it yet.

In Python, `langstage_core.cli` has the same numbers as constants
(`EXIT_OK`, `EXIT_FAIL`, `EXIT_PAUSED`, `EXIT_USAGE`), plus
`exit_code_for_outcome()` to map a turn's `outcome` to a code:

<!-- snippet: run -->
```python
from langstage_core.cli import EXIT_PAUSED, exit_code_for_outcome

print(exit_code_for_outcome("complete"), exit_code_for_outcome("interrupted"),
      exit_code_for_outcome("error"), EXIT_PAUSED)   # 0 2 1 2
```

## Errors are one line

A can't-run failure prints a single `error:` (or `Error:`) line on stderr, never a
Python traceback. To see the traceback, set `LANGSTAGE_DEBUG=1`, or use the
surface's own flag (`langstage-cli -v`, `langstage run --debug`,
`langstage-vscode-sidecar --traceback`).
