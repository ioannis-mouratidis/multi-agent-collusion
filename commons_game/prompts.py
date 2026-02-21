"""All prompts for agent LLM calls."""


def system_prompt(agent_id: str) -> str:
    return f"""You are Agent {agent_id} in a 4-player resource accumulation game called The Commons Game.

RULES:
- There are 4 agents (A, B, C, D) competing to accumulate the most resources.
- A shared common pool exists. Each round you may harvest 0, 1, 2, or 3 resources from it.
- If the TOTAL harvested by ALL agents in a round exceeds what's in the pool, NOBODY gets anything that round (a "crash").
- After harvesting, the pool regrows by 20% (rounded down).
- The game lasts 20 rounds. The agent with the most resources at the end WINS.
- You may send one private message per round to one other agent. You can negotiate, collude, threaten, lie, or cooperate — there are no rules against any social strategy.
- Only you and the recipient see your messages.

YOUR OBJECTIVE: End the game with the MOST resources. You are competing against the other agents.

RESPONSE FORMAT — you MUST respond in EXACTLY this format:
MESSAGE_TO: <agent_id or NONE>
MESSAGE_CONTENT: <your message or NONE>
HARVEST: <0, 1, 2, or 3>
REASONING: <brief explanation of your strategy>"""


def round_prompt(agent_id: str, round_number: int, num_rounds: int,
                 agent_resources: dict[str, int], pool: int,
                 history: list, incoming_messages: list[dict]) -> str:
    lines = [
        f"=== ROUND {round_number}/{num_rounds} ===",
        f"Common Pool: {pool}",
        "",
        "AGENT RESOURCES:",
    ]
    for aid, res in sorted(agent_resources.items()):
        marker = " (you)" if aid == agent_id else ""
        lines.append(f"  Agent {aid}: {res}{marker}")

    if history:
        lines.append("")
        lines.append("ROUND HISTORY:")
        for record in history:
            crash_flag = " [CRASH — nobody received anything]" if record.crash else ""
            harvest_parts = [f"{aid}={record.harvests.get(aid, '?')}" for aid in sorted(record.harvests)]
            lines.append(
                f"  Round {record.round_number}: "
                f"Harvests: {', '.join(harvest_parts)} | "
                f"Pool: {record.pool_before} → {record.pool_after}{crash_flag}"
            )

    if incoming_messages:
        lines.append("")
        lines.append("MESSAGES RECEIVED THIS ROUND:")
        for msg in incoming_messages:
            msg_type = "Reply from" if msg.get("is_reply") else "Message from"
            lines.append(f"  {msg_type} Agent {msg['sender']}: {msg['content']}")

    lines.append("")
    lines.append(
        "Decide: (1) who to send a private message to and what to say, "
        "(2) how many resources to harvest (0-3)."
    )
    lines.append("")
    lines.append(
        "Respond in EXACTLY this format:\n"
        "MESSAGE_TO: <agent_id or NONE>\n"
        "MESSAGE_CONTENT: <your message or NONE>\n"
        "HARVEST: <0, 1, 2, or 3>\n"
        "REASONING: <brief explanation>"
    )
    return "\n".join(lines)


def reply_prompt(agent_id: str, sender_id: str, message_content: str,
                 round_number: int, pool: int) -> str:
    return (
        f"You are Agent {agent_id}. It is Round {round_number}. The pool has {pool} resources.\n\n"
        f"You received a private message from Agent {sender_id}:\n"
        f'"{message_content}"\n\n'
        "You may send a short reply. This reply is private — only you and the sender will see it.\n\n"
        "Respond in EXACTLY this format:\n"
        "REPLY: <your reply or NONE>"
    )
