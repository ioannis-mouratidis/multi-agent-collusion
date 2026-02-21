"""Game state tracking."""

from dataclasses import dataclass, field


@dataclass
class Message:
    sender: str
    recipient: str
    content: str
    is_reply: bool = False


@dataclass
class RoundRecord:
    round_number: int
    pool_before: int
    harvests: dict[str, int]
    crash: bool
    pool_after: int
    messages: list[Message] = field(default_factory=list)
    replies: list[Message] = field(default_factory=list)
    reasoning: dict[str, str] = field(default_factory=dict)
    agent_resources_snapshot: dict[str, int] = field(default_factory=dict)


class GameState:
    def __init__(self, agent_ids: list[str], starting_resources: int, pool_start: int):
        self.round_number = 0
        self.pool = pool_start
        self.pool_start = pool_start
        self.agents: dict[str, int] = {aid: starting_resources for aid in agent_ids}
        self.agent_ids = agent_ids
        self.history: list[RoundRecord] = []

    def apply_harvests(self, harvests: dict[str, int]) -> bool:
        """Apply harvest decisions. Returns True if crash occurred."""
        total = sum(harvests.values())
        crash = total > self.pool

        if not crash:
            for agent_id, amount in harvests.items():
                self.agents[agent_id] += amount
            self.pool -= total

        return crash

    def apply_regrowth(self, rate: float) -> None:
        """Grow the pool by the regrowth rate, rounded down."""
        growth = int(self.pool * rate)
        self.pool += growth

    def record_round(self, harvests: dict[str, int], crash: bool, pool_before: int,
                     messages: list[Message], replies: list[Message],
                     reasoning: dict[str, str]) -> RoundRecord:
        record = RoundRecord(
            round_number=self.round_number,
            pool_before=pool_before,
            harvests=harvests,
            crash=crash,
            pool_after=self.pool,
            messages=messages,
            replies=replies,
            reasoning=reasoning,
            agent_resources_snapshot=dict(self.agents),
        )
        self.history.append(record)
        return record

    def is_game_over(self, max_rounds: int) -> bool:
        return self.round_number >= max_rounds or self.pool <= 0
