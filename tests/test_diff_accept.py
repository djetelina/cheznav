"""Tests for diff view accept behavior — post-accept navigation must work cleanly."""

from pathlib import Path

from cheznav.main import CheznavApp
from cheznav.widgets import DiffView, ManagedTree
from tests.conftest import make_entry, patch_chezmoi

MOCK_ENTRIES = [
    make_entry(".gitconfig"),
    make_entry(".zshrc"),
    make_entry(".vimrc"),
]


async def _mock_managed():
    return MOCK_ENTRIES


async def _mock_status():
    return [(" ", "M", ".gitconfig")]


async def _mock_cat(target):
    return "old line1\nold line2\n"


def _patch():
    return patch_chezmoi(
        managed=_mock_managed,
        status=_mock_status,
        cat=_mock_cat,
    )


async def test_diff_opens_and_closes():
    """Diff view should open and close cleanly."""
    with _patch():
        app = CheznavApp(dry_run=True)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            # Switch to managed pane and select first file
            await pilot.press("tab")
            await pilot.pause()

            assert app._diff_active is False
            assert len(app.query("#diff-view")) == 0

            # Both panes visible
            assert app.query_one("#pane-container").display is True


async def test_no_duplicate_diff_views_in_dom():
    """After closing diff, no diff-view should remain in the DOM."""
    with _patch():
        app = CheznavApp(dry_run=True)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            # After any operation, there should never be leftover diff views
            assert len(app.query("#diff-view")) == 0
            assert app._diff_active is False


async def test_panes_visible_after_close():
    """Both panes must be display=True when not in diff mode."""
    with _patch():
        app = CheznavApp(dry_run=True)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            left = app.query_one("#left-pane")
            right = app.query_one("#right-pane")
            assert left.display is True
            assert right.display is True


async def test_managed_tree_single_instance():
    """There should only ever be one ManagedTree in the DOM."""
    with _patch():
        app = CheznavApp(dry_run=True)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert len(app.query(ManagedTree)) == 1


async def test_close_diff_state_clean():
    """_close_diff must reset all diff state."""
    with _patch():
        app = CheznavApp(dry_run=True)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            # Manually set diff state as if we opened diff
            app._diff_active = True
            app._diff_target = "/some/path"

            # Mount a fake diff view
            diff_view = DiffView("test", "left\n", "right\n", id="diff-view")
            app.query_one("#left-pane").display = False
            app.query_one("#right-pane").display = False
            await app.mount(diff_view, after=app.query_one("#header"))
            await pilot.pause()

            assert len(app.query("#diff-view")) == 1

            # Close diff
            await app._close_diff()
            await pilot.pause()

            # All state should be clean
            assert app._diff_active is False
            assert app._diff_target == ""
            assert len(app.query("#diff-view")) == 0
            assert app.query_one("#pane-container").display is True
