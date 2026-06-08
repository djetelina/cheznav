from unittest.mock import patch

from cheznav.main import main


def test_main_sets_custom_chezmoi_config_path():
    with (
        patch("cheznav.main.CheznavApp") as app_cls,
        patch("cheznav.main.chezmoi.set_config_path") as set_config_path,
        patch("sys.argv", ["cheznav", "--chezmoi-config", "~/.config/chezmoi/work.toml"]),
    ):
        main()

    set_config_path.assert_called_once()
    called_path = set_config_path.call_args.args[0]
    assert called_path.endswith("/.config/chezmoi/work.toml")
    assert "~" not in called_path
    app_cls.assert_called_once_with(dry_run=False)
    app_cls.return_value.run.assert_called_once()


def test_main_without_custom_config_does_not_set_it():
    with (
        patch("cheznav.main.CheznavApp") as app_cls,
        patch("cheznav.main.chezmoi.set_config_path") as set_config_path,
        patch("sys.argv", ["cheznav"]),
    ):
        main()

    set_config_path.assert_called_once_with(None)
    app_cls.assert_called_once_with(dry_run=False)
    app_cls.return_value.run.assert_called_once()
