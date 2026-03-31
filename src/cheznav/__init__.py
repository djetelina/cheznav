from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("cheznav")
except PackageNotFoundError:
    __version__ = "0.1.0"

THEME = "dracula"
