"""Tests for diff panel building logic."""

from cheznav.widgets.diff import _build_diff_panels


def test_identical_files():
    content = "line1\nline2\nline3\n"
    left, right = _build_diff_panels(content, content)
    left_str = left.plain
    right_str = right.plain
    assert "   1  line1" in left_str
    assert "   1  line1" in right_str
    assert left_str == right_str


def test_added_line():
    old = "line1\nline2\n"
    new = "line1\nline2\nline3\n"
    _left, right = _build_diff_panels(old, new)
    right_str = right.plain
    assert "line3" in right_str


def test_removed_line():
    old = "line1\nline2\nline3\n"
    new = "line1\nline2\n"
    left, _right = _build_diff_panels(old, new)
    left_str = left.plain
    assert "line3" in left_str


def test_changed_line():
    old = "hello\n"
    new = "world\n"
    left, right = _build_diff_panels(old, new)
    assert "hello" in left.plain
    assert "world" in right.plain


def test_no_trailing_newline_warning():
    with_nl = "line1\nline2\n"
    without_nl = "line1\nline2"
    left, right = _build_diff_panels(with_nl, without_nl)
    assert "No newline" not in left.plain
    assert "No newline" in right.plain


def test_both_no_trailing_newline():
    content = "line1\nline2"
    left, right = _build_diff_panels(content, content)
    assert "No newline" in left.plain
    assert "No newline" in right.plain


def test_empty_files():
    left, right = _build_diff_panels("", "")
    assert left.plain.strip() == ""
    assert right.plain.strip() == ""


def test_line_numbers_sequential():
    content = "a\nb\nc\nd\ne\n"
    left, _ = _build_diff_panels(content, content)
    for i in range(1, 6):
        assert f"   {i}  " in left.plain


def test_mixed_changes_preserve_alignment():
    """Both sides should have the same number of lines (padded with blanks)."""
    old = "same\nremoved\nsame2\n"
    new = "same\nsame2\nadded\n"
    left, right = _build_diff_panels(old, new)
    left_lines = left.plain.rstrip("\n").split("\n")
    right_lines = right.plain.rstrip("\n").split("\n")
    assert len(left_lines) == len(right_lines)
