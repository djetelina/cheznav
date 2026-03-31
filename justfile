set shell := ["bash", "-cu"]

init:
	uv run pre-commit install
	uv sync

test:
	uv run pytest

test-update:
	uv run pytest --snapshot-update

run:
	uv run cheznav

check:
	uv run pre-commit run --all-files
