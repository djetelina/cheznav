"""Tests for git dirty marker rendering in tree labels."""

from unittest.mock import patch

from cheznav.widgets.managed_tree import ManagedTree
from tests.conftest import make_entry


class TestMakeLabel:
    def _make_tree(self):
        tree = ManagedTree.__new__(ManagedTree)
        tree.diff_paths = set()
        tree.git_dirty_paths = set()
        return tree

    def _call(self, tree, name, entry, **kwargs):
        with patch.object(type(tree), "_theme_color", return_value="magenta"):
            return tree._make_label(name, entry, **kwargs)

    def test_plain_label(self):
        tree = self._make_tree()
        entry = make_entry(".bashrc")
        label = self._call(tree, ".bashrc", entry)
        assert label.plain == ".bashrc"
        assert "🔄" not in label.plain

    def test_git_dirty_shows_emoji(self):
        tree = self._make_tree()
        entry = make_entry(".bashrc")
        label = self._call(tree, ".bashrc", entry, git_dirty=True)
        assert "🔄" in label.plain

    def test_diff_and_dirty_both_shown(self):
        tree = self._make_tree()
        entry = make_entry(".bashrc")
        label = self._call(tree, ".bashrc", entry, has_diff=True, git_dirty=True)
        assert "🔄" in label.plain
        assert ".bashrc" in label.plain

    def test_dirty_with_indicators(self):
        tree = self._make_tree()
        entry = make_entry(".bashrc", is_template=True)
        label = self._call(tree, ".bashrc", entry, git_dirty=True)
        assert "🔄" in label.plain
        assert "📝" in label.plain
