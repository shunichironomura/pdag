default:
  just --list

ruff:
  uv run -- ruff check

alias tc := typecheck

typecheck:
  uv run -- mypy .

test:
  PYTHONHASHSEED=0 uv run -- coverage run --source=./src/pdag -m pytest --import-mode importlib
  uv run -- coverage report -m
  uv run -- coverage xml -o ./coverage.xml

lint:
  -uv run -- ruff check
  -uv run -- mypy .
  -uv run -- lint-imports
  -uv run -- deptry .
