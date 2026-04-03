"""Tests for chezmoi module helpers."""

from unittest.mock import AsyncMock, patch

import pytest

from cheznav.chezmoi import (
    _parse_attributes,
    git_ahead_behind,
    git_status_porcelain,
)


class TestParseAttributes:
    def test_plain_file(self):
        attrs = _parse_attributes("dot_gitconfig")
        assert not attrs["is_encrypted"]
        assert not attrs["is_private"]
        assert not attrs["is_executable"]
        assert not attrs["is_template"]

    def test_encrypted(self):
        attrs = _parse_attributes("encrypted_private_dot_ssh/encrypted_private_key")
        assert attrs["is_encrypted"]
        assert attrs["is_private"]

    def test_private(self):
        attrs = _parse_attributes("private_dot_config/something")
        assert attrs["is_private"]
        assert not attrs["is_encrypted"]

    def test_executable(self):
        attrs = _parse_attributes("executable_dot_local/bin/myscript")
        assert attrs["is_executable"]

    def test_template(self):
        attrs = _parse_attributes("dot_gitconfig.tmpl")
        assert attrs["is_template"]

    def test_not_template_without_suffix(self):
        attrs = _parse_attributes("dot_gitconfig")
        assert not attrs["is_template"]

    def test_combined_attributes(self):
        attrs = _parse_attributes("encrypted_private_dot_config/secret.tmpl")
        assert attrs["is_encrypted"]
        assert attrs["is_private"]
        assert attrs["is_template"]
        assert not attrs["is_executable"]


def _mock_run_git(stdout: str, rc: int = 0):
    return patch("cheznav.chezmoi._run_git", new_callable=AsyncMock, return_value=(stdout, "", rc))


class TestGitStatusPorcelain:
    @pytest.mark.asyncio
    async def test_modified_file(self):
        with _mock_run_git(" M dot_bashrc\n"):
            result = await git_status_porcelain()
        assert result == [("M", "dot_bashrc")]

    @pytest.mark.asyncio
    async def test_multiple_statuses(self):
        with _mock_run_git("M  dot_bashrc\n?? new_file\n A dot_zshrc\n"):
            result = await git_status_porcelain()
        assert result == [("M", "dot_bashrc"), ("??", "new_file"), ("A", "dot_zshrc")]

    @pytest.mark.asyncio
    async def test_rename_uses_destination(self):
        with _mock_run_git("R  old_name -> new_name\n"):
            result = await git_status_porcelain()
        assert result == [("R", "new_name")]

    @pytest.mark.asyncio
    async def test_empty_output(self):
        with _mock_run_git(""):
            result = await git_status_porcelain()
        assert result == []

    @pytest.mark.asyncio
    async def test_short_line_skipped(self):
        with _mock_run_git("XY\n"):
            result = await git_status_porcelain()
        assert result == []

    @pytest.mark.asyncio
    async def test_failure_returns_empty(self):
        with _mock_run_git("", rc=1):
            result = await git_status_porcelain()
        assert result == []


class TestGitAheadBehind:
    @pytest.mark.asyncio
    async def test_normal(self):
        with _mock_run_git("3\t1\n"):
            result = await git_ahead_behind()
        assert result == (3, 1)

    @pytest.mark.asyncio
    async def test_zero(self):
        with _mock_run_git("0\t0\n"):
            result = await git_ahead_behind()
        assert result == (0, 0)

    @pytest.mark.asyncio
    async def test_failure_returns_zero(self):
        with _mock_run_git("", rc=128):
            result = await git_ahead_behind()
        assert result == (0, 0)

    @pytest.mark.asyncio
    async def test_non_integer_returns_zero(self):
        with _mock_run_git("abc def\n"):
            result = await git_ahead_behind()
        assert result == (0, 0)

    @pytest.mark.asyncio
    async def test_unexpected_format_returns_zero(self):
        with _mock_run_git("just_one_token\n"):
            result = await git_ahead_behind()
        assert result == (0, 0)

    @pytest.mark.asyncio
    async def test_empty_output_returns_zero(self):
        with _mock_run_git("\n"):
            result = await git_ahead_behind()
        assert result == (0, 0)
