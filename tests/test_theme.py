"""Tests for cheznav.theme module."""

from pathlib import Path

from cheznav.theme import _match_gtk_theme, _read_gtk_settings, resolve_theme


class TestMatchGtkTheme:
    def test_exact_match_case_insensitive(self):
        assert _match_gtk_theme("Dracula") == "dracula"

    def test_already_lowercase(self):
        assert _match_gtk_theme("nord") == "nord"

    def test_no_match_returns_none(self):
        assert _match_gtk_theme("Adwaita") is None

    def test_prefix_catppuccin_mocha(self):
        assert _match_gtk_theme("catppuccin-mocha-blue-standard+default") == "catppuccin-mocha"

    def test_prefix_catppuccin_frappe(self):
        assert _match_gtk_theme("catppuccin-frappe-lavender-standard+default") == "catppuccin-frappe"

    def test_prefix_catppuccin_macchiato(self):
        assert _match_gtk_theme("Catppuccin-Macchiato-Teal-Standard+Default") == "catppuccin-macchiato"

    def test_prefix_catppuccin_latte(self):
        assert _match_gtk_theme("catppuccin-latte-pink-standard+default") == "catppuccin-latte"

    def test_prefix_rose_pine(self):
        assert _match_gtk_theme("rose-pine-something-extra") == "rose-pine"

    def test_exact_beats_prefix(self):
        assert _match_gtk_theme("rose-pine-moon") == "rose-pine-moon"

    def test_empty_string_returns_none(self):
        assert _match_gtk_theme("") is None


class TestReadGtkSettings:
    def test_reads_theme_name(self, tmp_path: Path):
        settings = tmp_path / "settings.ini"
        settings.write_text("[Settings]\ngtk-theme-name = Dracula\n")
        assert _read_gtk_settings(settings) == "Dracula"

    def test_missing_file_returns_none(self, tmp_path: Path):
        assert _read_gtk_settings(tmp_path / "nonexistent.ini") is None

    def test_missing_key_returns_none(self, tmp_path: Path):
        settings = tmp_path / "settings.ini"
        settings.write_text("[Settings]\ngtk-font-name = Sans 10\n")
        assert _read_gtk_settings(settings) is None

    def test_missing_section_returns_none(self, tmp_path: Path):
        settings = tmp_path / "settings.ini"
        settings.write_text("[General]\ngtk-theme-name = Dracula\n")
        assert _read_gtk_settings(settings) is None

    def test_empty_value_returns_none(self, tmp_path: Path):
        settings = tmp_path / "settings.ini"
        settings.write_text("[Settings]\ngtk-theme-name =\n")
        assert _read_gtk_settings(settings) is None


class TestResolveTheme:
    def test_textual_theme_wins_over_gtk_theme(self, monkeypatch):
        monkeypatch.setenv("TEXTUAL_THEME", "nord")
        monkeypatch.setenv("GTK_THEME", "dracula")
        assert resolve_theme() == "nord"

    def test_textual_theme_invalid_falls_through(self, monkeypatch, tmp_path):
        monkeypatch.setenv("TEXTUAL_THEME", "not-a-real-theme")
        monkeypatch.delenv("GTK_THEME", raising=False)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        assert resolve_theme() == "dracula"

    def test_gtk_theme_env_exact_match(self, monkeypatch):
        monkeypatch.delenv("TEXTUAL_THEME", raising=False)
        monkeypatch.setenv("GTK_THEME", "Nord")
        assert resolve_theme() == "nord"

    def test_gtk_theme_env_no_match_falls_through(self, monkeypatch, tmp_path):
        monkeypatch.delenv("TEXTUAL_THEME", raising=False)
        monkeypatch.setenv("GTK_THEME", "Adwaita")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        assert resolve_theme() == "dracula"

    def test_gtk_theme_env_no_match_falls_through_to_ini(self, monkeypatch, tmp_path):
        monkeypatch.delenv("TEXTUAL_THEME", raising=False)
        monkeypatch.setenv("GTK_THEME", "Adwaita")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        gtk4_dir = tmp_path / "gtk-4.0"
        gtk4_dir.mkdir()
        (gtk4_dir / "settings.ini").write_text("[Settings]\ngtk-theme-name = Nord\n")
        assert resolve_theme() == "nord"

    def test_gtk4_settings_ini(self, monkeypatch, tmp_path):
        monkeypatch.delenv("TEXTUAL_THEME", raising=False)
        monkeypatch.delenv("GTK_THEME", raising=False)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        gtk4_dir = tmp_path / "gtk-4.0"
        gtk4_dir.mkdir()
        (gtk4_dir / "settings.ini").write_text("[Settings]\ngtk-theme-name = nord\n")
        assert resolve_theme() == "nord"

    def test_gtk3_settings_ini_fallback(self, monkeypatch, tmp_path):
        monkeypatch.delenv("TEXTUAL_THEME", raising=False)
        monkeypatch.delenv("GTK_THEME", raising=False)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        gtk3_dir = tmp_path / "gtk-3.0"
        gtk3_dir.mkdir()
        (gtk3_dir / "settings.ini").write_text("[Settings]\ngtk-theme-name = nord\n")
        assert resolve_theme() == "nord"

    def test_gtk4_takes_priority_over_gtk3(self, monkeypatch, tmp_path):
        monkeypatch.delenv("TEXTUAL_THEME", raising=False)
        monkeypatch.delenv("GTK_THEME", raising=False)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        gtk4_dir = tmp_path / "gtk-4.0"
        gtk4_dir.mkdir()
        (gtk4_dir / "settings.ini").write_text("[Settings]\ngtk-theme-name = catppuccin-mocha-blue-standard+default\n")
        gtk3_dir = tmp_path / "gtk-3.0"
        gtk3_dir.mkdir()
        (gtk3_dir / "settings.ini").write_text("[Settings]\ngtk-theme-name = nord\n")
        assert resolve_theme() == "catppuccin-mocha"

    def test_fallback_to_default(self, monkeypatch, tmp_path):
        monkeypatch.delenv("TEXTUAL_THEME", raising=False)
        monkeypatch.delenv("GTK_THEME", raising=False)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        assert resolve_theme() == "dracula"

    def test_custom_default(self, monkeypatch, tmp_path):
        monkeypatch.delenv("TEXTUAL_THEME", raising=False)
        monkeypatch.delenv("GTK_THEME", raising=False)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        assert resolve_theme(default="nord") == "nord"

    def test_nonexistent_xdg_config_home_fallback(self, monkeypatch, tmp_path):
        monkeypatch.delenv("TEXTUAL_THEME", raising=False)
        monkeypatch.delenv("GTK_THEME", raising=False)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "nonexistent"))
        assert resolve_theme() == "dracula"
