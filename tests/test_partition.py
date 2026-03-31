"""Tests for _partition_entries."""

from cheznav.main import CheznavApp
from tests.conftest import make_entry


class TestPartitionEntries:
    def test_no_externals(self):
        entries = [make_entry(".bashrc"), make_entry(".vimrc")]
        managed, external = CheznavApp._partition_entries(entries, {})
        assert len(managed) == 2  # noqa: PLR2004
        assert external == {}

    def test_separates_externals(self):
        entries = [
            make_entry(".bashrc"),
            make_entry(".oh-my-zsh/plugins/git"),
            make_entry(".oh-my-zsh/themes/robbyrussell"),
        ]
        ext_config = {".oh-my-zsh": {"type": "archive", "url": "https://example.com"}}
        managed, external = CheznavApp._partition_entries(entries, ext_config)
        assert len(managed) == 1
        assert managed[0].target_relative == ".bashrc"
        assert len(external[".oh-my-zsh"]) == 2  # noqa: PLR2004

    def test_multiple_externals(self):
        entries = [
            make_entry(".bashrc"),
            make_entry(".oh-my-zsh/file1"),
            make_entry(".tmux/plugins/tpm"),
        ]
        ext_config = {
            ".oh-my-zsh": {"type": "archive"},
            ".tmux/plugins/tpm": {"type": "git-repo"},
        }
        managed, external = CheznavApp._partition_entries(entries, ext_config)
        assert len(managed) == 1
        assert len(external[".oh-my-zsh"]) == 1
        assert len(external[".tmux/plugins/tpm"]) == 1

    def test_empty_externals_have_keys(self):
        entries = [make_entry(".bashrc")]
        ext_config = {".oh-my-zsh": {"type": "archive"}}
        managed, external = CheznavApp._partition_entries(entries, ext_config)
        assert len(managed) == 1
        assert ".oh-my-zsh" in external
        assert len(external[".oh-my-zsh"]) == 0
