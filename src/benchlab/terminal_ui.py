"""Terminal presentation: original banner, readable tables, and observed live progress."""

import asyncio
import re
import time

from rich import box
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from benchlab import __version__
from benchlab.analysis import summarize
from benchlab.settings import redact

_FONT = {
    "B": ["#### ", "#   #", "#### ", "#   #", "#### "],
    "E": ["#####", "#    ", "#### ", "#    ", "#####"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #"],
    "C": [" ####", "#    ", "#    ", "#    ", " ####"],
    "H": ["#   #", "#   #", "#####", "#   #", "#   #"],
    "A": [" ### ", "#   #", "#####", "#   #", "#   #"],
    "G": [" ####", "#    ", "# ###", "#   #", " ####"],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
    "S": [" ####", "#    ", " ### ", "    #", "#### "],
    "U": ["#   #", "#   #", "#   #", "#   #", " ### "],
    " ": ["     "] * 5,
}


def terminal_text(value):
    # Render untrusted control bytes visibly; never let a publisher/provider
    # issue terminal commands, clipboard requests, carriage returns or bidi overrides.
    return re.sub(
        r"[\x00-\x08\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]",
        lambda match: f"\\u{ord(match.group()):04x}",
        str(redact(value)),
    )


def safe(value, style=""):
    return Text(terminal_text(value), style=style)


def render_banner(console, lab):
    if console.width >= 64:
        glyph = "█" if console.encoding.lower().replace("-", "") == "utf8" else "#"
        logo = "\n".join(
            " ".join(_FONT[char][row] for char in "AGENT HUB").rstrip() for row in range(5)
        )
        heading = Text(logo.replace("#", glyph), style="bold #d8c98d")
    else:
        heading = Text("Agent Hub", style="bold #d8c98d")
    console.print(
        Panel(
            Group(
                heading,
                Text(
                    f"\nAgent Hub  /  {__version__}  /  Local evaluation workbench", style="bold"
                ),
            ),
            border_style="#66665e",
            padding=(1, 2),
        )
    )
    console.print(safe(f"Workspace: {lab.store.data_dir}", "dim"))
    arrow = "→" if console.encoding.lower().replace("-", "") == "utf8" else "->"
    console.print(
        Text(
            f"Connect {arrow} test {arrow} inspect. Keys stay private to your local process.",
            style="dim",
        )
    )


def render_menu(console, lab):
    models = len(lab.store.list_models())
    agents = len(lab.store.list_agents())
    experiments = len(lab.store.list_experiments())
    console.print()
    console.rule(f"{models} models  ·  {agents} agents  ·  {experiments} experiments", style="dim")
    table = Table(box=box.SIMPLE, expand=True, show_header=False, padding=(0, 1))
    table.add_column(style="bold #d8c98d", width=2, no_wrap=True)
    table.add_column(style="bold")
    if console.width >= 76:
        table.add_column(style="dim", ratio=1)
    actions = [
        ("1", "Connect a model", "Existing Ollama or chat API endpoint"),
        ("2", "Connect an agent", "A custom harness or native CLI product"),
        ("3", "Test models", "Compare one or several registered endpoints"),
        ("4", "Test model + agents", "One endpoint with selected custom harnesses"),
        ("5", "Test native agent", "Use the product's own configuration"),
        ("6", "Inspect/export results", "Failures, verified scores, and ZIP evidence"),
        ("7", "Compare saved runs", "Check conditions before comparing outcomes"),
        ("8", "Test multiple models + agents", "Preview and benchmark every selected pair"),
        ("0", "Exit", "Keep your saved connections and results"),
    ]
    for number, action, detail in actions:
        table.add_row(*([number, action, detail] if console.width >= 76 else [number, action]))
    console.print(table)


def render_results(console, lab, experiment):
    console.rule(safe(f"Experiment {experiment['id']}"), style="dim")
    console.print(
        safe(f"Execution: {experiment['status']} • task checks are reported separately", "bold")
    )
    for run in lab.store.list_runs(experiment["id"]):
        results = lab.store.list_results(run["id"])
        metrics = summarize(results)
        console.print(
            safe(
                f"\n{run['system_name']}  •  {metrics['passed']}/{metrics['total']} verified",
                "bold",
            )
        )
        console.print(safe(f"Run ID: {run['id']}", "dim"))
        table = Table("Task", "Check", "Time", box=box.SIMPLE_HEAD, expand=True)
        for result in results:
            table.add_row(
                safe(result.get("task_name") or result["task_id"]),
                Text(
                    "PASS" if result["passed"] else "FAIL",
                    style="green" if result["passed"] else "red",
                ),
                f"{result['duration_seconds']:.2f}s",
            )
        console.print(table)
        low, high = metrics["confidence_low"], metrics["confidence_high"]
        if low is not None and high is not None:
            console.print(
                Text(
                    f"95% Wilson interval: {low:.1%}–{high:.1%}. Public fixture samples limit inference.",
                    style="dim",
                )
            )
        console.print(
            safe(
                f"Tokens: {metrics['tokens'] if metrics['tokens'] is not None else 'unavailable'}  |  Calculated cost USD: {metrics['cost_usd'] if metrics['cost_usd'] is not None else 'unavailable'}"
            )
        )
        for result in results:
            if not result["passed"]:
                console.print(
                    Panel(
                        safe(
                            result.get("error")
                            or result["verification"].get("reason")
                            or "Independent verification rejected the output"
                        ),
                        title=safe(result["task_id"]),
                        border_style="red",
                    )
                )


async def execute_with_progress(lab, config, console):
    from benchlab.benchmarks.catalog import get_tasks

    experiment = await lab.engine.submit(config)
    total = (
        len(get_tasks(config.benchmark_id, config.task_ids or None))
        * config.trials
        * len(config.systems)
    )
    task = asyncio.create_task(lab.engine.execute(experiment["id"]))
    start = time.monotonic()
    try:
        with Live(
            console=console, refresh_per_second=4, transient=True, auto_refresh=False
        ) as live:
            while not task.done():
                runs = lab.store.list_runs(experiment["id"])
                done = sum(len(lab.store.list_results(run["id"])) for run in runs)
                live.update(
                    Panel(
                        Text(
                            f"{done}/{total} tasks recorded  •  {time.monotonic() - start:.1f}s elapsed\nCtrl+C interrupts execution and preserves evidence."
                        ),
                        title=Text("Running verified test", style="bold"),
                        border_style="#d8c98d",
                    ),
                    refresh=console.is_terminal,
                )
                await asyncio.sleep(0.1)
            return await task
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
