from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar

from rich.text import Text
from textual.binding import Binding, BindingType
from textual.widgets import Tree

from cheznav.chezmoi import ManagedEntry


@dataclass
class ExternalRoot:
    """Data attached to external root nodes."""

    target_path: str  # e.g. ".oh-my-zsh"
    ext_type: str  # e.g. "archive"
    url: str
    file_count: int
    diff_count: int = 0


class ManagedTree(Tree):
    ICON_NODE = ""
    ICON_NODE_EXPANDED = ""

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
    ManagedTree {
        height: 100%;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("Managed", **kwargs)
        self.show_root = False
        self.guide_depth = 4
        self.show_guides = True
        self.diff_paths: set[str] = set()
        self._auto_expanded: list = []

    def _theme_color(self, name: str) -> str:
        theme = self.app.current_theme
        return getattr(theme, name, name) if theme else name

    def _get_expanded_paths(self, node=None) -> set[str]:
        """Collect path keys of all expanded directory nodes."""
        if node is None:
            node = self.root
        expanded = set()
        for child in node.children:
            if child.children and child.is_expanded and isinstance(child.data, str):
                expanded.add(child.data)
                expanded.update(self._get_expanded_paths(child))
        return expanded

    async def load_entries(self, entries: list[ManagedEntry], restore_state: bool = False) -> None:
        # Save state before clearing
        expanded_keys: set[str] = set()
        if restore_state:
            expanded_keys = self._get_expanded_paths()

        self.clear()
        self.root.expand()

        dir_children: dict[str, set[str]] = defaultdict(set)
        file_map: dict[str, list[ManagedEntry]] = defaultdict(list)

        for entry in entries:
            parts = PurePosixPath(entry.target_relative).parts
            for i in range(len(parts) - 1):
                parent = "/".join(parts[:i]) if i > 0 else ""
                dir_children[parent].add(parts[i])
                child_path = "/".join(parts[: i + 1])
                dir_children.setdefault(child_path, set())
            parent = "/".join(parts[:-1])
            file_map[parent].append(entry)

        nodes: dict = {}
        self._build_level(self.root, "", dir_children, file_map, nodes)

        # Restore expanded state
        if restore_state:
            for key, node in nodes.items():
                if key in expanded_keys:
                    node.expand()

    def mark_diffs(self, diff_paths: set[str]) -> None:
        """Update diff_paths and rebuild labels to show diff indicators."""
        self.diff_paths = diff_paths
        self._update_diff_labels(self.root)
        self._update_external_diff_counts(diff_paths)

    def _update_diff_labels(self, node) -> int:
        """Update labels and return count of diffs under this node."""
        total_diffs = 0
        for child in node.children:
            if isinstance(child.data, ManagedEntry):
                has_diff = child.data.target_relative in self.diff_paths
                child.set_label(
                    self._make_label(
                        PurePosixPath(child.data.target_relative).name,
                        child.data,
                        has_diff,
                    )
                )
                if has_diff:
                    total_diffs += 1
            elif isinstance(child.data, str) and child.children:
                # Directory node — recurse and update label with count
                child_diffs = self._update_diff_labels(child)
                total_diffs += child_diffs
                dirname = child.data.rsplit("/", 1)[-1] if "/" in child.data else child.data
                label = Text()
                label.append(dirname, style="bold cyan")
                label.append("/", style="dim cyan")
                if child_diffs > 0:
                    label.append(f" ({child_diffs})", style=f"bold {self._theme_color('warning')}")
                child.set_label(label)
            elif child.children:
                total_diffs += self._update_diff_labels(child)
        return total_diffs

    def _update_external_diff_counts(self, diff_paths: set[str]) -> None:
        """Update external node labels with diff counts."""

        def _find_externals(node):
            for child in node.children:
                if isinstance(child.data, ExternalRoot):
                    yield child
                elif child.children:
                    yield from _find_externals(child)

        for child in _find_externals(self.root):
            ext = child.data
            count = sum(1 for p in diff_paths if p.startswith(ext.target_path))
            ext.diff_count = count

            label = Text()
            if count > 0:
                warn = self._theme_color("warning")
                label.append(f"{ext.target_path}/", style=f"bold {warn}")
                label.append(f" ⟳ {count} outdated", style=f"bold {warn}")
            else:
                label.append(f"{ext.target_path}/", style="bold #8be9fd")
                label.append(f" ({ext.file_count} files)", style="dim")
            child.set_label(label)

    def load_externals(self, external_entries: dict[str, list[ManagedEntry]], ext_config: dict[str, dict]) -> None:
        """Add external entries under an 'externals' section header."""
        if not any(external_entries.values()):
            return

        section = self.root.add(Text("externals", style="bold magenta"), expand=False)

        for ext_path, entries in external_entries.items():
            if not entries:
                continue
            config = ext_config.get(ext_path, {})

            ext_data = ExternalRoot(
                target_path=ext_path,
                ext_type=config.get("type", "unknown"),
                url=config.get("url", ""),
                file_count=len(entries),
            )

            label = Text()
            label.append(f"{ext_path}/", style="bold #8be9fd")
            label.append(f" ({len(entries)} files)", style="dim")

            section.add_leaf(label, data=ext_data)

    def load_metafiles(self, metafiles: list[Path]) -> None:
        if not metafiles:
            return
        config_node = self.root.add(Text("chezmoi config", style="bold magenta"), expand=False)
        for item in metafiles:
            if item.is_file():
                config_node.add_leaf(Text(item.name), data=item)
            elif item.is_dir():
                dir_label = Text()
                dir_label.append(item.name, style="bold cyan")
                dir_label.append("/", style="dim cyan")
                dir_node = config_node.add(dir_label, expand=False)
                for child in sorted(item.rglob("*"), key=lambda p: p.name.lower()):
                    if child.is_file():
                        rel = child.relative_to(item)
                        dir_node.add_leaf(Text(str(rel)), data=child)

    def _build_level(self, parent_node, path_key, dir_children, file_map, nodes) -> None:
        subdirs = sorted(dir_children.get(path_key, set()), key=str.lower)
        for dirname in subdirs:
            child_key = f"{path_key}/{dirname}" if path_key else dirname
            label = Text()
            label.append(dirname, style="bold cyan")
            label.append("/", style="dim cyan")
            node = parent_node.add(label, data=child_key, expand=False)
            nodes[child_key] = node
            self._build_level(node, child_key, dir_children, file_map, nodes)

        files = sorted(file_map.get(path_key, []), key=lambda e: PurePosixPath(e.target_relative).name.lower())
        for entry in files:
            name = PurePosixPath(entry.target_relative).name
            has_diff = entry.target_relative in self.diff_paths
            label = self._make_label(name, entry, has_diff)
            parent_node.add_leaf(label, data=entry)

    def set_mirror(self, target_absolute: Path | None) -> None:
        """Move cursor to the node matching target_absolute, expanding parents as needed."""
        # Collapse previously auto-expanded nodes
        for node in reversed(self._auto_expanded):
            node.collapse()
        self._auto_expanded.clear()

        if target_absolute is None:
            return

        # Find matching node
        def _find(n):
            for child in n.children:
                if isinstance(child.data, ManagedEntry) and child.data.target_absolute == target_absolute:
                    return child
                if child.children:
                    result = _find(child)
                    if result:
                        return result
            return None

        node = _find(self.root)
        if node is None:
            return

        # Auto-expand collapsed parents
        parent = node.parent
        while parent and parent is not self.root:
            if not parent.is_expanded:
                parent.expand()
                self._auto_expanded.append(parent)
            parent = parent.parent

        self.select_node(node)

    def _make_label(self, name: str, entry: ManagedEntry, has_diff: bool = False) -> Text:
        label = Text()
        if has_diff:
            label.append(name, style=self._theme_color("warning"))
        else:
            label.append(name)
        if entry.indicator_str:
            label.append(f" {entry.indicator_str}")
        return label
