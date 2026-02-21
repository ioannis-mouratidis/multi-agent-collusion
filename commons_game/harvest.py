"""Phase 2 — Harvest: apply harvest decisions and detect crashes."""

from agent import AgentResponse
from game_state import GameState
from config import REGROWTH_RATE


def execute_harvest(state: GameState, decisions: dict[str, AgentResponse]) -> tuple[dict[str, int], bool]:
    """
    Execute harvest phase. Returns (harvests_dict, crash_occurred).
    """
    harvests = {aid: d.harvest for aid, d in decisions.items()}
    pool_before = state.pool

    crash = state.apply_harvests(harvests)

    if not crash:
        state.apply_regrowth(REGROWTH_RATE)

    return harvests, crash
