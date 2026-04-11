from importlib.metadata import version

from cheznav.theme import resolve_theme

__version__ = version("cheznav")

THEME = resolve_theme()
