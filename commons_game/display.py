"""Rich-based terminal display for the game."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from game_state import GameState, RoundRecord

console = Console()


def show_banner() -> None:
    banner = Text("THE COMMONS GAME", style="bold white on blue", justify="center")
    console.print(Panel(banner, box=box.DOUBLE, style="blue", width=60))
    console.print()


def show_round_header(round_number: int, num_rounds: int, pool: int, pool_start: int) -> None:
    console.rule(f"[bold cyan]Round {round_number}/{num_rounds}[/]")

    bar_width = 40
    filled = max(0, int((pool / pool_start) * bar_width)) if pool_start > 0 else 0
    bar = "█" * filled + "░" * (bar_width - filled)
    pool_color = "green" if pool > pool_start * 0.5 else ("yellow" if pool > pool_start * 0.2 else "red")
    console.print(f"  Common Pool: [{pool_color}]{bar}[/] {pool}/{pool_start}")
    console.print()


def show_round_results(record: RoundRecord, agent_ids: list[str]) -> None:
    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
    table.add_column("Agent", style="cyan", width=8)
    table.add_column("Resources", justify="right", width=10)
    table.add_column("Harvested", justify="right", width=10)
    table.add_column("Message", width=24)

    for aid in agent_ids:
        res = record.agent_resources_snapshot.get(aid, "?")
        harvest = record.harvests.get(aid, "?")

        # Find if this agent sent a message
        msg_display = "—"
        for m in record.messages:
            if m.sender == aid:
                msg_display = f"→ {m.recipient}"
                break

        harvest_style = ""
        if record.crash:
            harvest_style = "red"
        elif harvest == 3:
            harvest_style = "yellow"
        elif harvest == 0:
            harvest_style = "green"

        table.add_row(
            aid,
            str(res),
            f"[{harvest_style}]{harvest}[/]" if harvest_style else str(harvest),
            msg_display,
        )

    console.print(table)

    total_harvested = sum(record.harvests.values())
    if record.crash:
        console.print(f"  [bold red]CRASH![/] Total requested: {total_harvested} > Pool: {record.pool_before}. Nobody receives anything.")
    else:
        console.print(f"  Total Harvested: {total_harvested}  |  Pool After Regrowth: {record.pool_after}")
    console.print()


def show_messages_detail(record: RoundRecord) -> None:
    """Show that messages were exchanged (content redacted for observer view)."""
    if not record.messages and not record.replies:
        return
    for m in record.messages:
        console.print(f"  [dim]📨 Agent {m.sender} → Agent {m.recipient} (private message)[/]")
    for m in record.replies:
        console.print(f"  [dim]↩  Agent {m.sender} → Agent {m.recipient} (reply)[/]")
    console.print()


def show_game_over(state: GameState) -> None:
    console.print()
    console.rule("[bold red]GAME OVER[/]")
    console.print()

    sorted_agents = sorted(state.agents.items(), key=lambda x: x[1], reverse=True)
    winner = sorted_agents[0][0]

    table = Table(title="Final Standings", box=box.DOUBLE_EDGE, show_header=True, header_style="bold")
    table.add_column("Rank", justify="center", width=6)
    table.add_column("Agent", style="cyan", width=8)
    table.add_column("Resources", justify="right", width=10)

    for i, (aid, res) in enumerate(sorted_agents):
        rank = str(i + 1)
        style = "bold green" if i == 0 else ""
        table.add_row(rank, f"[{style}]{aid}[/]" if style else aid,
                       f"[{style}]{res}[/]" if style else str(res))

    console.print(table)
    console.print(f"\n  [bold green]Winner: Agent {winner}[/] with {sorted_agents[0][1]} resources!")

    # Pool trajectory
    if state.history:
        console.print(f"  Final pool: {state.pool}")
        crash_count = sum(1 for r in state.history if r.crash)
        console.print(f"  Crash rounds: {crash_count}/{len(state.history)}")
    console.print()

    return winner
