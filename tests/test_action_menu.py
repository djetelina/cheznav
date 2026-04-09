"""Tests for action menu builders."""

from pathlib import Path

from cheznav.widgets.action_menu import build_home_actions, build_managed_actions
from cheznav.widgets.managed_tree import ExternalRoot
from tests.conftest import make_entry


class TestBuildHomeActions:
    def test_no_file_selected(self):
        _title, actions = build_home_actions(None, False, False)
        assert actions == []

    def test_unmanaged_file(self):
        path = Path.home() / "new_file"
        _title, actions = build_home_actions(path, is_managed=False, has_diff=False)
        action_names = [a.action for a in actions]
        assert "home_add" in action_names
        assert "view" in action_names
        assert "home_re_add" not in action_names

    def test_directory(self):
        path = Path.home() / "somedir"
        _title, actions = build_home_actions(path, is_managed=False, has_diff=False, is_dir=True)
        action_names = [a.action for a in actions]
        assert "home_toggle" in action_names
        assert "home_add" in action_names

    def test_managed_file(self):
        path = Path.home() / ".bashrc"
        _title, actions = build_home_actions(path, is_managed=True, has_diff=False)
        action_names = [a.action for a in actions]
        assert "home_re_add" in action_names
        assert "home_add" not in action_names


class TestBuildManagedActions:
    def test_managed_entry(self):
        entry = make_entry(".bashrc")
        _title, actions = build_managed_actions(entry, has_diff=False)
        action_names = [a.action for a in actions]
        assert "managed_apply" in action_names
        assert "managed_edit" in action_names
        assert "managed_forget" in action_names
        assert "managed_diff" in action_names

    def test_managed_entry_with_diff(self):
        entry = make_entry(".bashrc")
        _title, actions = build_managed_actions(entry, has_diff=True)
        action_names = [a.action for a in actions]
        assert "managed_diff" in action_names

    def test_external_root_with_diffs(self):
        ext = ExternalRoot(target_path=".oh-my-zsh", ext_type="archive", url="https://example.com", file_count=100, diff_count=5)
        title, actions = build_managed_actions(ext, has_diff=False)
        action_names = [a.action for a in actions]
        assert "managed_apply" in action_names
        assert "external" in title

    def test_external_root_no_diffs(self):
        ext = ExternalRoot(target_path=".oh-my-zsh", ext_type="archive", url="https://example.com", file_count=100, diff_count=0)
        _title, actions = build_managed_actions(ext, has_diff=False)
        action_names = [a.action for a in actions]
        assert "managed_apply" in action_names

    def test_directory_node(self):
        _title, actions = build_managed_actions(".config/nvim", has_diff=False)
        action_names = [a.action for a in actions]
        assert "managed_ignore" in action_names
        assert "managed_toggle" in action_names

    def test_metafile(self):
        path = Path("/source/.chezmoiignore")
        _title, actions = build_managed_actions(path, has_diff=False)
        action_names = [a.action for a in actions]
        assert "managed_edit" in action_names
        assert "view" in action_names

    def test_nothing_selected(self):
        _title, actions = build_managed_actions(None, has_diff=False)
        assert actions == []
