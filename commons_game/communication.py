"""Phase 1 — Communication: handle message sending and replies."""

import asyncio

from agent import Agent, AgentResponse
from game_state import Message


async def run_communication_phase(
    agents: dict[str, Agent],
    decisions: dict[str, AgentResponse],
    round_number: int,
    pool: int,
) -> tuple[list[Message], list[Message]]:
    """
    Process messages from agent decisions and collect replies.
    Returns (messages, replies).
    """
    messages: list[Message] = []
    replies: list[Message] = []

    # Collect outgoing messages from decisions
    outgoing: dict[str, Message] = {}  # keyed by recipient
    for agent_id, decision in decisions.items():
        if decision.message_to and decision.message_content:
            msg = Message(
                sender=agent_id,
                recipient=decision.message_to,
                content=decision.message_content,
            )
            messages.append(msg)
            # If multiple agents message the same recipient, all get delivered
            # but we track them separately for replies
            outgoing.setdefault(decision.message_to, [])
            outgoing[decision.message_to].append(msg)

    # Collect replies concurrently
    reply_tasks = []
    for recipient_id, msgs in outgoing.items():
        for msg in msgs:
            reply_tasks.append(
                _get_reply(agents[recipient_id], msg, round_number, pool)
            )

    reply_results = await asyncio.gather(*reply_tasks)
    for reply_msg in reply_results:
        if reply_msg:
            replies.append(reply_msg)

    return messages, replies


async def _get_reply(agent: Agent, msg: Message, round_number: int, pool: int) -> Message | None:
    reply_text = await agent.reply_to_message(msg.sender, msg.content, round_number, pool)
    if reply_text:
        return Message(
            sender=msg.recipient,
            recipient=msg.sender,
            content=reply_text,
            is_reply=True,
        )
    return None
