from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label

HELP_TEXT = """\
[b]Actions[/b]
  [b]Enter[/b]      Open actions menu for selected item
  [b]:[/b]          Open command palette (global actions)
  [b]v[/b]          Quick view file content

[b]Navigation[/b]
  [b]Tab[/b]        Switch pane
  [b]← →[/b]       Expand/collapse directory
  [b]↑ ↓ / j k[/b] Navigate tree

[b]Diff View[/b]
  [b]Enter[/b]      Actions (keep disk / use target / close)
  [b]Escape[/b]     Close diff
  [b]Tab[/b]        Switch diff panes

[b]Global[/b]
  [b]?[/b]          This help screen
  [b]q[/b]          Quit
"""


class HelpScreen(ModalScreen):
    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-dialog {
        width: 60;
        height: auto;
        max-height: 80%;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }

    #help-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #help-hint {
        margin-top: 1;
        color: $text-muted;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "close", "Close"),
        ("question_mark", "close", "Close"),
        ("q", "quit_app", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="help-dialog"):
            yield Label("cheznav — Keybindings", id="help-title")
            yield Label(HELP_TEXT)
            yield Label("Press [b]Escape[/b] or [b]?[/b] to close", id="help-hint")

    def action_close(self) -> None:
        self.dismiss()

    def action_quit_app(self) -> None:
        self.app.exit()
