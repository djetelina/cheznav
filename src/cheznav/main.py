import argparse
import asyncio
import json
import logging
import os
import subprocess
from collections.abc import Awaitable
from pathlib import Path
from typing import ClassVar, NamedTuple

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container
from textual.widgets import DirectoryTree, Footer, Tab, Tabs, Tree

from cheznav import THEME, chezmoi
from cheznav.chezmoi import ManagedEntry
from cheznav.utils import is_binary, is_binary_content
from cheznav.widgets import (
    ActionMenu,
    AddFlagsScreen,
    ChattrScreen,
    CommandPalette,
    ConfirmScreen,
    Header,
    HelpScreen,
    HomeTree,
    Legend,
    ManagedTree,
)
from cheznav.widgets.action_menu import build_home_actions, build_managed_actions

log = logging.getLogger(__name__)


class _RefreshData(NamedTuple):
    """Bundle of data fetched from chezmoi for tree updates."""

    entries: list[ManagedEntry]
    managed_entries: list[ManagedEntry]
    external_entries: dict[str, list[ManagedEntry]]
    ext_config: dict
    metas: list[Path]
    status_entries: list[tuple[str, str, str]]
    remote: str
    git_dirty: list[tuple[str, str]]
    git_ahead: int
    git_behind: int


class CheznavApp(App):
    CSS_PATH = "cheznav.tcss"
    TITLE = "cheznav"
    NOTIFICATION_TIMEOUT = 3
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "open_actions", "Context menu"),
        Binding("colon", "open_commands", "Commands"),
        Binding("left", "switch_pane_left", "← Pane", show=False),
        Binding("right", "switch_pane_right", "→ Pane", show=False),
        # Direct shortcuts (not shown in footer, learned from menu)
        Binding("v", "view", "", show=False),
        Binding("a", "shortcut_a", "", show=False),
        Binding("e", "shortcut_e", "", show=False),
        Binding("d", "shortcut_d", "", show=False),
        Binding("i", "shortcut_i", "", show=False),
        Binding("x", "shortcut_x", "", show=False),
        # Global
        Binding("question_mark", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, *, dry_run: bool = False, **kwargs) -> None:
        self.dry_run = dry_run
        self._refreshing = False
        if dry_run:
            chezmoi.set_dry_run(True)
        super().__init__(**kwargs)
        self.theme = THEME
        if dry_run:
            self.title = "cheznav [DRY RUN]"

    def compose(self) -> ComposeResult:
        yield Header(id="header")
        tabs = Tabs(
            Tab("Local", id="tab-home"),
            Tab("Chezmoi Managed", id="tab-managed"),
            id="pane-tabs",
        )
        tabs.can_focus = False
        yield tabs
        with Container(id="pane-container"):
            with Container(id="left-pane"):
                yield HomeTree(id="home-tree")
            with Container(id="right-pane"):
                yield ManagedTree(id="managed-tree")
        with Container(id="bottom-bar"):
            yield Legend()
            yield Footer()

    @staticmethod
    def _partition_entries(
        entries: list[ManagedEntry],
        ext_config: dict,
    ) -> tuple[list[ManagedEntry], dict[str, list[ManagedEntry]]]:
        managed_entries: list[ManagedEntry] = []
        external_entries: dict[str, list[ManagedEntry]] = {k: [] for k in ext_config}
        for entry in entries:
            for ext_root in ext_config:
                if entry.target_relative.startswith(ext_root):
                    external_entries[ext_root].append(entry)
                    break
            else:
                managed_entries.append(entry)
        return managed_entries, external_entries

    async def _update_trees(self, data: _RefreshData, *, restore_state: bool = False) -> None:
        managed_tree = self.query_one(ManagedTree)
        await managed_tree.load_entries(data.managed_entries, restore_state=restore_state)
        managed_tree.load_externals(data.external_entries, data.ext_config)
        git_dirty_source_paths = {src for _, src in data.git_dirty}
        managed_tree.load_metafiles(data.metas, git_dirty_source_paths=git_dirty_source_paths)

        home_tree = self.query_one(HomeTree)
        home_tree.managed_paths = {e.target_absolute for e in data.entries}
        home_tree.managed_entries = {e.target_absolute: e for e in data.entries}
        home_tree.diff_paths = {Path.home() / path for _, _, path in data.status_entries}

        # Map git dirty source-relative paths to target-relative paths
        source_to_target = {e.source_relative: e.target_relative for e in data.entries}
        git_dirty_target_paths = set()
        for _code, src_path in data.git_dirty:
            target = source_to_target.get(src_path)
            if target:
                git_dirty_target_paths.add(target)
        managed_tree.mark_diffs(
            {path for _, _, path in data.status_entries},
            git_dirty_paths=git_dirty_target_paths,
        )
        home_tree.git_dirty_paths = {Path.home() / t for t in git_dirty_target_paths}

        self.query_one(Header).update_info(
            data.remote,
            uncommitted=len(data.git_dirty),
            ahead=data.git_ahead,
            behind=data.git_behind,
        )

    async def _fetch_refresh_data(self) -> _RefreshData:
        entries, ext_config, metas, status_entries, remote, git_dirty, git_ab = await asyncio.gather(
            chezmoi.managed(),
            chezmoi.externals(),
            chezmoi.metafiles(),
            chezmoi.status(),
            chezmoi.git_remote_url(),
            chezmoi.git_status_porcelain(),
            chezmoi.git_ahead_behind(),
        )
        managed_entries, external_entries = self._partition_entries(entries, ext_config)
        return _RefreshData(
            entries=entries,
            managed_entries=managed_entries,
            external_entries=external_entries,
            ext_config=ext_config,
            metas=metas,
            status_entries=status_entries,
            remote=remote,
            git_dirty=git_dirty,
            git_ahead=git_ab[0],
            git_behind=git_ab[1],
        )

    async def on_ready(self) -> None:
        self._git_fetch_task = asyncio.create_task(self._fetch_and_refresh_ahead_behind())
        data = await self._fetch_refresh_data()
        await self._update_trees(data)

        managed_tree = self.query_one(ManagedTree)
        if managed_tree.root.children:
            managed_tree.cursor_line = 0

        home_tree = self.query_one(HomeTree)
        home_tree.focus()
        if home_tree.root.children:
            home_tree.cursor_line = 0

    def _sync_tab_to_focus(self) -> None:
        from textual.css.query import NoMatches  # noqa: PLC0415

        try:
            tabs = self.query_one(Tabs)
        except NoMatches:
            return
        if self.query_one(HomeTree).has_focus:
            tabs.active = "tab-home"
        elif self.query_one(ManagedTree).has_focus:
            tabs.active = "tab-managed"

    def on_descendant_focus(self, event: object) -> None:
        self._sync_tab_to_focus()

    @on(Tabs.TabActivated)
    def on_tab_activated(self, event: Tabs.TabActivated) -> None:
        if event.tab.id == "tab-home":
            self.query_one(HomeTree).focus()
        elif event.tab.id == "tab-managed":
            self.query_one(ManagedTree).focus()

    def _home_focused(self) -> bool:
        return self.query_one(HomeTree).has_focus

    def _managed_focused(self) -> bool:
        return self.query_one(ManagedTree).has_focus

    def _home_managed_file_selected(self) -> bool:
        path = self._get_home_selected_path()
        return path is not None and path in self.query_one(HomeTree).managed_paths

    def action_switch_pane_left(self) -> None:
        if self.query_one(ManagedTree).has_focus:
            self.query_one(HomeTree).focus()
            self.refresh_bindings()

    def action_switch_pane_right(self) -> None:
        if self.query_one(HomeTree).has_focus:
            self.query_one(ManagedTree).focus()
            self.refresh_bindings()

    def action_open_actions(self) -> None:
        if self._home_focused():
            home = self.query_one(HomeTree)
            node = home.cursor_node
            path = node.data.path if node and node.data else None
            is_dir = path is not None and path.is_dir()
            is_expanded = node.is_expanded if node else False
            is_managed = path is not None and not is_dir and path in home.managed_paths
            has_diff = path is not None and path in home.diff_paths
            title, actions = build_home_actions(path, is_managed, has_diff, is_dir=is_dir, is_expanded=is_expanded)
        elif self._managed_focused():
            managed = self.query_one(ManagedTree)
            node = managed.cursor_node
            node_data = node.data if node else None
            is_expanded = node.is_expanded if node else False
            has_diff = False
            if isinstance(node_data, ManagedEntry):
                has_diff = node_data.target_relative in managed.diff_paths
            title, actions = build_managed_actions(node_data, has_diff, is_expanded=is_expanded)
        else:
            return

        if not actions:
            self.notify("No actions available", severity="warning")
            return

        async def on_action(action: str | None) -> None:
            if action:
                await self.run_action(action)

        self.push_screen(ActionMenu(title, actions), on_action)

    def action_open_commands(self) -> None:
        async def on_command(action: str | None) -> None:
            if action:
                await self.run_action(action)

        self.push_screen(CommandPalette(), on_command)

    # --- Direct keyboard shortcuts (context-aware, no menu needed) ---

    async def action_shortcut_a(self) -> None:
        if self._home_focused():
            path = self._get_home_cursor_path()
            if path and path.is_file() and self._home_managed_file_selected():
                await self.run_action("home_re_add")
            else:
                await self.run_action("home_add")
        elif self._managed_focused():
            await self.run_action("managed_apply")

    async def action_shortcut_e(self) -> None:
        if self._home_focused():
            if self._home_managed_file_selected():
                await self.run_action("home_edit_local")
        elif self._managed_focused():
            await self.run_action("managed_edit")

    async def action_shortcut_d(self) -> None:
        entry = self._resolve_entry()
        if entry is None:
            return
        if self._managed_focused():
            if entry.target_relative in self.query_one(ManagedTree).diff_paths:
                await self.run_action("managed_diff")
        elif self._home_managed_file_selected():
            await self.run_action("managed_diff")

    async def action_shortcut_i(self) -> None:
        if self._managed_focused() or self._home_managed_file_selected():
            await self.run_action("managed_ignore")

    async def action_shortcut_x(self) -> None:
        if self._managed_focused() or self._home_managed_file_selected():
            await self.run_action("managed_forget")

    async def action_cmd_update(self) -> None:
        self.notify("Updating (pull + apply)...")
        _, stderr, rc = await chezmoi.update()
        if rc != 0:
            self.notify(f"Update failed: {stderr.strip()}", severity="error")
        else:
            self.notify("Update complete", severity="information")
            await self._refresh_managed()

    async def action_cmd_init(self) -> None:
        self.notify("Running chezmoi init...")
        _, stderr, rc = await chezmoi.init()
        if rc != 0:
            self.notify(f"Init failed: {stderr.strip()}", severity="error")
        else:
            self.notify("Init complete", severity="information")
            await self._refresh_managed()

    async def action_cmd_data(self) -> None:
        content = await chezmoi.data()
        if not content.strip():
            self.notify("No template data", severity="warning")
            return
        try:
            parsed = json.loads(content)
            content = json.dumps(parsed, indent=2)
        except json.JSONDecodeError:
            pass
        self._show_content(content)

    async def action_cmd_dump_config(self) -> None:
        stdout, stderr, rc = await chezmoi.dump_config()
        content = stdout if rc == 0 else stderr
        if not content.strip():
            self.notify("No config data", severity="warning")
            return
        self._show_content(content)

    async def action_preview_template(self) -> None:
        """Preview a template file rendered with current machine data."""
        source_path = None

        entry = self._get_managed_selected_entry()
        if entry and entry.is_template:
            source_path = str(entry.source_absolute)
        else:
            # Check for metafile
            managed = self.query_one(ManagedTree)
            node = managed.cursor_node
            if node and isinstance(node.data, Path) and node.data.name.endswith(".tmpl"):
                source_path = str(node.data)

        if source_path is None:
            self.notify("Select a template file", severity="warning")
            return
        try:
            content = await chezmoi.execute_template(source_path)
        except chezmoi.ChezmoiError as exc:
            self.notify(f"Template error: {exc}", severity="error")
            return
        if not content.strip():
            self.notify("Template produced empty output", severity="warning")
            return
        self._show_content(content)

    async def action_cmd_doctor(self) -> None:
        stdout, stderr, _rc = await chezmoi.doctor()
        content = (stdout + stderr).strip()
        if not content:
            self.notify("No output from doctor", severity="warning")
            return
        self._show_content(content)

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    async def _fetch_and_refresh_ahead_behind(self) -> None:
        """Run git fetch, then refresh to pick up accurate ahead/behind counts."""
        await chezmoi.git_fetch()
        await self._refresh_managed()

    async def _refresh_managed(self) -> None:
        data = await self._fetch_refresh_data()

        # Suppress event handlers during rebuild
        self._refreshing = True

        managed_tree = self.query_one(ManagedTree)
        saved_cursor = managed_tree.cursor_line
        had_focus = managed_tree.has_focus

        await self._update_trees(data, restore_state=True)

        # Restore cursor and focus
        if managed_tree.last_line >= 0:
            managed_tree.cursor_line = min(saved_cursor, managed_tree.last_line)
        if had_focus:
            managed_tree.focus()

        self._refreshing = False
        self.refresh_bindings()

    # --- Home tree: file selected updates status ---

    @on(DirectoryTree.FileSelected)
    def on_home_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        if not self._refreshing:
            self.refresh_bindings()

    @on(Tree.NodeHighlighted, "#home-tree")
    def on_home_highlighted(self, event: Tree.NodeHighlighted) -> None:
        if self._refreshing:
            return
        self.refresh_bindings()
        # Mirror highlight in managed tree
        managed_tree = self.query_one(ManagedTree)
        path = self._get_home_selected_path()
        if path and path in self.query_one(HomeTree).managed_paths:
            managed_tree.set_mirror(path)
        else:
            managed_tree.set_mirror(None)

    @on(Tree.NodeHighlighted, "#managed-tree")
    async def on_managed_highlighted(self, event: Tree.NodeHighlighted) -> None:
        if self._refreshing:
            return
        self.refresh_bindings()
        # Mirror highlight in home tree
        home_tree = self.query_one(HomeTree)
        entry = self._get_managed_selected_entry()
        if entry:
            await home_tree.set_mirror(entry.target_absolute)
        else:
            await home_tree.set_mirror(None)

    # --- Helpers to get selected items ---

    def _get_home_selected_path(self) -> Path | None:
        home = self.query_one(HomeTree)
        if home.cursor_node and home.cursor_node.data:
            path = home.cursor_node.data.path
            if path.is_file():
                return path
        return None

    def _get_home_cursor_path(self) -> Path | None:
        """Get the path of the cursor node, whether file or directory."""
        home = self.query_one(HomeTree)
        if home.cursor_node and home.cursor_node.data:
            return home.cursor_node.data.path
        return None

    def _get_managed_selected_entry(self) -> ManagedEntry | None:
        managed = self.query_one(ManagedTree)
        if managed.cursor_node and isinstance(managed.cursor_node.data, ManagedEntry):
            return managed.cursor_node.data
        return None

    def _resolve_entry(self) -> ManagedEntry | None:
        """Get the selected ManagedEntry, checking managed tree first then home tree."""
        entry = self._get_managed_selected_entry()
        if entry is None and self._home_focused():
            path = self._get_home_selected_path()
            if path:
                entry = self.query_one(HomeTree).managed_entries.get(path)
        return entry

    # --- Action handlers ---

    async def action_view(self) -> None:
        if self._home_focused():
            await self._view_home_file()
        elif self._managed_focused():
            await self._view_managed_file()

    def _show_file(self, path: Path) -> None:
        """Open a file in $PAGER (falls back to 'less')."""
        pager = os.environ.get("PAGER", "less")
        with self.suspend():
            subprocess.run(f"{pager} {path}", shell=True, check=False)

    def _show_content(self, content: str) -> None:
        """Pipe content into $PAGER (falls back to 'less')."""
        pager = os.environ.get("PAGER", "less")
        with self.suspend():
            proc = subprocess.Popen(pager, shell=True, stdin=subprocess.PIPE)
            proc.communicate(input=content.encode())

    async def _view_home_file(self) -> None:
        path = self._get_home_selected_path()
        if path is None:
            return
        if is_binary(path.name) or await asyncio.to_thread(is_binary_content, path):
            self.notify("Cannot view binary file", severity="warning")
            return
        self._show_file(path)

    async def _view_managed_file(self) -> None:
        managed = self.query_one(ManagedTree)
        node = managed.cursor_node
        if node and isinstance(node.data, Path):
            self._show_file(node.data)
            return
        entry = self._get_managed_selected_entry()
        if entry is None:
            return
        if entry.is_template:
            self._show_file(entry.source_absolute)
        else:
            try:
                content = await chezmoi.cat(str(entry.target_absolute))
            except chezmoi.ChezmoiError as exc:
                self.notify(f"Cannot read file: {exc}", severity="error")
                return
            if not content.strip():
                self.notify("No content (file may be encrypted or empty)", severity="warning")
                return
            self._show_content(content)

    # --- Home pane actions ---

    def action_home_add(self) -> None:
        path = self._get_home_cursor_path()
        if path is None:
            self.notify("Select a file or directory first", severity="warning")
            return
        is_dir = path.is_dir()

        def on_flags(flags: dict[str, bool] | None) -> None:
            if flags is None:
                return
            target = str(path)
            flag_parts = [f"--{k}" for k, v in flags.items() if v]
            parts = ["chezmoi", "add", *flag_parts, target]
            cmd = " ".join(parts)

            def on_confirm(confirmed: bool | None) -> None:
                if confirmed:
                    self._run_and_refresh(chezmoi.add(target, **flags))

            self.push_screen(ConfirmScreen("Add", cmd), on_confirm)

        self.push_screen(AddFlagsScreen(f"Add {path.name}", is_dir=is_dir), on_flags)

    # --- Managed pane actions ---

    async def action_managed_apply(self) -> None:
        from cheznav.widgets.managed_tree import ExternalRoot  # noqa: PLC0415

        managed = self.query_one(ManagedTree)
        node = managed.cursor_node

        # External root — apply the whole directory
        if node and isinstance(node.data, ExternalRoot):
            ext = node.data
            target = str(Path.home() / ext.target_path)
            cmd = f"chezmoi apply --force {target}"

            def on_ext_confirm(confirmed: bool | None) -> None:
                if confirmed:
                    self._run_and_refresh(chezmoi.apply(target))

            self.push_screen(ConfirmScreen(f"Apply external ({ext.diff_count} outdated)", cmd), on_ext_confirm)
            return

        entry = self._get_managed_selected_entry()
        if entry is None:
            self.notify("Select a managed file first", severity="warning")
            return
        target = str(entry.target_absolute)
        cmd = f"chezmoi apply --force {target}"

        def on_confirm(confirmed: bool | None) -> None:
            if confirmed:
                self._run_and_refresh(chezmoi.apply(target))

        self.push_screen(ConfirmScreen("Apply file", cmd), on_confirm)

    def action_managed_edit(self) -> None:
        managed = self.query_one(ManagedTree)
        node = managed.cursor_node
        if node and isinstance(node.data, Path):
            self._run_edit_path(node.data)
            return
        entry = self._get_managed_selected_entry()
        if entry is None:
            self.notify("Select a managed file first", severity="warning")
            return
        self._run_edit_path(entry.source_absolute)

    def action_managed_edit_local(self) -> None:
        entry = self._get_managed_selected_entry()
        if entry is None:
            self.notify("Select a managed file first", severity="warning")
            return
        self._run_edit_path(entry.target_absolute)

    def action_managed_diff(self) -> None:
        entry = self._resolve_entry()
        if entry is None:
            self.notify("Select a managed file first", severity="warning")
            return
        with self.suspend():
            subprocess.run(["chezmoi", "diff", str(entry.target_absolute)], check=False)

    async def action_home_re_add(self) -> None:
        path = self._get_home_selected_path()
        if path is None:
            self.notify("Select a managed file first", severity="warning")
            return
        target = str(path)
        cmd = f"chezmoi re-add {target}"

        def on_confirm(confirmed: bool | None) -> None:
            if confirmed:
                self._run_and_refresh(chezmoi.re_add(target))

        self.push_screen(ConfirmScreen("Re-add file", cmd), on_confirm)

    def action_home_edit_source(self) -> None:
        path = self._get_home_selected_path()
        if path is None:
            return
        entry = self.query_one(HomeTree).managed_entries.get(path)
        if entry is None:
            self.notify("Not a managed file", severity="warning")
            return
        self._run_edit_path(entry.source_absolute)

    def action_home_edit_local(self) -> None:
        path = self._get_home_selected_path()
        if path is None:
            return
        self._run_edit_path(path)

    async def action_managed_forget(self) -> None:
        entry = self._resolve_entry()
        if entry is None:
            self.notify("Select a managed file first", severity="warning")
            return
        target = str(entry.target_absolute)
        cmd = f"chezmoi forget {target}"

        def on_confirm(confirmed: bool | None) -> None:
            if confirmed:
                self._run_and_refresh(chezmoi.forget(target))

        self.push_screen(ConfirmScreen("Forget file", cmd), on_confirm)

    async def action_managed_destroy(self) -> None:
        entry = self._resolve_entry()
        if entry is None:
            self.notify("Select a managed file first", severity="warning")
            return
        target = str(entry.target_absolute)
        cmd = f"chezmoi destroy --force {target}"

        def on_confirm(confirmed: bool | None) -> None:
            if confirmed:
                self._run_and_refresh(chezmoi.destroy(target))

        self.push_screen(ConfirmScreen("⚠ Destroy (deletes source AND target)", cmd), on_confirm)

    async def action_managed_ignore(self) -> None:
        entry = self._resolve_entry()

        if entry:
            pattern = entry.target_relative
        elif self._managed_focused():
            managed = self.query_one(ManagedTree)
            node = managed.cursor_node
            if node and isinstance(node.data, str):
                pattern = node.data + "/**"
            else:
                self.notify("Select a file or directory", severity="warning")
                return
        else:
            self.notify("Select a managed file first", severity="warning")
            return

        cmd = f"echo '{pattern}' >> .chezmoiignore"

        def on_confirm(confirmed: bool | None) -> None:
            if confirmed:
                self._run_ignore_and_refresh(pattern)

        self.push_screen(ConfirmScreen("Ignore pattern", cmd), on_confirm)

    def action_managed_chattr(self) -> None:
        entry = self._resolve_entry()
        metafile = None
        if entry is None and self._managed_focused():
            managed = self.query_one(ManagedTree)
            node = managed.cursor_node
            if node and isinstance(node.data, Path):
                metafile = node.data

        if entry is None and metafile is None:
            self.notify("Select a managed file first", severity="warning")
            return

        if entry:
            current = {
                "encrypted": entry.is_encrypted,
                "executable": entry.is_executable,
                "private": entry.is_private,
                "template": entry.is_template,
            }
            target = str(entry.target_absolute)
            title = f"Attributes: {entry.target_relative}"
            is_script = False
        else:
            name = metafile.name
            is_script = name.startswith("run_")
            current = {
                "encrypted": "encrypted_" in name,
                "executable": is_script or "executable_" in name,
                "private": "private_" in name,
                "template": name.endswith(".tmpl"),
                "exact": "exact_" in name,
                "empty": "empty_" in name,
                "readonly": "readonly_" in name,
            }
            if is_script:
                current["once"] = "once_" in name
                current["onchange"] = "onchange_" in name
                current["before"] = "before_" in name
                current["after"] = "after_" in name
            target = str(metafile)
            title = f"Attributes: {name}"

        def on_chattr(changes: dict[str, bool] | None) -> None:
            if not changes:
                return
            modifier = ",".join(f"+{attr}" if enabled else f"no{attr}" for attr, enabled in changes.items())
            cmd = f"chezmoi chattr {modifier} {target}"

            def on_confirm(confirmed: bool | None) -> None:
                if confirmed:
                    self._run_and_refresh(chezmoi.chattr(target, changes))

            self.push_screen(ConfirmScreen("Change attributes", cmd), on_confirm)

        self.push_screen(
            ChattrScreen(title, current, is_script=is_script),
            on_chattr,
        )

    def action_home_toggle(self) -> None:
        home = self.query_one(HomeTree)
        if home.cursor_node:
            home.cursor_node.toggle()

    def action_managed_toggle(self) -> None:
        managed = self.query_one(ManagedTree)
        if managed.cursor_node:
            managed.cursor_node.toggle()

    @work
    async def _run_ignore_and_refresh(self, pattern: str) -> None:
        try:
            await chezmoi.add_ignore(pattern)
        except (chezmoi.ChezmoiError, OSError) as exc:
            self.notify(f"Failed to add ignore pattern: {exc}", severity="error")
            return
        self.notify(f"Added '{pattern}' to .chezmoiignore")
        await self._refresh_managed()

    # --- Workers ---

    def _run_edit_path(self, path: Path) -> None:
        """Suspend the TUI and open a file in $EDITOR (defaults to vi)."""
        editor = os.environ.get("EDITOR", "vi")
        try:
            with self.suspend():
                subprocess.run([editor, str(path)], check=False)
            self.run_worker(self._refresh_managed())
        except FileNotFoundError:
            self.notify(f"Editor not found: {editor}", severity="error")

    @work
    async def _run_and_refresh(self, coro: Awaitable[tuple[str, str, int]]) -> None:
        try:
            stdout, stderr, rc = await coro
        except Exception as exc:
            self.notify(f"Command failed: {exc}", severity="error")
            return
        output = (stdout + stderr).strip()
        if output:
            self.notify(output, timeout=15, severity="error" if rc != 0 else "information")
        elif rc != 0:
            self.notify("Command failed", severity="error")
        await self._refresh_managed()
        self.refresh_bindings()


def main() -> None:
    parser = argparse.ArgumentParser(description="TUI for chezmoi")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Dry-run mode (no mutations)")
    args = parser.parse_args()
    CheznavApp(dry_run=args.dry_run).run()


if __name__ == "__main__":
    main()
