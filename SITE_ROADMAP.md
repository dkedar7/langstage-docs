# Site roadmap

A short backlog of improvements that make this site easier to use. The daily sweep
takes one item per run when the run isn't already heavy. Each item is one reviewable
PR, and it merges only with both checks green. Move an item to **Done** with its PR
number when it merges. Add ideas at the end of **Next**, and reorder the list when
priorities change.

Real-model recordings for the Gallery cost about $1 at most per sweep. Keys come only
through `op run`, and each Gallery page names the model it was recorded on. OpenRouter
has credit again (topped up by Nov 27). A Codraft take costs about $0.45, so plan on
two takes per sweep at most.

## Next

1. **Gallery: JupyterLab.** An analysis notebook in which a cell fails. The agent reads
   the traceback with `read_cell_outputs` and proposes the fix. Real model.
2. **Gallery: Hermes.** Memory and skills across two sessions, then
   `memory show --history`. Real model.
3. **Gallery: VS Code.** Editing a repository from the panel, with an approval. Real
   model.
4. **Recipes, second batch.** Add answers as questions come up: a custom system
   prompt per stage, a workspace folder for file tools, tracing with LangSmith.

## Done

- **Test your agent in CI** (`docs/guides/test-in-ci.md`, under Guides): a keyless
  GitHub Actions job (`check --json`, `--verify`, the exit-`2` approval gate, pytest
  with `verify()`) around a scripted model. Linked from Installation and Exit codes.
- **Gallery: Codraft** (`docs/gallery/board-update.md`): a board update drafted from the
  numbers, suggestions accepted, a comment-driven correction, and a checkpoint's
  changes. Linked from the Documents page and "Which stage should I use?".
- **Recipes** (`docs/guides/recipes.md`): any model through OpenRouter, an approval
  step, a scheduled prompt, the web app behind a proxy, serving to your own frontend.
- **Troubleshooting page** (`docs/getting-started/troubleshooting.md`): the first
  errors people hit, each with the real message and the fix, under Getting started.
- **Home: Codraft tab** (`demos/scripts/record_codraft.py`, keyless), so the home page
  now has a demo for every stage.
- **"Which stage should I use?"** (`docs/getting-started/choose-a-stage.md`), first in
  Getting started and linked from the home page.
- **Cross-links** between the stage pages and the Gallery.
- **Home: Hermes tab**, using the keyless demo CI already records.
- **What's new page** (`docs/whats-new.md`), with this file.
