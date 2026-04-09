from pathlib import Path
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option

from cheznav.chezmoi import ManagedEntry


class ActionItem(Option):
    """An option that carries an action name."""

    def __init__(self, label: str, action: str, key_hint: str = "", disabled: bool = False) -> None:
        display = f" {label:<30} \\[{key_hint}]" if key_hint else f" {label}"
        super().__init__(display, disabled=disabled)
        self.action = action
        self.key_hint = key_hint


class _MenuScreen(ModalScreen[str | None]):
    """Base for compact popup menus."""

    DEFAULT_CSS = """
    _MenuScreen {
        align: center middle;
    }

    _MenuScreen .menu-box {
        width: auto;
        min-width: 30;
        max-width: 50;
        height: auto;
        background: $surface;
        border-left: vkey $accent;
        padding: 0 1;
    }

    _MenuScreen .menu-header {
        text-style: bold;
        color: $accent;
        width: 100%;
        padding: 0 1;
    }

    _MenuScreen OptionList {
        height: auto;
        max-height: 20;
        background: $surface;
        border: none;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "close", "Close"),
        ("q", "quit_app", "Quit"),
    ]

    def _get_actions(self) -> list[ActionItem]:
        """Override to provide actions list for key shortcut lookup."""
        return []

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if isinstance(event.option, ActionItem):
            self.dismiss(event.option.action)

    def on_key(self, event: Key) -> None:
        """Handle key shortcuts to select actions directly."""
        for item in self._get_actions():
            if item.key_hint and event.character == item.key_hint and not item.disabled:
                self.dismiss(item.action)
                event.prevent_default()
                event.stop()
                return

    def action_close(self) -> None:
        self.dismiss(None)

    def action_quit_app(self) -> None:
        self.dismiss(None)
        self.app.exit()


class ActionMenu(_MenuScreen):
    """Context-aware action menu for the selected item."""

    def __init__(self, title: str, actions: list[ActionItem]) -> None:
        super().__init__()
        self._title = title
        self._actions = actions

    def _get_actions(self) -> list[ActionItem]:
        return self._actions

    def compose(self) -> ComposeResult:
        with Container(classes="menu-box"):
            yield Label(self._title, classes="menu-header")
            yield OptionList(*self._actions)


class CommandPalette(_MenuScreen):
    """Global command palette."""

    @staticmethod
    def _make_commands() -> list[ActionItem]:
        return [
            ActionItem("Update (pull + apply)", "cmd_update"),
            ActionItem("View template data", "cmd_data"),
            ActionItem("Dump config", "cmd_dump_config"),
            ActionItem("Doctor", "cmd_doctor"),
            ActionItem("Help", "help"),
            ActionItem("Quit", "quit"),
        ]

    def __init__(self) -> None:
        super().__init__()
        self._commands = self._make_commands()

    def _get_actions(self) -> list[ActionItem]:
        return self._commands

    def compose(self) -> ComposeResult:
        with Container(classes="menu-box"):
            yield Label("Commands", classes="menu-header")
            yield OptionList(*self._commands)


def build_home_actions(
    path: Path | None,
    is_managed: bool,
    has_diff: bool,
    is_dir: bool = False,
    is_expanded: bool = False,
) -> tuple[str, list[ActionItem]]:
    """Build action list for a home tree selection."""
    if path is None:
        return "No file selected", []

    name = path.name

    if is_dir:
        toggle_label = "Collapse" if is_expanded else "Expand"
        actions = [
            ActionItem(toggle_label, "home_toggle", "space"),
            ActionItem("Add to chezmoi", "home_add", "a"),
        ]
        return f"{name}/", actions

    if is_managed:
        actions = [
            ActionItem("Re-add", "home_re_add", "a"),
            ActionItem("View diff", "managed_diff", "d", disabled=not has_diff),
            ActionItem("Edit local file", "home_edit_local", "e"),
            ActionItem("Edit chezmoi source", "home_edit_source"),
            ActionItem("Change attributes", "managed_chattr"),
            ActionItem("Ignore", "managed_ignore", "i"),
            ActionItem("Forget", "managed_forget", "x"),
            ActionItem("Destroy (delete both)", "managed_destroy"),
        ]
    else:
        actions = [ActionItem("Add to chezmoi", "home_add", "a")]

    actions.append(ActionItem("View file", "view", "v"))

    return name, actions


def build_managed_actions(node_data, has_diff: bool, is_expanded: bool = False) -> tuple[str, list[ActionItem]]:
    """Build action list for a managed tree selection."""
    from cheznav.widgets.managed_tree import ExternalRoot  # noqa: PLC0415

    if isinstance(node_data, ExternalRoot):
        ext = node_data
        if ext.diff_count > 0:
            actions = [ActionItem(f"Apply ({ext.diff_count} outdated)", "managed_apply", "a")]
        else:
            actions = [ActionItem("Apply", "managed_apply", "a")]
        return f"{ext.target_path}/ (external)", actions

    if isinstance(node_data, ManagedEntry):
        entry = node_data
        actions = [
            ActionItem("Apply", "managed_apply", "a"),
            ActionItem("View diff", "managed_diff", "d", disabled=not has_diff),
            ActionItem("Edit chezmoi source", "managed_edit", "e"),
            ActionItem("Edit local file", "managed_edit_local"),
            ActionItem("View file", "view", "v"),
        ]
        if entry.is_template:
            actions.append(ActionItem("Preview template", "preview_template"))
        actions.extend(
            [
                ActionItem("Change attributes", "managed_chattr"),
                ActionItem("Ignore", "managed_ignore", "i"),
                ActionItem("Forget", "managed_forget", "x"),
                ActionItem("Destroy (delete both)", "managed_destroy"),
            ]
        )
        return entry.target_relative, actions

    if isinstance(node_data, Path):
        # Metafile
        actions = [
            ActionItem("Edit", "managed_edit", "e"),
            ActionItem("View file", "view", "v"),
        ]
        if node_data.name.endswith(".tmpl"):
            actions.append(ActionItem("Preview template", "preview_template"))
        actions.append(ActionItem("Change attributes", "managed_chattr"))
        return node_data.name, actions

    if isinstance(node_data, str):
        # Directory node
        toggle_label = "Collapse" if is_expanded else "Expand"
        actions = [
            ActionItem(toggle_label, "managed_toggle", "space"),
            ActionItem("Ignore directory", "managed_ignore", "i"),
        ]
        dirname = node_data.rsplit("/", 1)[-1] if "/" in node_data else node_data
        return f"{dirname}/", actions

    return "Nothing selected", []
