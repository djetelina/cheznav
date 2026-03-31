# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-02

### Added

- Dual-pane TUI: local home directory (left) and chezmoi-managed files (right)
- Cross-tree highlighting with auto-expand/collapse
- Context menus with keyboard shortcuts for all actions
- Side-by-side diff view with accept left/right
- Flag picker for `chezmoi add` (recursive, exact, encrypt, template, etc.)
- Attribute picker for `chezmoi chattr` (pre-filled from current state)
- Command palette: update, template data, doctor, dump-config
- Support for encrypted files, templates, executables, symlinks, directories
- Externals section with outdated count and apply
- Chezmoi config files and run scripts in managed pane
- Template preview via `execute-template`
- Dry-run mode (`--dry-run` / `-n`)
