"""Tests for confirm screen widgets."""

from textual.app import App, ComposeResult

from cheznav.widgets.confirm import AddFlagsScreen, ChattrScreen, ConfirmScreen


class ConfirmApp(App):
    def compose(self) -> ComposeResult:
        yield from ()


async def test_confirm_screen_confirm():
    app = ConfirmApp()
    async with app.run_test() as pilot:
        results = []
        app.push_screen(ConfirmScreen("Test", "chezmoi add .bashrc"), results.append)
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()
        assert results == [True]


async def test_confirm_screen_cancel():
    app = ConfirmApp()
    async with app.run_test() as pilot:
        results = []
        app.push_screen(ConfirmScreen("Test", "chezmoi add .bashrc"), results.append)
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert results == [False]


async def test_add_flags_default_no_flags():
    app = ConfirmApp()
    async with app.run_test() as pilot:
        results = []
        app.push_screen(AddFlagsScreen("Add file"), results.append)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert len(results) == 1
        flags = results[0]
        assert isinstance(flags, dict)
        # No flags selected by default
        assert not any(flags.values())


async def test_add_flags_dir_has_recursive():
    app = ConfirmApp()
    async with app.run_test() as pilot:
        results = []
        app.push_screen(AddFlagsScreen("Add dir", is_dir=True), results.append)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        flags = results[0]
        assert flags["recursive"] is True
        assert "exact" in flags


async def test_add_flags_cancel():
    app = ConfirmApp()
    async with app.run_test() as pilot:
        results = []
        app.push_screen(AddFlagsScreen("Add file"), results.append)
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert results == [None]


async def test_chattr_no_changes():
    app = ConfirmApp()
    async with app.run_test() as pilot:
        results = []
        current = {"encrypted": False, "executable": True}
        app.push_screen(ChattrScreen("Attrs", current), results.append)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        # No changes made — should dismiss with None
        assert results == [None]


async def test_chattr_cancel():
    app = ConfirmApp()
    async with app.run_test() as pilot:
        results = []
        app.push_screen(ChattrScreen("Attrs", {}), results.append)
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert results == [None]
