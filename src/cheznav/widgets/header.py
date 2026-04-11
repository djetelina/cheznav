from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label, Link, Static


class Logo(Static):
    DEFAULT_CSS = """
    Logo {
        width: auto;
        height: 3;
        background: $background;
    }
    """

    def render(self):
        from cheznav import __version__  # noqa: PLC0415

        return (
            "[$accent]  ┌───────┐\n"
            "[$secondary]│[/$secondary]  [$primary]cheznav[/$primary]  [$secondary]│[/$secondary]\n"
            f"[$accent]  └─{__version__}─┘"
        )


class StatusBar(Container):
    DEFAULT_CSS = """
    StatusBar {
        layout: horizontal;
        background: $background;
        width: 1fr;
        height: 3;
        border: round $accent;
        border-right: none;
        border-left: none;
    }

    StatusBar > #status-inner {
        layout: grid;
        width: 100%;
        grid-size: 2;
        grid-columns: 1fr auto;
    }

    #status-info {
        width: auto;
        align: left middle;
        layout: horizontal;
        padding: 0 1;
    }

    #status-links {
        width: auto;
        align: right middle;
        layout: horizontal;
    }

    #status-links Link {
        padding: 0 1;
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._remote_label = Label("")
        self._git_status_label = Label("")

    def compose(self) -> ComposeResult:
        with Container(id="status-inner"):
            with Container(id="status-info"):
                yield Label("\\[ ")
                yield self._remote_label
                yield Label(" ]")
                yield self._git_status_label
            with Container(id="status-links"):
                yield Link("GitHub", url="https://github.com/djetelina/cheznav")
                yield Link("Changelog", url="https://github.com/djetelina/cheznav/blob/main/CHANGELOG.md")

    def update_info(
        self,
        remote: str,
        uncommitted: int = 0,
        ahead: int = 0,
        behind: int = 0,
        **_,
    ) -> None:
        self._remote_label.update(remote or "no remote")
        parts = []
        if uncommitted > 0:
            parts.append(f"[$warning]{uncommitted} uncommitted[/]")
        if ahead > 0:
            parts.append(f"[$accent]{ahead} ahead[/]")
        if behind > 0:
            parts.append(f"[$error]{behind} behind[/]")
        if parts:
            self._git_status_label.update(" \\[ " + ", ".join(parts) + " ]")
        else:
            self._git_status_label.update("")


class Legend(Label):
    def __init__(self, **kwargs) -> None:
        super().__init__("[$success]managed[/]  [$warning]diff[/]  🔄 uncommitted  🔒 encrypted  📝 template  ⚡ executable", **kwargs)


class Header(Container):
    DEFAULT_CSS = """
    Header {
        layout: horizontal;
        height: 3;
        background: $background;
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._status_bar = StatusBar()

    def update_info(self, remote: str, **kwargs) -> None:
        self._status_bar.update_info(remote, **kwargs)

    def compose(self) -> ComposeResult:
        yield self._status_bar
        yield Logo()
