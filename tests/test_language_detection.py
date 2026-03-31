"""Tests for file language detection and binary detection."""

from cheznav.utils import detect_language, is_binary, is_binary_content


class TestDetectLanguage:
    def test_python(self):
        assert detect_language("foo.py") == "python"

    def test_javascript(self):
        assert detect_language("app.js") == "javascript"

    def test_typescript(self):
        assert detect_language("app.ts") == "typescript"

    def test_yaml(self):
        assert detect_language("config.yaml") == "yaml"
        assert detect_language("config.yml") == "yaml"

    def test_toml(self):
        assert detect_language("pyproject.toml") == "toml"

    def test_shell(self):
        assert detect_language("script.sh") == "bash"

    def test_template_strips_tmpl(self):
        assert detect_language("config.toml.tmpl") == "toml"
        assert detect_language("script.sh.tmpl") == "bash"

    def test_dotfile_names(self):
        assert detect_language(".zshrc") == "bash"
        assert detect_language(".bashrc") == "bash"

    def test_makefile(self):
        assert detect_language("Makefile") == "make"

    def test_dockerfile(self):
        assert detect_language("Dockerfile") == "docker"

    def test_unknown(self):
        assert detect_language("README") is None

    def test_markdown(self):
        assert detect_language("README.md") == "markdown"

    def test_nested_tmpl(self):
        assert detect_language("deep.yaml.tmpl") == "yaml"


class TestIsBinary:
    def test_images(self):
        assert is_binary("photo.png")
        assert is_binary("photo.jpg")
        assert is_binary("icon.ico")

    def test_archives(self):
        assert is_binary("data.zip")
        assert is_binary("data.tar")
        assert is_binary("data.gz")

    def test_text_files_not_binary(self):
        assert not is_binary("readme.md")
        assert not is_binary("config.toml")
        assert not is_binary("script.sh")

    def test_case_insensitive(self):
        assert is_binary("IMAGE.PNG")
        assert is_binary("Photo.JPG")

    def test_compiled(self):
        assert is_binary("module.pyc")
        assert is_binary("lib.so")

    def test_no_extension(self):
        assert not is_binary("Makefile")


class TestIsBinaryContent:
    def test_null_bytes_detected(self, tmp_path):
        f = tmp_path / "cookie"
        f.write_bytes(b"header\x00\x01\x02binary")
        assert is_binary_content(f)

    def test_high_non_text_ratio(self, tmp_path):
        f = tmp_path / "pulse-cookie"
        f.write_bytes(bytes(range(0x80, 0x100)))
        assert is_binary_content(f)

    def test_text_file_not_binary(self, tmp_path):
        f = tmp_path / "readme"
        f.write_text("hello world\n")
        assert not is_binary_content(f)

    def test_nonexistent_file(self, tmp_path):
        assert not is_binary_content(tmp_path / "nope")

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty"
        f.write_bytes(b"")
        assert not is_binary_content(f)
