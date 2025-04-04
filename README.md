# `pdag` — Parameter Directed Acyclic Graph

[![PyPI](https://img.shields.io/pypi/v/pdag)](https://pypi.org/project/pdag/)
![PyPI - License](https://img.shields.io/pypi/l/pdag)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pdag)
[![Test Status](https://github.com/shunichironomura/pdag/actions/workflows/test.yaml/badge.svg)](https://github.com/shunichironomura/pdag/actions)
[![codecov](https://codecov.io/gh/shunichironomura/pdag/graph/badge.svg?token=Hz2YE2769a)](https://codecov.io/gh/shunichironomura/pdag)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![PyPI - Downloads](https://img.shields.io/pypi/dm/pdag)

> [!WARNING]
> This package is under development.

`pdag` helps you create and execute a directed acyclic graph (DAG) of parameters and their relationships.
Its features include:

- You can define parameters and their dependencies with a Python's class-based syntax and annotations.
- You can import another model into your model, allowing you to create a hierarchy of models and reuse them.
- You can use the `pdag watch` command to watch the graph representation of your model while you are creating it.

## Installation

```bash
pip install pdag
```

or any package manager that supports Python packages.

## Usage

Here is a simple example of how to use `pdag` to create a model that squares a number:

```python
from typing import Annotated
import pdag

class SquareModel(pdag.Model):
    """Square model that squares a number."""

    # x is a real number parameter and is the input to the model
    x = pdag.RealParameter("x")

    # y is a real number parameter and is the output of the model
    y = pdag.RealParameter("y")

    # The relationship is defined as a static method
    # with the @pdag.relationship decorator
    @pdag.relationship
    @staticmethod
    def square(
      # The annotation `x.ref()` indicates that the value of `x` will be provided
      # as the value of the `x_arg` parameter when the model is executed.
      x_arg: Annotated[float, x.ref()],

      # The annotation `y.ref()` indicates that the return value of the method
      # will be assigned to the `y` parameter when the model is executed.
    ) -> Annotated[float, y.ref()]:
        return x_arg**2
```

This `SquareModel` is a static model with input `x` and output `y`.

To execute the model for a specific value of `x`, execute the following code:

```python
core_model = SquareModel.to_core_model()
exec_model = pdag.create_exec_model_from_core_model(core_model)
results = pdag.execute_exec_model(
  exec_model,
  inputs={
    # `()` indicates the root model, and `"x"` is the name of the parameter.
    pdag.StaticParameterId((), "x"): 2.0,
  },
)

print(results)
# {
#   StaticParameterId(model_path=(), name='x'): 2.0,
#   StaticParameterId(model_path=(), name='y'): 4.0,
# }
```
