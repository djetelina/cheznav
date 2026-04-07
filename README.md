<div align="center">

# cheznav

[![opentrend.dev reach](https://opentrend.dev/badge/djetelina/cheznav/reach.svg)](https://opentrend.dev/)
[![PyPI - Version](https://img.shields.io/pypi/v/cheznav)](https://pypi.org/project/cheznav/)
[![AUR - Version](https://img.shields.io/aur/version/cheznav)](https://aur.archlinux.org/packages/cheznav)
[![Homebrew](https://img.shields.io/github/v/release/djetelina/homebrew-tap?filter=cheznav-*&label=brew)](https://github.com/djetelina/homebrew-tap)
![PyPI - License](https://img.shields.io/pypi/l/cheznav)
![GitHub Repo stars](https://img.shields.io/github/stars/DJetelina/cheznav?style=flat&logo=github)

A TUI for [chezmoi](https://www.chezmoi.io/).

Dual-pane layout: local home directory on the left, chezmoi-managed files on the right.
Cross-tree highlighting keeps selection in sync between panes.

![Screenshot](https://github.com/djetelina/cheznav/blob/main/tests/__snapshots__/test_snapshots/test_managed_expand_dir.svg?raw=true)

</div>

Add, apply, diff, edit, forget, destroy, chattr, ignore — through context menus or direct keyboard shortcuts. Side-by-side diffs with accept left/right.

Supports encrypted files, templates, executables, symlinks, directories, externals, chezmoi config files, run scripts, and dry-run mode.

## Install

```bash
pipx install cheznav

# or with Homebrew
brew install djetelina/tap/cheznav

# or from AUR
yay -S cheznav
```

## Usage

```bash
cheznav            # normal
cheznav --dry-run  # pass -n to all chezmoi calls
```

<details>
<summary><strong>Controls</strong></summary>

### Navigation

| Key | Action |
|-----|--------|
| Left / Right | Switch panes |
| Up / Down | Move within tree |
| Space | Expand / collapse directory |
| Enter | Context menu (files), expand + context menu (directories) |
| `:` | Command palette |
| `?` | Help |
| `q` | Quit |
| Tab | Cycle focusable elements |

### Direct shortcuts (no menu needed)

| Key | Local pane | Managed pane | Diff view |
|-----|-----------|--------------|-----------|
| `a` | Add / Re-add | Apply | Accept left (keep disk) |
| `e` | Edit local | Edit source | |
| `d` | View diff | View diff | |
| `i` | Ignore | Ignore | |
| `x` | Forget | Forget | |
| `r` | | | Accept right (use chezmoi) |
| `v` | View file | View file | |

</details>

<details>
<summary><strong>Development</strong></summary>

```bash
just init    # install pre-commit hooks + sync deps
just test    # run tests
just run     # run cheznav
just check   # run pre-commit on all files
```

</details>
