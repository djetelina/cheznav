import asyncio
import json
import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class ChezmoiError(Exception):
    """Raised when a chezmoi subprocess fails."""


@dataclass(frozen=True)
class ManagedEntry:
    target_relative: str
    target_absolute: Path
    source_absolute: Path
    source_relative: str
    is_encrypted: bool
    is_private: bool
    is_executable: bool
    is_template: bool

    @property
    def indicator_str(self) -> str:
        parts = []
        if self.is_encrypted:
            parts.append("🔒")
        if self.is_template:
            parts.append("📝")
        if self.is_executable:
            parts.append("⚡")
        return "".join(parts)


def _parse_attributes(source_relative: str) -> dict[str, bool]:
    # Attributes on parent dirs (e.g. private_dot_config/) apply to children too
    all_parts = source_relative.replace("/", " ")
    return {
        "is_encrypted": "encrypted_" in all_parts,
        "is_private": "private_" in all_parts,
        "is_executable": "executable_" in all_parts,
        "is_template": all_parts.endswith(".tmpl"),
    }


_dry_run: bool = False

# Commands that modify the filesystem — only these get the -n flag in dry-run mode
_MUTATING_COMMANDS = frozenset({"add", "apply", "chattr", "destroy", "edit", "forget", "re-add", "update"})


def set_dry_run(enabled: bool) -> None:
    global _dry_run  # noqa: PLW0603
    _dry_run = enabled


async def _run(args: list[str]) -> tuple[str, str, int]:
    if _dry_run and args and args[0] in _MUTATING_COMMANDS:
        args = ["-n", *args]
    args = ["--no-tty", *args]
    proc = await asyncio.create_subprocess_exec(
        "chezmoi",
        *args,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode(), stderr.decode(), proc.returncode


def _check(stdout: str, stderr: str, rc: int, cmd: str) -> str:
    """Return stdout if rc == 0, otherwise raise ChezmoiError."""
    if rc != 0:
        msg = stderr.strip() or f"chezmoi {cmd} failed (exit {rc})"
        raise ChezmoiError(msg)
    return stdout


async def managed() -> list[ManagedEntry]:
    stdout, stderr, rc = await _run(["managed", "--include=files,symlinks", "--path-style=all", "--format=json"])
    stdout = _check(stdout, stderr, rc, "managed")
    if not stdout.strip():
        return []
    raw = json.loads(stdout)
    entries = []
    for target_rel, info in raw.items():
        attrs = _parse_attributes(info["sourceRelative"])
        entries.append(
            ManagedEntry(
                target_relative=target_rel,
                target_absolute=Path(info["absolute"]),
                source_absolute=Path(info["sourceAbsolute"]),
                source_relative=info["sourceRelative"],
                **attrs,
            )
        )
    return entries


async def update() -> tuple[str, str, int]:
    return await _run(["update"])


async def data() -> str:
    stdout, stderr, rc = await _run(["data", "--format=json"])
    return _check(stdout, stderr, rc, "data")


async def execute_template(source_path: str) -> str:
    stdout, stderr, rc = await _run(["execute-template", "--file", source_path])
    return _check(stdout, stderr, rc, "execute-template")


async def diff(target: str) -> str:
    stdout, _, _ = await _run(["diff", target])
    # diff returns rc=1 when there are differences — not an error
    return stdout


async def cat(target: str) -> str:
    stdout, stderr, rc = await _run(["cat", target])
    return _check(stdout, stderr, rc, "cat")


async def add(target: str, **flags: bool) -> tuple[str, str, int]:
    args = ["add", target]
    for flag, enabled in flags.items():
        if enabled:
            args.append(f"--{flag}")
    return await _run(args)


async def chattr(target: str, changes: dict[str, bool]) -> tuple[str, str, int]:
    """Run chezmoi chattr with +attr or -attr (noattr) modifiers."""
    modifier = ",".join(f"+{attr}" if enabled else f"no{attr}" for attr, enabled in changes.items())
    return await _run(["chattr", modifier, target])


async def re_add(target: str) -> tuple[str, str, int]:
    return await _run(["re-add", target])


async def edit(target: str, apply: bool = True) -> tuple[str, str, int]:
    args = ["edit", target]
    if apply:
        args.append("--apply")
    return await _run(args)


async def apply(target: str) -> tuple[str, str, int]:
    return await _run(["apply", "--force", target])


async def forget(target: str) -> tuple[str, str, int]:
    return await _run(["forget", "--force", target])


async def destroy(target: str) -> tuple[str, str, int]:
    return await _run(["destroy", "--force", target])


_source_path_cache: Path | None = None


async def source_path() -> Path:
    global _source_path_cache  # noqa: PLW0603
    if _source_path_cache is not None:
        return _source_path_cache
    stdout, stderr, rc = await _run(["source-path"])
    stdout = _check(stdout, stderr, rc, "source-path")
    _source_path_cache = Path(stdout.strip())
    return _source_path_cache


async def metafiles() -> list[Path]:
    """Return chezmoi meta files and run scripts from the source directory."""
    try:
        src = await source_path()
        results = []
        for item in sorted(src.iterdir(), key=lambda p: p.name.lower()):
            if item.name.startswith(".chezmoi") or (item.is_file() and item.name.startswith("run_")):
                results.append(item)
        return results
    except (ChezmoiError, OSError) as exc:
        log.warning("Failed to list metafiles: %s", exc)
        return []


async def externals() -> dict[str, Any]:
    """Return external paths and config from .chezmoiexternal.toml in the source root."""
    try:
        src = await source_path()
        ext_file = src / ".chezmoiexternal.toml"
        if not ext_file.exists():
            return {}
        with ext_file.open("rb") as f:
            return await asyncio.to_thread(tomllib.load, f)
    except (ChezmoiError, OSError, tomllib.TOMLDecodeError) as exc:
        log.warning("Failed to read externals: %s", exc)
        return {}


async def add_ignore(pattern: str) -> None:
    """Append a pattern to .chezmoiignore."""
    src = await source_path()
    ignore_file = src / ".chezmoiignore"

    def _write() -> None:
        existing = ignore_file.read_text() if ignore_file.exists() else ""
        separator = "\n" if existing and not existing.endswith("\n") else ""
        ignore_file.write_text(existing + separator + pattern + "\n")

    await asyncio.to_thread(_write)


async def git_remote_url() -> str:
    """Return the chezmoi repo's git remote URL, or empty string."""
    proc = await asyncio.create_subprocess_exec(
        "chezmoi",
        "git",
        "--",
        "remote",
        "get-url",
        "origin",
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    if proc.returncode != 0:
        return ""
    url = stdout.decode().strip().removesuffix(".git")
    for prefix in ("https://github.com/", "git@github.com:"):
        if url.startswith(prefix):
            return url.removeprefix(prefix)
    return url


async def dump_config() -> tuple[str, str, int]:
    return await _run(["dump-config"])


async def doctor() -> tuple[str, str, int]:
    return await _run(["doctor"])


async def status() -> list[tuple[str, str, str]]:
    stdout, stderr, rc = await _run(["status"])
    # status returns rc=1 when there are differences — not an error
    if rc not in {0, 1}:
        log.warning("chezmoi status failed: %s", stderr.strip())
    results = []
    min_line_length = 3
    for line in stdout.strip().splitlines():
        if len(line) >= min_line_length:
            source_state = line[0]
            dest_state = line[1]
            path = line[2:].strip()
            results.append((source_state, dest_state, path))
    return results
