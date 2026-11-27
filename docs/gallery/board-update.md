# Board update with suggestions

<figure markdown="span">
  <video width="1100" style="max-width:100%; height:auto" controls muted playsinline preload="metadata"
         poster="../../assets/gallery/board-update.png"
         aria-label="The agent drafts two sections of a board update from the quarter's numbers; they arrive as suggestions the author accepts. The author saves a checkpoint, comments that finance corrected the return rate, and accepts the agent's edit. The checkpoint view then shows the one changed paragraph as a word diff.">
    <source src="../../assets/gallery/board-update.webm" type="video/webm">
  </video>
  <figcaption>Claude Sonnet 5, unscripted, one take. Waits on the model play at 3x; reading and accepting the suggestions plays at real speed.</figcaption>
</figure>

**Stage:** [Documents](../stages/codraft.md), `langstage-codraft`. **Shows:** your own
agent co-authoring a document, suggestions you accept, a comment the agent acts on,
and a checkpoint that shows what changed since.

A quarterly update goes through several hands. Someone drafts it from the numbers,
finance checks the figures, and the board reads the final version. This example is
that loop on one page. The authors write the outline and the ask. The agent drafts
the sections in between from the data, and changes nothing without the authors' yes.

## What happens

1. The document holds the authors' outline: an opening, headings for **Results** and
   **Returns**, and the ask, $120,000 for a tent-pole fix.
2. You ask the agent, Juniper, to "draft a short paragraph under Results and one under
   Returns from the Q3 numbers and the ops notes." It reads the metrics and the notes,
   works out each percentage change with a tool rather than guessing, and proposes
   both paragraphs. They wait on the page as suggested blocks. The return rate is
   marked preliminary, as the data says.
3. You accept both, then save a checkpoint called **Sent to finance**.
4. Finance closes the books and corrects the return rate from 6.4% to 7.1%. You leave
   that as a comment on the Returns paragraph and click **Address all comments**. The
   agent proposes an edit that changes the figure, drops "preliminary", and leaves the
   rest alone. You read the diff and accept it.
5. **Document → Checkpoints → 1 change since…** shows exactly what changed since the
   version finance saw: one paragraph, as a word diff. **Export redline** turns the same
   diff into a Word file with tracked changes.

## The agent

94 lines in [`gallery/board-update/agent.py`](https://github.com/dkedar7/langstage-docs/blob/main/gallery/board-update/agent.py).
The parts that matter:

- **Your tools, next to Codraft's.** `read_metrics` and `read_ops_notes` read the
  source material in
  [`workspace/`](https://github.com/dkedar7/langstage-docs/tree/main/gallery/board-update/workspace),
  and `percent_change` does the arithmetic. `CodraftMiddleware` adds Codraft's own
  tools for reading the document and proposing edits, plus its co-author prompt.
- **Instructions through `extra_prompt`.** The middleware appends them to the co-author
  prompt: take every figure from the tools, say when one is preliminary, draft only
  the sections asked for, and when a comment corrects a figure, change only what
  depends on it.
- **A name.** `create_agent(..., name="Juniper")`, so the editor says "Ask Juniper" and
  "Suggestions from Juniper".

There's no approval code in the agent. Codraft turns every change the agent proposes
into a suggestion on the block, and the author decides.

<!-- snippet: skip -->
```python title="gallery/board-update/agent.py"
--8<-- "gallery/board-update/agent.py"
```

## Run it yourself

<!-- snippet: check -->
```bash
git clone https://github.com/dkedar7/langstage-docs
cd langstage-docs/gallery/board-update
pip install langstage-codraft langchain-anthropic
export ANTHROPIC_API_KEY=...
langstage-codraft run --agent agent.py:graph
```

Make a document with a **Results** and a **Returns** heading, then ask "Draft a short
paragraph under Results and one under Returns from the Q3 numbers and the ops notes."
To use OpenRouter instead, set `OPENROUTER_API_KEY` and `pip install langchain-openai`.

The company is fictional: Northwind Outfitters, the same shop as the
[support triage](support-triage.md) example, whose cracked tent poles show up here
as a quarter's returns. For your own reports, point the reading tools at your metrics
store or a spreadsheet export. Suggestions, comments and checkpoints work the same way.

## Related

- [Documents](../stages/codraft.md): the stage, including
  [bringing your own agent](../stages/codraft.md#bring-your-own-agent),
  [checkpoints](../stages/codraft.md#checkpoints-what-changed-since-and-going-back-011)
  and the [redline Word export](../stages/codraft.md#redline-word-export-012).
- [Support triage](support-triage.md): the same company's support desk, on the web
  app's Board.

## About this recording

Recorded on 2026-11-27 with Claude Sonnet 5 (through OpenRouter), langstage-codraft
0.12.5 and langstage-core 1.0.70. The run is unscripted: the model chose every tool
call and wrote every paragraph. The recorder created the outline through Codraft's
REST API before the clip starts, then typed the request, the checkpoint name and the
comment. Stretches where the screen is waiting on the model play at 3x. The recorder
is
[`demos/gallery/record_board_update.py`](https://github.com/dkedar7/langstage-docs/blob/main/demos/gallery/record_board_update.py).
