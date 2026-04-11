import configparser
import os
from pathlib import Path

from textual.theme import BUILTIN_THEMES

_PREFIX_THEMES = (
    "catppuccin-mocha",
    "catppuccin-frappe",
    "catppuccin-macchiato",
    "catppuccin-latte",
    "rose-pine",
)

_AVAILABLE_THEMES = set(BUILTIN_THEMES)


def _match_gtk_theme(gtk_theme_name: str) -> str | None:
    """Match a GTK theme name against available Textual themes.

    Lowercases the GTK theme name, tries exact match first, then prefix match
    for known multi-variant theme families.

    Returns the matched theme name or None if no match is found.
    """
    if not gtk_theme_name:
        return None

    lowered = gtk_theme_name.lower()

    if lowered in _AVAILABLE_THEMES:
        return lowered

    for prefix in _PREFIX_THEMES:
        if lowered.startswith(prefix + "-") and prefix in _AVAILABLE_THEMES:
            return prefix

    return None


def _read_gtk_settings(path: Path) -> str | None:
    """Read gtk-theme-name from a GTK settings.ini file.

    Returns the theme name string, or None if the file is missing,
    the key/section is absent, the value is empty, or parsing fails.
    """
    if not path.exists():
        return None

    try:
        parser = configparser.ConfigParser()
        parser.read(path)
        value = parser.get("Settings", "gtk-theme-name", fallback=None)
    except configparser.Error:
        return None

    return value if value else None


def resolve_theme(*, default: str = "dracula") -> str:
    """Resolve the Textual theme to use.

    Priority:
    1. TEXTUAL_THEME env var (returned as-is, no validation)
    2. GTK_THEME env var (lowercased and matched)
    3. ~/.config/gtk-4.0/settings.ini
    4. ~/.config/gtk-3.0/settings.ini
    5. default fallback

    Uses XDG_CONFIG_HOME env var with fallback to ~/.config.
    """
    textual_theme = os.environ.get("TEXTUAL_THEME")
    if textual_theme and textual_theme in _AVAILABLE_THEMES:
        return textual_theme

    gtk_theme_env = os.environ.get("GTK_THEME")
    if gtk_theme_env:
        matched = _match_gtk_theme(gtk_theme_env)
        if matched:
            return matched

    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    config_home = Path(xdg_config) if xdg_config else Path.home() / ".config"

    for gtk_version in ("gtk-4.0", "gtk-3.0"):
        settings_path = config_home / gtk_version / "settings.ini"
        raw = _read_gtk_settings(settings_path)
        if raw:
            matched = _match_gtk_theme(raw)
            if matched:
                return matched

    return default
