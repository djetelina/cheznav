"""Non-interactive `cheznav info` command.

Prints the cheznav and chezmoi versions and chezmoi's config status without
launching the TUI, so it is safe to run in scripts, CI, and packaging smoke
tests (e.g. Homebrew).
"""

import os
import shutil
import subprocess
from pathlib import Path

from cheznav import __version__


def _find_chezmoi_config() -> tuple[Path | None, Path]:
    """Locate chezmoi's config file in its default config directory."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    search_dir = (Path(xdg) if xdg else Path.home() / ".config") / "chezmoi"
    for name in ("chezmoi.toml", "chezmoi.yaml", "chezmoi.yml", "chezmoi.json", "chezmoi.jsonc"):
        candidate = search_dir / name
        if candidate.is_file():
            return candidate, search_dir
    return None, search_dir


def print_info(config_path: str | None = None) -> None:
    """Print cheznav/chezmoi versions and chezmoi's config status, then return."""
    print(f"cheznav {__version__}")

    chezmoi_bin = shutil.which("chezmoi")
    if chezmoi_bin is None:
        print("chezmoi: not found on PATH (install from https://www.chezmoi.io)")
        return

    version_proc = subprocess.run([chezmoi_bin, "--version"], capture_output=True, text=True, check=False)
    version_line = next(iter(version_proc.stdout.splitlines()), "").strip() or "unknown version"
    print(f"chezmoi: {version_line} ({chezmoi_bin})")

    if config_path:
        config = Path(config_path)
        config_file = config if config.is_file() else None
        search_dir = config
    else:
        config_file, search_dir = _find_chezmoi_config()
    print(f"config:  {config_file}" if config_file else f"config:  none found (looked in {search_dir})")

    prefix = [chezmoi_bin, "--config", config_path] if config_path else [chezmoi_bin]
    source_proc = subprocess.run([*prefix, "source-path"], capture_output=True, text=True, check=False)
    source = Path(source_proc.stdout.strip()) if source_proc.returncode == 0 and source_proc.stdout.strip() else None
    if source and source.is_dir():
        print(f"source:  {source} ({'git repo' if (source / '.git').exists() else 'directory'})")
    else:
        print("source:  not initialized")
