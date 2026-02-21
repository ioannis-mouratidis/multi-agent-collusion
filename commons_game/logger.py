"""Structured JSON logging of the entire game."""

import json
import os
from datetime import datetime
from dataclasses import asdict

from game_state import GameState, RoundRecord, Message
from config import LOG_DIR


class GameLogger:
    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filepath = os.path.join(LOG_DIR, f"game_log_{ts}.json")
        self.data = {
            "timestamp": ts,
            "config": {},
            "rounds": [],
            "final_scores": {},
            "winner": None,
        }

    def log_config(self, config_dict: dict) -> None:
        self.data["config"] = config_dict

    def log_round(self, record: RoundRecord) -> None:
        round_data = {
            "round_number": record.round_number,
            "pool_before": record.pool_before,
            "harvests": record.harvests,
            "crash": record.crash,
            "pool_after": record.pool_after,
            "agent_resources": record.agent_resources_snapshot,
            "messages": [
                {"sender": m.sender, "recipient": m.recipient,
                 "content": m.content, "is_reply": m.is_reply}
                for m in record.messages
            ],
            "replies": [
                {"sender": m.sender, "recipient": m.recipient,
                 "content": m.content, "is_reply": m.is_reply}
                for m in record.replies
            ],
            "reasoning": record.reasoning,
        }
        self.data["rounds"].append(round_data)

    def log_final(self, state: GameState, winner: str) -> None:
        self.data["final_scores"] = dict(state.agents)
        self.data["winner"] = winner

    def save(self) -> str:
        with open(self.filepath, "w") as f:
            json.dump(self.data, f, indent=2)
        return self.filepath
