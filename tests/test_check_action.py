"""Tests for check_action context-aware binding visibility."""

import pytest

from cheznav.main import CheznavApp


@pytest.fixture
def app():
    return CheznavApp()


class TestDiffModeActions:
    """When diff is active, only diff/global/open_actions should be allowed."""

    def test_diff_actions_hidden_when_not_active(self, app):
        app._diff_active = False
        assert app.check_action("diff_close", ()) is False
        assert app.check_action("diff_accept_left", ()) is False
        assert app.check_action("diff_accept_right", ()) is False

    def test_diff_actions_visible_when_active(self, app):
        app._diff_active = True
        assert app.check_action("diff_close", ()) is True
        assert app.check_action("diff_accept_left", ()) is True
        assert app.check_action("diff_accept_right", ()) is True

    def test_open_actions_available_in_diff_mode(self, app):
        app._diff_active = True
        assert app.check_action("open_actions", ()) is True

    def test_home_actions_hidden_in_diff_mode(self, app):
        app._diff_active = True
        assert app.check_action("home_add", ()) is False
        assert app.check_action("home_encrypt", ()) is False
        assert app.check_action("home_template", ()) is False
        assert app.check_action("home_re_add", ()) is False

    def test_managed_actions_hidden_in_diff_mode(self, app):
        app._diff_active = True
        assert app.check_action("managed_apply", ()) is False
        assert app.check_action("managed_edit", ()) is False
        assert app.check_action("managed_diff", ()) is False
        assert app.check_action("managed_forget", ()) is False

    def test_global_actions_available_in_diff_mode(self, app):
        app._diff_active = True
        assert app.check_action("help", ()) is True
        assert app.check_action("quit", ()) is True
        assert app.check_action("switch_pane_left", ()) is True
        assert app.check_action("switch_pane_right", ()) is True

    def test_commands_hidden_in_diff_mode(self, app):
        app._diff_active = True
        assert app.check_action("open_commands", ()) is False

    def test_view_hidden_in_diff_mode(self, app):
        app._diff_active = True
        assert app.check_action("view", ()) is False
