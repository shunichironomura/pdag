# `pdag` — Parameter Directed Acyclic Graph

To watch the output diagram in real-time, you can use the `fswatch` and `xargs`. Make sure you have `fswatch` installed
 and run the following command in the root directory of the project:

```bach
fswatch ./examples/umbrella2.py | xargs -n1 -I{} uv run python {}
```
