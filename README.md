# langstage-docs

Source for the **LangStage** documentation site — *every stage for your
LangGraph agent*.

**Live:** https://dkedar7.github.io/langstage-docs/

Built with [MkDocs](https://www.mkdocs.org/) +
[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) (the same
stack FastAPI's docs use). Covers the whole family: `langstage` (web),
`langstage-cli`, `langstage-jupyter`, `langstage-vscode`, `langstage-hermes`,
and the shared `langstage-core` core.

## Local development

```bash
pip install -r requirements.txt
mkdocs serve              # http://127.0.0.1:8000
mkdocs build --strict     # full build; fails on broken internal links / missing images
```

Run `mkdocs build --strict` before you push. The deploy workflow does not run it
yet, so a broken link is only caught if you run it locally.

## Deploy

Pushing to `main` triggers `.github/workflows/docs.yml`, which runs
`mkdocs gh-deploy` to publish the built site to the `gh-pages` branch.
