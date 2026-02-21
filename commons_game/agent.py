"""Agent class — wraps LLM calls for each game agent."""

import asyncio
import re

import anthropic

from config import MODEL, MAX_RETRIES, API_TIMEOUT, TEMPERATURE, MAX_TOKENS, API_DELAY
from prompts import system_prompt, round_prompt, reply_prompt
from game_state import Message


class AgentResponse:
    def __init__(self, message_to: str | None, message_content: str | None,
                 harvest: int, reasoning: str):
        self.message_to = message_to
        self.message_content = message_content
        self.harvest = harvest
        self.reasoning = reasoning


class Agent:
    def __init__(self, agent_id: str, client: anthropic.AsyncAnthropic):
        self.agent_id = agent_id
        self.client = client
        self.system = system_prompt(agent_id)

    async def decide(self, round_number: int, num_rounds: int,
                     agent_resources: dict[str, int], pool: int,
                     history: list, incoming_messages: list[dict]) -> AgentResponse:
        """Main round call: get message + harvest decision."""
        user_msg = round_prompt(
            self.agent_id, round_number, num_rounds,
            agent_resources, pool, history, incoming_messages,
        )

        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    system=self.system,
                    messages=[{"role": "user", "content": user_msg}],
                    timeout=API_TIMEOUT,
                )
                text = response.content[0].text
                parsed = self._parse_decision(text)
                if parsed:
                    await asyncio.sleep(API_DELAY)
                    return parsed
            except Exception as e:
                wait = 2 ** attempt
                print(f"  [Agent {self.agent_id}] API error (attempt {attempt+1}): {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)

        # Default fallback
        return AgentResponse(
            message_to=None, message_content=None,
            harvest=1, reasoning="[PARSE FAILURE — defaulted to harvest 1]",
        )

    async def reply_to_message(self, sender_id: str, message_content: str,
                               round_number: int, pool: int) -> str | None:
        """Reply to an incoming message."""
        user_msg = reply_prompt(self.agent_id, sender_id, message_content, round_number, pool)

        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.messages.create(
                    model=MODEL,
                    max_tokens=256,
                    temperature=TEMPERATURE,
                    system=self.system,
                    messages=[{"role": "user", "content": user_msg}],
                    timeout=API_TIMEOUT,
                )
                text = response.content[0].text
                reply = self._parse_reply(text)
                await asyncio.sleep(API_DELAY)
                return reply
            except Exception as e:
                wait = 2 ** attempt
                print(f"  [Agent {self.agent_id}] Reply API error (attempt {attempt+1}): {e}")
                await asyncio.sleep(wait)

        return None

    def _parse_decision(self, text: str) -> AgentResponse | None:
        """Parse the structured response from the agent."""
        msg_to_match = re.search(r"MESSAGE_TO:\s*(.+)", text)
        msg_content_match = re.search(r"MESSAGE_CONTENT:\s*(.+)", text)
        harvest_match = re.search(r"HARVEST:\s*(\d)", text)
        reasoning_match = re.search(r"REASONING:\s*(.+)", text, re.DOTALL)

        if not harvest_match:
            return None

        harvest = int(harvest_match.group(1))
        if harvest < 0 or harvest > 3:
            return None

        msg_to = None
        msg_content = None
        if msg_to_match:
            raw = msg_to_match.group(1).strip().upper()
            if raw in ("A", "B", "C", "D") and raw != self.agent_id:
                msg_to = raw
        if msg_content_match:
            raw = msg_content_match.group(1).strip()
            if raw.upper() != "NONE":
                msg_content = raw

        # If either part is missing, send no message
        if not msg_to or not msg_content:
            msg_to = None
            msg_content = None

        reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

        return AgentResponse(msg_to, msg_content, harvest, reasoning)

    def _parse_reply(self, text: str) -> str | None:
        match = re.search(r"REPLY:\s*(.+)", text, re.DOTALL)
        if match:
            reply = match.group(1).strip()
            if reply.upper() == "NONE":
                return None
            return reply
        return None
