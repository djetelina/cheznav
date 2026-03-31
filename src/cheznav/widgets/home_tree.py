import asyncio
from collections.abc import Iterable
from pathlib import Path
from typing import ClassVar

from rich.style import Style
from rich.text import Text
from textual.binding import Binding, BindingType
from textual.widgets import DirectoryTree
from textual.widgets._tree import TreeNode

from cheznav.chezmoi import ManagedEntry


class HomeTree(DirectoryTree):
    ICON_FILE = ""
    ICON_FOLDER = ""
    ICON_FOLDER_OPEN = ""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "open_actions", "Context menu"),
        Binding("space", "toggle_node", "Toggle", show=False),
    ]

    async def action_open_actions(self) -> None:
        await self.app.run_action("open_actions")

    def action_toggle_node(self) -> None:
        if self.cursor_node:
            self.cursor_node.toggle()

    DEFAULT_CSS = """
    HomeTree {
        height: 100%;
    }
    """

    managed_paths: set[Path]
    managed_entries: dict[Path, ManagedEntry]
    diff_paths: set[Path]

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return sorted(
            paths,
            key=lambda p: (not p.is_dir(), p.name.lower()),
        )

    def _theme_color(self, name: str) -> str:
        theme = self.app.current_theme
        return getattr(theme, name, name) if theme else name

    def __init__(self, **kwargs) -> None:
        super().__init__(Path.home(), **kwargs)
        self.show_root = False
        self.managed_paths = set()
        self.managed_entries = {}
        self.diff_paths = set()
        self._auto_expanded: list = []

    @staticmethod
    def _find_child_by_name(node: TreeNode, name: str) -> TreeNode | None:
        for c in node.children:
            if c.data and hasattr(c.data, "path") and c.data.path.name == name:
                return c
        return None

    async def _expand_and_wait(self, node: TreeNode) -> None:
        if not node.is_expanded:
            node.expand()
            self._auto_expanded.append(node)
            for _ in range(50):
                await asyncio.sleep(0.05)
                if node.children:
                    break

    async def set_mirror(self, target_absolute: Path | None) -> None:
        """Move cursor to the node matching target_absolute, expanding parents as needed."""
        for node in reversed(self._auto_expanded):
            node.collapse()
        self._auto_expanded.clear()

        if target_absolute is None:
            return

        try:
            rel = target_absolute.relative_to(self.path)
        except ValueError:
            return

        current = self.root
        for part in rel.parts:
            child = self._find_child_by_name(current, part)

            if child is None:
                await self._expand_and_wait(current)
                child = self._find_child_by_name(current, part)

            if child is None:
                return

            if child.data and hasattr(child.data, "path") and child.data.path == target_absolute:
                self.select_node(child)
                return

            await self._expand_and_wait(child)
            current = child

    def render_label(self, node: TreeNode, base_style: Style, style: Style) -> Text:
        path = node.data.path if node.data else None

        if path and path.is_dir():
            label = Text()
            label.append(path.name, style=base_style + style + Style(color="cyan", bold=True))
            label.append("/", style=base_style + style + Style(color="cyan", dim=True))
            return label

        if path and path.is_file() and path in self.managed_paths:
            has_diff = path in self.diff_paths
            color = self._theme_color("warning") if has_diff else self._theme_color("success")
            label = Text()
            label.append(path.name, style=base_style + style + Style(color=color))
            entry = self.managed_entries.get(path)
            if entry and entry.indicator_str:
                label.append(f" {entry.indicator_str}")
            return label

        return super().render_label(node, base_style, style)
