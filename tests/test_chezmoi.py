"""Tests for chezmoi module helpers."""

from cheznav.chezmoi import _parse_attributes


class TestParseAttributes:
    def test_plain_file(self):
        attrs = _parse_attributes("dot_gitconfig")
        assert not attrs["is_encrypted"]
        assert not attrs["is_private"]
        assert not attrs["is_executable"]
        assert not attrs["is_template"]

    def test_encrypted(self):
        attrs = _parse_attributes("encrypted_private_dot_ssh/encrypted_private_key")
        assert attrs["is_encrypted"]
        assert attrs["is_private"]

    def test_private(self):
        attrs = _parse_attributes("private_dot_config/something")
        assert attrs["is_private"]
        assert not attrs["is_encrypted"]

    def test_executable(self):
        attrs = _parse_attributes("executable_dot_local/bin/myscript")
        assert attrs["is_executable"]

    def test_template(self):
        attrs = _parse_attributes("dot_gitconfig.tmpl")
        assert attrs["is_template"]

    def test_not_template_without_suffix(self):
        attrs = _parse_attributes("dot_gitconfig")
        assert not attrs["is_template"]

    def test_combined_attributes(self):
        attrs = _parse_attributes("encrypted_private_dot_config/secret.tmpl")
        assert attrs["is_encrypted"]
        assert attrs["is_private"]
        assert attrs["is_template"]
        assert not attrs["is_executable"]
