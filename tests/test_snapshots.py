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


GIT_DIRTY_ENTRIES = [("M", "dot_.bashrc"), ("M", "dot_.zshrc")]


def _patch_all(home: Path, git_dirty=None, git_ahead_behind=(0, 0)):
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

    async def mock_git_fetch():
        return None

    async def mock_git_status_porcelain():
        return git_dirty if git_dirty is not None else []

    _git_ab = git_ahead_behind

    async def mock_git_ahead_behind():
        return _git_ab

    return patch.multiple(
        "cheznav.chezmoi",
        managed=mock_managed,
        status=mock_status,
        cat=mock_cat,
        metafiles=mock_metafiles,
        source_path=mock_source_path,
        git_remote_url=mock_git_remote_url,
        externals=mock_externals,
        git_fetch=mock_git_fetch,
        git_status_porcelain=mock_git_status_porcelain,
        git_ahead_behind=mock_git_ahead_behind,
    )


def _ctx(home: Path, **patch_kwargs):
    """Combined context manager for all patches."""

    class _Ctx:
        def __enter__(self):
            self._p1 = _patch_all(home, **patch_kwargs)
            self._p2 = patch("cheznav.widgets.home_tree.Path.home", return_value=home)
            # Disable syntax highlighting to avoid Pygments rendering differences across environments
            self._p3 = patch("cheznav.widgets.content._make_syntax", side_effect=lambda c, lang=None: c)
            self._p1.__enter__()
            self._p2.__enter__()
            self._p3.__enter__()
            return self

        def __exit__(self, *args):
            self._p3.__exit__(*args)
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


def test_git_dirty_indicators(snap_compare, mock_home):
    """Show 🔄 markers on files with uncommitted source changes."""
    with _ctx(mock_home, git_dirty=GIT_DIRTY_ENTRIES):
        assert snap_compare(CheznavApp(dry_run=True), terminal_size=(120, 40), press=["right"])


def test_git_uncommitted_header(snap_compare, mock_home):
    """Header shows uncommitted count."""
    with _ctx(mock_home, git_dirty=GIT_DIRTY_ENTRIES):
        assert snap_compare(CheznavApp(dry_run=True), terminal_size=(120, 40))


def test_git_ahead_behind_header(snap_compare, mock_home):
    """Header shows ahead/behind counts."""
    with _ctx(mock_home, git_ahead_behind=(3, 1)):
        assert snap_compare(CheznavApp(dry_run=True), terminal_size=(120, 40))
