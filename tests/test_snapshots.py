"""Snapshot tests for cheznav UI."""

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from cheznav.main import CheznavApp
from tests.conftest import make_entry

SNAPSHOT_HOME = Path("/tmp/cheznav-snapshot-home")


@pytest.fixture
def mock_home():
    """Create a fake home directory at a fixed path for deterministic snapshots."""
    home = SNAPSHOT_HOME
    if home.exists():
        shutil.rmtree(home)
    home.mkdir(parents=True)
    # Managed files
    (home / ".bashrc").write_text("# .bashrc\nexport PATH=$HOME/bin:$PATH\nalias ll='ls -la'\n")
    (home / ".vimrc").write_text("set nocompatible\nset number\nset relativenumber\n")
    (home / ".zshrc").write_text("# .zshrc\nsource ~/.bashrc\nautoload -Uz compinit\n")
    (home / ".gitconfig").write_text("[user]\n  name = Test User\n  email = test@example.com\n")
    (home / ".config" / "nvim").mkdir(parents=True)
    (home / ".config" / "nvim" / "init.lua").write_text("vim.opt.number = true\nvim.opt.shiftwidth = 4\n")
    # Unmanaged files
    (home / ".profile").write_text("# .profile\nexport EDITOR=vim\n")
    (home / ".local" / "bin").mkdir(parents=True)
    (home / ".local" / "bin" / "myscript").touch()
    (home / "Documents").mkdir()
    (home / "Documents" / "notes.md").touch()
    (home / "Downloads").mkdir()
    yield home
    shutil.rmtree(home, ignore_errors=True)


def _make_entries(home: Path):
    base = str(home)
    return [
        make_entry(".bashrc", base=base),
        make_entry(".vimrc", base=base),
        make_entry(".zshrc", base=base),
        make_entry(".gitconfig", base=base),
        make_entry(
            ".config/nvim/init.lua",
            base=base,
            source_relative="dot_config/nvim/init.lua.tmpl",
            is_template=True,
        ),
    ]


STATUS_ENTRIES = [(" ", "M", ".bashrc"), (" ", "M", ".config/nvim/init.lua")]


def _patch_all(home: Path):
    entries = _make_entries(home)

    async def mock_managed():
        return entries

    async def mock_status():
        return STATUS_ENTRIES

    async def mock_cat(target):
        return "# managed content\nline 2\nline 3\n"

    async def mock_metafiles():
        return []

    async def mock_source_path():
        return Path("/source")

    async def mock_git_remote_url():
        return "djetelina/dotfiles"

    async def mock_externals():
        return {}

    return patch.multiple(
        "cheznav.chezmoi",
        managed=mock_managed,
        status=mock_status,
        cat=mock_cat,
        metafiles=mock_metafiles,
        source_path=mock_source_path,
        git_remote_url=mock_git_remote_url,
        externals=mock_externals,
    )


def _ctx(home: Path):
    """Combined context manager for all patches."""

    class _Ctx:
        def __enter__(self):
            self._p1 = _patch_all(home)
            self._p2 = patch("cheznav.widgets.home_tree.Path.home", return_value=home)
            self._p1.__enter__()
            self._p2.__enter__()
            return self

        def __exit__(self, *args):
            self._p2.__exit__(*args)
            self._p1.__exit__(*args)

    return _Ctx()


def test_main_view(snap_compare, mock_home):
    with _ctx(mock_home):
        assert snap_compare(CheznavApp(dry_run=True), terminal_size=(120, 40))


def test_managed_pane(snap_compare, mock_home):
    with _ctx(mock_home):
        assert snap_compare(CheznavApp(dry_run=True), terminal_size=(120, 40), press=["right"])


def test_context_menu_home(snap_compare, mock_home):
    with _ctx(mock_home):
        assert snap_compare(CheznavApp(dry_run=True), terminal_size=(120, 40), press=["down", "enter"])


def test_context_menu_managed(snap_compare, mock_home):
    with _ctx(mock_home):
        assert snap_compare(CheznavApp(dry_run=True), terminal_size=(120, 40), press=["right", "enter"])


def test_command_palette(snap_compare, mock_home):
    with _ctx(mock_home):
        assert snap_compare(CheznavApp(dry_run=True), terminal_size=(120, 40), press=["colon"])


def test_help_screen(snap_compare, mock_home):
    with _ctx(mock_home):
        assert snap_compare(CheznavApp(dry_run=True), terminal_size=(120, 40), press=["question_mark"])


def test_add_flags(snap_compare, mock_home):
    with _ctx(mock_home):
        assert snap_compare(CheznavApp(dry_run=True), terminal_size=(120, 40), press=["down", "a"])


def test_view_home_shortcut(snap_compare, mock_home):
    """View a home file with 'v' shortcut."""
    with _ctx(mock_home):
        # .bashrc is 4 downs (past .config/, .local/, Documents/, Downloads/)
        assert snap_compare(
            CheznavApp(dry_run=True),
            terminal_size=(120, 40),
            press=["down", "down", "down", "down", "v"],
        )


def test_view_home_context_menu(snap_compare, mock_home):
    """View a home file via context menu."""
    with _ctx(mock_home):
        assert snap_compare(
            CheznavApp(dry_run=True),
            terminal_size=(120, 40),
            press=["down", "down", "down", "down", "enter", "v"],
        )


def test_view_managed_shortcut(snap_compare, mock_home):
    """View a managed file with 'v' shortcut."""
    with _ctx(mock_home):
        assert snap_compare(
            CheznavApp(dry_run=True),
            terminal_size=(120, 40),
            press=["right", "down", "v"],
        )


def test_view_managed_context_menu(snap_compare, mock_home):
    """View a managed file via context menu."""
    with _ctx(mock_home):
        assert snap_compare(
            CheznavApp(dry_run=True),
            terminal_size=(120, 40),
            press=["right", "down", "enter", "v"],
        )


def test_managed_expand_dir(snap_compare, mock_home):
    """Expand .config/ directory in managed pane."""
    with _ctx(mock_home):
        assert snap_compare(
            CheznavApp(dry_run=True),
            terminal_size=(120, 40),
            press=["right", "space"],
        )


def test_diff_shortcut(snap_compare, mock_home):
    """Open diff with 'd' shortcut on managed pane."""
    with _ctx(mock_home):
        # .bashrc has a diff — down once from .config/ dir
        assert snap_compare(
            CheznavApp(dry_run=True),
            terminal_size=(120, 40),
            press=["right", "down", "d"],
        )


def test_diff_context_menu(snap_compare, mock_home):
    """Open diff via context menu."""
    with _ctx(mock_home):
        assert snap_compare(
            CheznavApp(dry_run=True),
            terminal_size=(120, 40),
            press=["right", "down", "enter", "d"],
        )
