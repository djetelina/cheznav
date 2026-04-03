"""Shared test helpers for chezmoi TUI tests."""

from pathlib import Path
from unittest.mock import patch

# Fix pytest-textual-snapshot 1.0 compat with syrupy 5.x (attribute renamed)
from pytest_textual_snapshot import SVGImageExtension

from cheznav.chezmoi import ManagedEntry

SVGImageExtension.file_extension = "svg"


def make_entry(name: str, base: str = "/home/test", **overrides) -> ManagedEntry:
    defaults = dict(
        target_relative=name,
        target_absolute=Path(f"{base}/{name}"),
        source_absolute=Path(f"/source/{name}"),
        source_relative=f"dot_{name}",
        is_encrypted=False,
        is_private=False,
        is_executable=False,
        is_template=False,
    )
    defaults.update(overrides)
    return ManagedEntry(**defaults)


async def mock_managed_empty():
    return []


async def mock_status_empty():
    return []


async def mock_cat(target):
    return "old content\n"


async def mock_apply(target):
    return "", "", 0


async def mock_re_add(target):
    return "", "", 0


async def mock_metafiles():
    return []


async def mock_source_path():
    return Path("/source")


async def mock_git_remote_url():
    return "test/dotfiles"


async def mock_externals():
    return {}


async def mock_git_fetch():
    return None


async def mock_git_status_porcelain():
    return []


async def mock_git_ahead_behind():
    return (0, 0)


def patch_chezmoi(**overrides):
    """Patch chezmoi module with standard mocks. Override any with kwargs."""
    defaults = dict(
        managed=mock_managed_empty,
        status=mock_status_empty,
        cat=mock_cat,
        apply=mock_apply,
        re_add=mock_re_add,
        metafiles=mock_metafiles,
        source_path=mock_source_path,
        git_remote_url=mock_git_remote_url,
        externals=mock_externals,
        git_fetch=mock_git_fetch,
        git_status_porcelain=mock_git_status_porcelain,
        git_ahead_behind=mock_git_ahead_behind,
    )
    defaults.update(overrides)
    return patch.multiple("cheznav.chezmoi", **defaults)


async def settle(pilot, n=6):
    """Give async workers time to complete."""
    for _ in range(n):
        await pilot.pause()
