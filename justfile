set shell := ["bash", "-cu"]

init:
	uv run prek install
	uv sync

test:
	uv run pytest

test-update:
	uv run pytest --snapshot-update

run:
	uv run cheznav

check:
	uv run prek run --all-files
