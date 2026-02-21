"""The Commons Game — main entry point and game loop."""

import asyncio
import os
import sys

import anthropic

import config
from game_state import GameState, Message
from agent import Agent
from communication import run_communication_phase
from harvest import execute_harvest
from logger import GameLogger
from display import (
    console, show_banner, show_round_header,
    show_round_results, show_messages_detail, show_game_over,
)
from analysis import run_analysis


async def run_game() -> None:
    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[bold red]Error:[/] ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    # Initialize
    client = anthropic.AsyncAnthropic(api_key=api_key)
    state = GameState(config.AGENT_IDS, config.STARTING_RESOURCES, config.POOL_START)
    agents = {aid: Agent(aid, client) for aid in config.AGENT_IDS}
    logger = GameLogger()
    logger.log_config({
        "num_agents": config.NUM_AGENTS,
        "agent_ids": config.AGENT_IDS,
        "starting_resources": config.STARTING_RESOURCES,
        "pool_start": config.POOL_START,
        "num_rounds": config.NUM_ROUNDS,
        "max_harvest": config.MAX_HARVEST,
        "regrowth_rate": config.REGROWTH_RATE,
        "model": config.MODEL,
        "temperature": config.TEMPERATURE,
    })

    # Track pending messages to deliver next round
    pending_messages: dict[str, list[dict]] = {aid: [] for aid in config.AGENT_IDS}

    show_banner()
    console.print(f"  Model: {config.MODEL}")
    console.print(f"  Agents: {', '.join(config.AGENT_IDS)}")
    console.print(f"  Starting resources: {config.STARTING_RESOURCES} each")
    console.print(f"  Pool: {config.POOL_START}  |  Rounds: {config.NUM_ROUNDS}")
    console.print(f"  Regrowth rate: {config.REGROWTH_RATE*100:.0f}%")
    console.print()

    for round_num in range(1, config.NUM_ROUNDS + 1):
        state.round_number = round_num
        pool_before = state.pool

        show_round_header(round_num, config.NUM_ROUNDS, state.pool, config.POOL_START)

        # Phase 1 + 2 combined: each agent gets state + pending messages → decides message + harvest
        console.print("  [dim]Agents deliberating...[/]")

        decision_tasks = []
        for aid in config.AGENT_IDS:
            decision_tasks.append(
                agents[aid].decide(
                    round_number=round_num,
                    num_rounds=config.NUM_ROUNDS,
                    agent_resources=dict(state.agents),
                    pool=state.pool,
                    history=state.history,
                    incoming_messages=pending_messages[aid],
                )
            )

        decisions_list = await asyncio.gather(*decision_tasks)
        decisions = dict(zip(config.AGENT_IDS, decisions_list))

        # Phase 1b: process communication (send messages, collect replies)
        messages, replies = await run_communication_phase(
            agents, decisions, round_num, state.pool,
        )

        # Prepare pending messages for NEXT round (messages sent this round + replies)
        pending_messages = {aid: [] for aid in config.AGENT_IDS}
        for m in messages:
            pending_messages[m.recipient].append({
                "sender": m.sender,
                "content": m.content,
                "is_reply": False,
            })
        for m in replies:
            pending_messages[m.recipient].append({
                "sender": m.sender,
                "content": m.content,
                "is_reply": True,
            })

        # Phase 2: execute harvests
        harvests, crash = execute_harvest(state, decisions)

        # Collect reasoning
        reasoning = {aid: d.reasoning for aid, d in decisions.items()}

        # Record round
        record = state.record_round(harvests, crash, pool_before, messages, replies, reasoning)
        logger.log_round(record)

        # Display results
        show_round_results(record, config.AGENT_IDS)
        show_messages_detail(record)

        # Check end condition
        if state.pool <= 0:
            console.print("[bold red]  The common pool is depleted! Game ends early.[/]")
            break

    # Game over
    winner = show_game_over(state)
    logger.log_final(state, winner)

    # Analysis
    analysis_results = run_analysis(state)
    logger.data["analysis"] = analysis_results

    # Save log
    log_path = logger.save()
    console.print(f"  Full game log saved to: [cyan]{log_path}[/]")
    console.print()


def main():
    asyncio.run(run_game())


if __name__ == "__main__":
    main()
