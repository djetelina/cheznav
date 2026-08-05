import subprocess
from unittest.mock import patch

from cheznav.main import main


def test_info_does_not_launch_tui_when_chezmoi_missing(capsys):
    with (
        patch("cheznav.main.CheznavApp") as app_cls,
        patch("cheznav.info.shutil.which", return_value=None),
        patch("sys.argv", ["cheznav", "info"]),
    ):
        main()

    app_cls.assert_not_called()
    out = capsys.readouterr().out
    assert "cheznav" in out
    assert "chezmoi: not found" in out


def test_info_reports_versions_config_and_source(capsys, tmp_path, monkeypatch):
    source = tmp_path / "source"
    (source / ".git").mkdir(parents=True)
    config_dir = tmp_path / "config" / "chezmoi"
    config_dir.mkdir(parents=True)
    (config_dir / "chezmoi.toml").write_text('sourceDir = "x"\n')
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    def fake_run(cmd, **_kwargs):
        if cmd[-1] == "--version":
            return subprocess.CompletedProcess(cmd, 0, stdout="chezmoi version v2.50.0\nrest\n", stderr="")
        if cmd[-1] == "source-path":
            return subprocess.CompletedProcess(cmd, 0, stdout=f"{source}\n", stderr="")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

    with (
        patch("cheznav.main.CheznavApp") as app_cls,
        patch("cheznav.info.shutil.which", return_value="/usr/bin/chezmoi"),
        patch("cheznav.info.subprocess.run", side_effect=fake_run),
        patch("sys.argv", ["cheznav", "info"]),
    ):
        main()

    app_cls.assert_not_called()
    out = capsys.readouterr().out
    assert "chezmoi version v2.50.0" in out
    assert "chezmoi version v2.50.0\nrest" not in out  # only the first line
    assert str(config_dir / "chezmoi.toml") in out
    assert "git repo" in out


def test_info_reports_uninitialized_source_and_no_config(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty"))

    def fake_run(cmd, **_kwargs):
        if cmd[-1] == "--version":
            return subprocess.CompletedProcess(cmd, 0, stdout="chezmoi version v2.50.0\n", stderr="")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="chezmoi: source dir not found\n")

    with (
        patch("cheznav.info.shutil.which", return_value="/usr/bin/chezmoi"),
        patch("cheznav.info.subprocess.run", side_effect=fake_run),
        patch("sys.argv", ["cheznav", "info"]),
    ):
        main()

    out = capsys.readouterr().out
    assert "none found" in out
    assert "source:  not initialized" in out
