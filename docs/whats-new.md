# What's new

The changes you'd notice, newest first. Bug fixes that don't change how you use a
stage aren't listed; every package's full changelog is in its repository.

<!-- Add an entry only for a new feature, command, tool, route or setting, or a changed
     default or behaviour users will notice. One or two lines, linking to the page. -->

## November 2026

### Week of November 16

- **Web 0.13.68:** one window reads a conversation at a time. Opening it in a second
  window or tab gives a read-only copy, and **Continue here** moves it.
  [History](stages/web.md#history)
- **Web 0.13.67:** **History** lists past conversations from the server. Reopen one to
  continue it, or delete it, from any browser and after a restart.
  [History](stages/web.md#history)
- **Web 0.13.66:** TeX renders as math in chat, the task view and Canvas, with `\( … \)`
  inline and `\[ … \]` or `$$ … $$` for display. A single `$` stays a dollar sign.
  [Highlights](stages/web.md#highlights)
- **Codraft 0.11.0:** name a checkpoint, see what changed since, and restore it. The
  agent can list checkpoints and read the changes too.
  [Checkpoints](stages/codraft.md#checkpoints-what-changed-since-and-going-back-011)
- **JupyterLab 0.6.55:** a new `read_cell_outputs` tool lets the agent read a cell's
  saved output and traceback without running it again.
  [Notebook tools](stages/jupyter.md#notebook-tools-and-open-tabs)
- **Hermes 0.5.4:** memory changes are recorded in the audit log. You can list them,
  diff them, and roll back a single entry.
  [See and undo memory changes](stages/hermes.md#see-and-undo-memory-changes)
- **Terminal 0.6.54:** a quiet or piped one-shot run prints the final tool result when
  the turn ends on one. It exits `1` when there's nothing to print.
  [Scripting](stages/cli.md#scripting)
