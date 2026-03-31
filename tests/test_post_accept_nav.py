"""Regression tests: ensure arrow key navigation works correctly after accepting changes in diff view."""

from pathlib import Path

from cheznav.main import CheznavApp
from cheznav.widgets import ManagedTree
from cheznav.widgets.diff import DiffScroll, DiffView
from tests.conftest import make_entry, patch_chezmoi, settle

ENTRIES = [make_entry(f".file{i}", base=str(Path.home())) for i in range(200)]


async def _mock_managed():
    return ENTRIES


async def _mock_status():
    return [(" ", "M", ".file0")]


def _patch():
    return patch_chezmoi(
        managed=_mock_managed,
        status=_mock_status,
    )


async def test_single_down_moves_one_line():
    """Basic: each down press should move cursor by exactly 1."""
    with _patch():
        app = CheznavApp(dry_run=True)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            # Switch to managed pane
            await pilot.press("tab")
            await pilot.pause()

            tree = app.query_one(ManagedTree)
            start = tree.cursor_line

            await pilot.press("down")
            await pilot.pause()
            assert tree.cursor_line == start + 1, f"Expected {start + 1}, got {tree.cursor_line}"

            await pilot.press("down")
            await pilot.pause()
            assert tree.cursor_line == start + 2, f"Expected {start + 2}, got {tree.cursor_line}"


async def test_nav_after_diff_close():
    """After opening and closing diff (no accept), navigation should work."""
    with _patch():
        app = CheznavApp(dry_run=True)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            await pilot.press("tab")
            await pilot.pause()

            tree = app.query_one(ManagedTree)

            # Open diff via action directly (menu-driven UX)
            await app.run_action("managed_diff")
            await pilot.pause()

            assert app._diff_active is True

            # Close without accepting
            await pilot.press("escape")
            await pilot.pause()

            assert app._diff_active is False

            start = tree.cursor_line
            await pilot.press("down")
            await pilot.pause()
            assert tree.cursor_line == start + 1

            await pilot.press("down")
            await pilot.pause()
            assert tree.cursor_line == start + 2


async def test_nav_after_diff_accept_right():
    """After accepting right in diff, navigation should still work."""
    with _patch():
        app = CheznavApp(dry_run=True)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            await pilot.press("tab")
            await pilot.pause()

            tree = app.query_one(ManagedTree)

            await app.run_action("managed_diff")
            await pilot.pause()
            assert app._diff_active is True

            await app.run_action("diff_accept_right")
            await pilot.pause()

            # Confirm
            await pilot.press("y")
            await settle(pilot)

            assert app._diff_active is False, "Diff should be closed after accept"
            assert len(app.query("#diff-view")) == 0, "No diff view should remain"

            start = tree.cursor_line
            await pilot.press("down")
            await pilot.pause()
            assert tree.cursor_line == start + 1

            await pilot.press("down")
            await pilot.pause()
            assert tree.cursor_line == start + 2


async def test_diff_reopens_after_accept():
    """After accepting in diff, should be able to open diff again."""
    with _patch():
        app = CheznavApp(dry_run=True)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            await pilot.press("tab")
            await pilot.pause()

            await app.run_action("managed_diff")
            await pilot.pause()
            assert app._diff_active is True

            await app.run_action("diff_accept_right")
            await pilot.pause()
            await pilot.press("y")
            await settle(pilot)

            assert app._diff_active is False

            await app.run_action("managed_diff")
            await pilot.pause()
            assert app._diff_active is True, "Should be able to reopen diff after accept"

            await pilot.press("escape")
            await pilot.pause()
            assert app._diff_active is False


async def test_nav_during_refresh():
    """Navigate immediately after accept, while refresh worker may be running."""
    with _patch():
        app = CheznavApp(dry_run=True)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            await pilot.press("tab")
            await pilot.pause()

            tree = app.query_one(ManagedTree)

            await app.run_action("managed_diff")
            await pilot.pause()
            await app.run_action("diff_accept_right")
            await pilot.pause()
            await pilot.press("y")
            await pilot.pause()

            # Navigate while refresh might be running
            for _i in range(5):
                await pilot.press("down")
                await pilot.pause()

            # Wait for everything to settle
            await settle(pilot, 8)

            # Now navigate again — each press should move exactly 1
            pos = tree.cursor_line
            await pilot.press("down")
            await pilot.pause()
            assert tree.cursor_line == pos + 1

            await pilot.press("up")
            await pilot.pause()
            assert tree.cursor_line == pos


async def test_no_ghost_widgets_after_accept():
    """After accept, there should be no DiffScroll or DiffView widgets in DOM."""
    with _patch():
        app = CheznavApp(dry_run=True)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            await pilot.press("tab")
            await pilot.pause()

            await app.run_action("managed_diff")
            await pilot.pause()

            await app.run_action("diff_accept_right")
            await pilot.pause()
            await pilot.press("y")
            await settle(pilot)

            assert len(app.query(DiffView)) == 0, "No DiffView should remain"
            assert len(app.query(DiffScroll)) == 0, "No DiffScroll should remain"
            assert len(app.query(ManagedTree)) == 1, "Exactly one ManagedTree"
