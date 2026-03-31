from typing import ClassVar, Final

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.screen import ModalScreen
from textual.widgets import Label, SelectionList, Static
from textual.widgets.selection_list import Selection


class _ConfirmableSelectionList(SelectionList):
    """SelectionList where Enter confirms (bubbles to parent screen) instead of toggling."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "confirm_parent", "Confirm", show=False),
    ]

    def action_confirm_parent(self) -> None:
        self.screen.action_confirm()


class AddFlagsScreen(ModalScreen[dict[str, bool] | None]):
    """Flag picker for chezmoi add, using SelectionList."""

    DEFAULT_CSS = """
    AddFlagsScreen {
        align: center middle;
        background: $background 80%;
    }

    #flags-dialog {
        padding: 1 2;
        width: 50;
        height: auto;
        border-left: vkey $accent;
        background: $surface;
    }

    #flags-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #flags-list {
        height: auto;
        max-height: 10;
        background: $surface;
        border: none;
        margin-bottom: 1;
    }

    #flags-hint {
        color: $text-muted;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("enter", "confirm", "Confirm"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, title: str, is_dir: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._is_dir = is_dir
        self._flag_values: list[str] = []

    def compose(self) -> ComposeResult:
        if self._is_dir:
            selections = [
                Selection("Recursive", "recursive", True),
                Selection("Exact", "exact", False),
            ]
        else:
            selections = [
                Selection("Autotemplate", "autotemplate", False),
                Selection("Create", "create", False),
                Selection("Encrypt", "encrypt", False),
                Selection("Follow", "follow", False),
                Selection("New", "new", False),
                Selection("Template", "template", False),
            ]
        self._flag_values = [s.value for s in selections]

        with Static(id="flags-dialog"):
            yield Label(self._title, id="flags-title")
            yield _ConfirmableSelectionList(*selections, id="flags-list")
            yield Label("[b]Space[/] toggle    [b]Enter[/] confirm    [b]Esc[/] cancel", id="flags-hint")

    def action_confirm(self) -> None:
        selected = set(self.query_one(SelectionList).selected)
        flags = {v: v in selected for v in self._flag_values}
        self.dismiss(flags)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ChattrScreen(ModalScreen[dict[str, bool] | None]):
    """Attribute picker for chezmoi chattr, pre-filled with current attributes."""

    DEFAULT_CSS = """
    ChattrScreen {
        align: center middle;
        background: $background 80%;
    }

    #chattr-dialog {
        padding: 1 2;
        width: 50;
        height: auto;
        border-left: vkey $accent;
        background: $surface;
    }

    #chattr-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #chattr-list {
        height: auto;
        max-height: 15;
        background: $surface;
        border: none;
        margin-bottom: 1;
    }

    #chattr-hint {
        color: $text-muted;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("enter", "confirm", "Confirm"),
        ("escape", "cancel", "Cancel"),
    ]

    FILE_ATTRIBUTES: Final = [
        "empty",
        "encrypted",
        "exact",
        "executable",
        "private",
        "readonly",
        "template",
    ]
    SCRIPT_ATTRIBUTES: Final = [
        "after",
        "before",
        "once",
        "onchange",
    ]

    def __init__(self, title: str, current: dict[str, bool], is_script: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._current = current
        self._is_script = is_script
        self._attributes = self.SCRIPT_ATTRIBUTES + self.FILE_ATTRIBUTES if is_script else self.FILE_ATTRIBUTES

    def compose(self) -> ComposeResult:
        selections = [Selection(attr, attr, self._current.get(attr, False)) for attr in self._attributes]
        with Static(id="chattr-dialog"):
            yield Label(self._title, id="chattr-title")
            yield _ConfirmableSelectionList(*selections, id="chattr-list")
            yield Label("[b]Space[/] toggle    [b]Enter[/] confirm    [b]Esc[/] cancel", id="chattr-hint")

    def action_confirm(self) -> None:
        sel = self.query_one(SelectionList)
        selected = set(sel.selected)
        # Build dict of only changed attributes
        changes = {}
        for attr in self._attributes:
            new_val = attr in selected
            old_val = self._current.get(attr, False)
            if new_val != old_val:
                changes[attr] = new_val
        self.dismiss(changes if changes else None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfirmScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }

    #confirm-dialog {
        padding: 1 2;
        width: auto;
        max-width: 80;
        height: auto;
        border-left: vkey $accent;
        background: $surface;
    }

    #confirm-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #confirm-command {
        margin-bottom: 1;
        color: $text;
        background: $boost;
        padding: 1;
    }

    #confirm-hint {
        color: $text-muted;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("enter", "confirm", "Confirm"),
        ("escape", "cancel", "Cancel"),
        ("y", "confirm", "Confirm"),
        ("n", "cancel", "Cancel"),
    ]

    def __init__(self, title: str, command: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._command = command

    def compose(self) -> ComposeResult:
        with Static(id="confirm-dialog"):
            yield Label(self._title, id="confirm-title")
            yield Label(f"$ {self._command}", id="confirm-command")
            yield Label("[b]y[/] / [b]Enter[/] to confirm    [b]n[/] / [b]Esc[/] to cancel", id="confirm-hint")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
