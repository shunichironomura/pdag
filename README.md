# `pdag` — Parameter Directed Acyclic Graph

To watch the output diagram in real-time, you can use the `fswatch` and `xargs`. Make sure you have `fswatch` installed
 and run the following command in the root directory of the project:

```bach
fswatch ./examples/umbrella2.py | xargs -n1 -I{} uv run python {}
```

## Tests

Run test with:

```bash
dotenvx run -f .env.pytest -- uv run pytest -svv tests
```

This is to make tests deterministic by setting `PYTHONHASHSEED` to `0` in the `.env.pytest` file.
