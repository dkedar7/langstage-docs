# Support triage with approvals

<figure markdown="span">
  <video width="1100" style="max-width:100%; height:auto" controls muted playsinline preload="metadata"
         poster="../../assets/gallery/support-triage.png"
         aria-label="The support agent starts four background tasks, one per ticket. Three finish on their own; the $189 refund waits in Review until it is approved on the Board.">
    <source src="../../assets/gallery/support-triage.webm" type="video/webm">
  </video>
  <figcaption>Claude Sonnet 5, unscripted, one take. Waits on the model play at 3x; reading the approval request plays at real speed.</figcaption>
</figure>

**Stage:** the web app, `langstage`. **Shows:** an agent that delegates work to
background copies of itself, the Board, and a human approval inside a tool.

Customer support is one of the most common jobs teams give an agent, and refunds are
where they want a person to decide. This example is that pattern at desk scale: an
agent that clears the routine tickets on its own and hands the refund decision to a
manager.

## What happens

1. You ask Northwind Support to "work through the open support tickets."
2. It lists the queue and starts one background task per ticket with
   `start_async_task`. Each task shows up on the Board, running a copy of the same
   agent.
3. Three tickets resolve on their own. A late express delivery gets its $8.95 shipping
   fee back (refunds under $100 go straight through), a jacket in the wrong size gets
   the exchange link, and "where are my shoes?" gets the tracking number and date.
4. The fourth is a tent that arrived with a cracked pole. The policy says a full
   refund, $189, and `issue_refund` pauses for a care manager's approval. The task
   moves to **Review**.
5. You open it on the Board. The request shows the order, the amount and the agent's
   reason, with **Approve**, **Edit** and **Reject**. You approve; the task resumes,
   issues the refund, replies to the customer and finishes.

## The agent

177 lines in [`gallery/support-triage/agent.py`](https://github.com/dkedar7/langstage-docs/blob/main/gallery/support-triage/agent.py).
The parts that matter:

- **Tools that read real files:** `list_open_tickets`, `read_ticket`, `lookup_order`
  (from `orders.json`) and `read_policy` (from `policy.md`), plus `send_reply`, which
  writes the reply to `outbox/`.
- **An approval inside a tool.** `issue_refund` calls LangGraph's `interrupt()` when
  the amount is over $100, with the request in LangChain's human-in-the-loop shape
  (`action_requests` plus `review_configs`). It goes on only after a decision: approve,
  edit the amount, or reject.
- **Delegation.** `TASK_TOOLS` from `langstage_core.tasks` lets the agent start
  background tasks, which LangStage runs and shows on the Board. The system prompt
  says when to delegate (the whole queue) and when not to (a single ticket).

<!-- snippet: skip -->
```python title="gallery/support-triage/agent.py"
--8<-- "gallery/support-triage/agent.py"
```

## Run it yourself

<!-- snippet: check -->
```bash
git clone https://github.com/dkedar7/langstage-docs
cd langstage-docs/gallery/support-triage
pip install langstage langchain-anthropic
export ANTHROPIC_API_KEY=...
langstage run --agent agent.py:graph --workspace workspace
```

Ask "Work through the open support tickets." and open the **Board** tab. To use
OpenRouter instead, set `OPENROUTER_API_KEY` and `pip install langchain-openai`.

The shop is fictional: Northwind Outfitters, four tickets, four orders and a one-page
policy, all in [`workspace/`](https://github.com/dkedar7/langstage-docs/tree/main/gallery/support-triage/workspace).
For your own desk, replace the file-reading tools with calls to your ticketing and
order systems; the approval and the Board work the same way.

## About this recording

Recorded on 2026-10-11 with Claude Sonnet 5 (through OpenRouter), langstage 0.13.49
and langstage-core 1.0.47. The run is unscripted: the model chose every tool call and
wrote every reply. Stretches where the screen is waiting on the model play at 3x; the
approval request and the finished task play at real speed. The recorder is
[`demos/gallery/record_support_triage.py`](https://github.com/dkedar7/langstage-docs/blob/main/demos/gallery/record_support_triage.py).
