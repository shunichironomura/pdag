default:
  just --list

ruff:
  uv run -- ruff check

alias tc := typecheck

# Type check with mypy and pyright
typecheck:
  -uv run -- mypy .
  -uv run -- pyright .

# Run pytest and generate coverage report
test:
  uv run -- coverage run --source=./src/pdag -m pytest --import-mode importlib
  uv run -- coverage report -m
  uv run -- coverage xml -o ./coverage.xml

# Lint the code with ruff, mypy, pyright, lint-imports, deptry, and pip-licenses
lint:
  -uv run -- ruff check
  -uv run -- mypy .
  -uv run -- pyright .
  -uv run -- lint-imports
  -uv run -- deptry .
  -just --justfile {{justfile()}} license

# Run pip-licenses against the dependencies
license:
  uv sync --quiet --frozen --no-dev --group license
  uv run --quiet --no-sync -- pip-licenses
  uv sync --quiet


docs-addr := "localhost:8000"
# Serve the documentation
serve-docs:
  uv run -- mkdocs serve --dev-addr {{docs-addr}}

# Build the documentation
build-docs:
  uv run -- mkdocs build
