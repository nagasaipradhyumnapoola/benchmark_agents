from io import StringIO

from rich.console import Console

from benchlab.sdk import Laboratory


def test_startup_banner_and_menu_are_readable_without_color(tmp_path):
    from benchlab.terminal_ui import render_banner, render_menu

    stream = StringIO()
    console = Console(file=stream, width=90, color_system=None)
    lab = Laboratory(tmp_path)
    render_banner(console, lab)
    render_menu(console, lab)
    text = stream.getvalue()
    assert "Bench Agents" in text
    assert "Connect a model" in text and "Connect an agent" in text
    assert "0 models" in text and "0 agents" in text
    assert "\x1b[" not in text
    assert all(len(line) <= 90 for line in text.splitlines())


def test_narrow_terminal_uses_compact_heading(tmp_path):
    from benchlab.terminal_ui import render_banner

    stream = StringIO()
    render_banner(Console(file=stream, width=42, color_system=None), Laboratory(tmp_path))
    assert "Bench Agents" in stream.getvalue()
    assert all(len(line) <= 42 for line in stream.getvalue().splitlines())


def test_redirected_windows_encoding_does_not_crash_the_menu(tmp_path):
    from io import BytesIO, TextIOWrapper

    from benchlab.terminal_ui import render_banner, render_menu

    buffer = BytesIO()
    stream = TextIOWrapper(buffer, encoding="cp1252")
    console = Console(file=stream, width=90, color_system=None)
    lab = Laboratory(tmp_path)
    render_banner(console, lab)
    render_menu(console, lab)
    stream.flush()
    assert "Connect -> test -> inspect" in buffer.getvalue().decode("cp1252")
