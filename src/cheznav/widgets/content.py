from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Label, Static

from cheznav import THEME


def _make_syntax(content: str, language: str | None = None) -> Syntax:
    return Syntax(
        content,
        lexer=language or "text",
        theme=THEME,
        line_numbers=True,
        word_wrap=False,
    )


class ContentView(Container):
    """Inline content viewer that replaces panes (like DiffView)."""

    DEFAULT_CSS = """
    ContentView {
        height: 1fr;
    }

    ContentView #content-view-title {
        dock: top;
        height: 1;
        text-style: bold;
        padding: 0 1;
        background: $boost;
    }
    """

    def __init__(self, title: str, content: str, *, language: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._content = content
        self._language = language

    def compose(self) -> ComposeResult:
        yield Label(self._title, id="content-view-title")
        with VerticalScroll():
            yield Static(_make_syntax(self._content, self._language))

    def on_mount(self) -> None:
        self.query_one(VerticalScroll).focus()
