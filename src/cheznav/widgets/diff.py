import difflib

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.widgets import Label, Static

_NO_NEWLINE = "⏎ No newline at end of file"

# Diff highlight colors (Dracula-inspired)
_STYLE_DELETED = "on #3d1f1f"
_STYLE_INSERTED = "on #1f3d1f"
_STYLE_PADDING = "on #1a1a2e"


class _DiffBuilder:
    """Builds side-by-side Rich Text diff panels from two strings."""

    def __init__(self, left_lines: list[str], right_lines: list[str]) -> None:
        self._left_lines = left_lines
        self._right_lines = right_lines
        self.left = Text()
        self.right = Text()
        self._left_lineno = 0
        self._right_lineno = 0

    def _append_left(self, line: str, style: str = "") -> None:
        self._left_lineno += 1
        self.left.append(f"{self._left_lineno:>4}  {line}\n", style=style)

    def _append_right(self, line: str, style: str = "") -> None:
        self._right_lineno += 1
        self.right.append(f"{self._right_lineno:>4}  {line}\n", style=style)

    def apply_opcode(self, op: str, i1: int, i2: int, j1: int, j2: int) -> None:
        if op == "equal":
            for k in range(i2 - i1):
                self._append_left(self._left_lines[i1 + k])
                self._append_right(self._right_lines[j1 + k])
        elif op == "replace":
            for k in range(max(i2 - i1, j2 - j1)):
                if i1 + k < i2:
                    self._append_left(self._left_lines[i1 + k], style=_STYLE_DELETED)
                else:
                    self.left.append("     \n", style=_STYLE_PADDING)
                if j1 + k < j2:
                    self._append_right(self._right_lines[j1 + k], style=_STYLE_INSERTED)
                else:
                    self.right.append("     \n", style=_STYLE_PADDING)
        elif op == "delete":
            for k in range(i2 - i1):
                self._append_left(self._left_lines[i1 + k], style=_STYLE_DELETED)
                self.right.append("     \n", style=_STYLE_PADDING)
        elif op == "insert":
            for k in range(j2 - j1):
                self.left.append("     \n", style=_STYLE_PADDING)
                self._append_right(self._right_lines[j1 + k], style=_STYLE_INSERTED)


def _build_diff_panels(left: str, right: str) -> tuple[Text, Text]:
    """Build Rich Text objects with diff highlighting for both sides."""
    left_lines = left.splitlines()
    right_lines = right.splitlines()

    builder = _DiffBuilder(left_lines, right_lines)
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, left_lines, right_lines).get_opcodes():
        builder.apply_opcode(op, i1, i2, j1, j2)

    if not left.endswith("\n") and left_lines:
        builder.left.append(f"      {_NO_NEWLINE}\n", style="dim italic")
    if not right.endswith("\n") and right_lines:
        builder.right.append(f"      {_NO_NEWLINE}\n", style="dim italic")

    return builder.left, builder.right


class DiffScroll(ScrollableContainer):
    """Scrollable diff pane with both vertical and horizontal scrolling."""


class DiffView(Container):
    """Inline side-by-side diff that replaces the two panes."""

    DEFAULT_CSS = """
    DiffView {
        layout: vertical;
        height: 100%;
        width: 100%;
    }

    #diff-file-title {
        width: 100%;
        height: 1;
        text-style: bold;
        padding: 0 1;
        background: $boost;
    }

    #diff-panels {
        height: 1fr;
        width: 100%;
    }

    .diff-pane {
        width: 1fr;
        height: 100%;
        border-right: solid $primary;
    }

    .diff-pane:last-child {
        border-right: none;
    }

    .diff-pane-title {
        dock: top;
        height: 1;
        padding: 0 1;
        text-style: bold;
        background: $boost;
    }

    .diff-pane DiffScroll {
        height: 1fr;
    }

    .diff-pane Static {
        width: auto;
    }
    """

    def __init__(self, title: str, left: str, right: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._left = left
        self._right = right

    def compose(self) -> ComposeResult:
        # Display: left pane = disk (current file), right pane = chezmoi (target state)
        # _build_diff_panels(old, new): pass disk first so chezmoi changes appear as additions
        left_text, right_text = _build_diff_panels(self._right, self._left)

        yield Label(self._title, id="diff-file-title")
        with Horizontal(id="diff-panels"):
            with Container(classes="diff-pane"):
                yield Label("[$warning]◀ current file on disk[/]", classes="diff-pane-title")
                with DiffScroll():
                    yield Static(left_text)
            with Container(classes="diff-pane"):
                yield Label("[$success]chezmoi target state ▶[/]", classes="diff-pane-title")
                with DiffScroll():
                    yield Static(right_text)
