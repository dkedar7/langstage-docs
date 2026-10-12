"""Support triage: a customer-care agent that works a ticket queue in parallel.

Asked to work the queue, it starts one background task per open ticket (LangStage's
Board shows them). Each task reads the ticket, looks up the order, checks the refund
policy, acts, and drafts the reply. A refund over $100 pauses for a care manager's
approval with LangGraph's ``interrupt()``, which you answer from the Board.

Run it (from this folder):

    pip install langstage langchain-anthropic
    export ANTHROPIC_API_KEY=...        # or OPENROUTER_API_KEY=... (pip install langchain-openai)
    langstage run --agent agent.py:graph --workspace workspace

Then ask: "Work through the open support tickets."
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.types import interrupt
from langstage_core.tasks import TASK_TOOLS

APPROVAL_THRESHOLD = 100.00


def make_model():
    """Claude Sonnet 5: through OpenRouter when OPENROUTER_API_KEY is set, else directly."""
    if os.environ.get("OPENROUTER_API_KEY"):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model="anthropic/claude-sonnet-5",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
    return init_chat_model("anthropic:claude-sonnet-5")


# The desk's files live in the workspace LangStage serves (its working directory).
def _desk() -> Path:
    return Path.cwd()


def _orders() -> dict:
    return json.loads((_desk() / "orders.json").read_text(encoding="utf-8"))


def _subject(ticket: Path) -> str:
    for line in ticket.read_text(encoding="utf-8").splitlines():
        if line.startswith("Subject:"):
            return line.removeprefix("Subject:").strip()
    return ""


@tool
def list_open_tickets() -> str:
    """List the support tickets that have no reply yet: id and subject."""
    outbox = _desk() / "outbox"
    open_ = [
        f"{t.stem}: {_subject(t)}"
        for t in sorted((_desk() / "tickets").glob("*.md"))
        if not (outbox / t.name).exists()
    ]
    return "\n".join(open_) or "No open tickets."


@tool
def read_ticket(ticket_id: str) -> str:
    """Read a ticket's full text (sender, order number, subject, message)."""
    path = _desk() / "tickets" / f"{ticket_id}.md"
    if not path.exists():
        return f"No ticket {ticket_id}."
    return path.read_text(encoding="utf-8")


@tool
def lookup_order(order_id: str) -> str:
    """Look up an order: customer, items, shipping, total, status and dates."""
    order = _orders().get(order_id)
    return json.dumps(order, indent=2) if order else f"No order {order_id}."


@tool
def read_policy() -> str:
    """Read the customer care policy: refunds, exchanges, order status, tone."""
    return (_desk() / "policy.md").read_text(encoding="utf-8")


@tool
def issue_refund(order_id: str, amount: float, reason: str) -> str:
    """Refund an amount to the customer's original payment method.

    Refunds over $100 pause for a care manager's approval before any money moves.
    """
    order = _orders().get(order_id)
    if order is None:
        return f"No order {order_id}."
    if amount <= 0 or amount > order["total"]:
        return f"Refused: the refund must be between $0 and the order total, ${order['total']:.2f}."

    approved_by = "auto (under $100)"
    if amount > APPROVAL_THRESHOLD:
        # Pause the run until a human decides. LangStage shows this request in the
        # chat's approval dialog, or on the Board for a background task.
        answer = interrupt({
            "action_requests": [{
                "name": "issue_refund",
                "args": {"order_id": order_id, "amount": amount, "reason": reason},
                "description": (
                    f"Refund ${amount:.2f} to {order['customer']} for {order_id}. "
                    f"Refunds over ${APPROVAL_THRESHOLD:.0f} need a care manager's approval."
                ),
            }],
            "review_configs": [
                {"action_name": "issue_refund", "allowed_decisions": ["approve", "edit", "reject"]}
            ],
        })
        decisions = answer.get("decisions", []) if isinstance(answer, dict) else answer or []
        decision = decisions[0] if decisions else {}
        kind = decision.get("type")
        if kind == "reject":
            note = decision.get("message") or "no reason given"
            return f"The care manager rejected this refund ({note}). Don't refund; tell the customer a specialist will follow up."
        if kind == "edit":
            amount = float(decision["edited_action"]["args"].get("amount", amount))
        elif kind != "approve":
            return f"No refund issued: unexpected decision {decision!r}."
        approved_by = "care manager"

    ledger = _desk() / "refunds.json"
    refunds = json.loads(ledger.read_text(encoding="utf-8")) if ledger.exists() else []
    refund_id = f"RF-{2000 + len(refunds) + 1}"
    refunds.append({
        "refund_id": refund_id, "order_id": order_id, "amount": round(amount, 2),
        "reason": reason, "approved_by": approved_by, "date": date.today().isoformat(),
    })
    ledger.write_text(json.dumps(refunds, indent=2), encoding="utf-8")
    return f"Refund {refund_id} issued: ${amount:.2f} on {order_id} (approved by {approved_by})."


@tool
def send_reply(ticket_id: str, message: str) -> str:
    """Send the customer the reply to their ticket. Closes the ticket."""
    outbox = _desk() / "outbox"
    outbox.mkdir(exist_ok=True)
    (outbox / f"{ticket_id}.md").write_text(message.strip() + "\n", encoding="utf-8")
    return f"Reply to {ticket_id} sent."


SYSTEM_PROMPT = f"""You are the customer care agent for Northwind Outfitters, an outdoor gear shop.
Today is {date.today():%A, %B %d, %Y}.

When asked to work the queue: call list_open_tickets, then start ONE background task
per open ticket with start_async_task. Title each "<ticket id> · <short summary>" and
give it a self-contained prompt: "Resolve support ticket <id>: <one-line summary>."
Then tell the user, in two or three lines, which tasks you started. Don't resolve the
tickets yourself and don't check on the tasks.

When asked to resolve ONE ticket: read it, look up its order, read the policy, then
take the action the policy calls for (a refund, an exchange link, or a status update)
and finish with send_reply. Never start background tasks for a single ticket. Refunds
over $100 wait for a care manager's approval inside issue_refund; if it is rejected,
don't refund. End with a one-line summary of what you did."""

graph = create_agent(
    make_model(),
    tools=[list_open_tickets, read_ticket, lookup_order, read_policy, issue_refund, send_reply, *TASK_TOOLS],
    system_prompt=SYSTEM_PROMPT,
    name="Northwind Support",
)
