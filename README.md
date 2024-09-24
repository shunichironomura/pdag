# XLRM

This is a Python tool to help you make better decisions using the XLRM framework.

## Requirements list

### Requirements for variable nodes

- [ ] Users can define variables that are relevant to the decision-making process.
- [ ] Users can define a variable without specifying its type.

### Requirements for relationship edges

- [ ] Users can define relationships between variables that are relevant to the decision-making process.
- [ ] Users can define a relationship between variables that cannot be represented as a simple function. (Unknown relationships)

### Requirements for model evaluation

- [ ] Users can dynamically configure the variable node types.
- [ ] Users can configure the relationship boundaries.
- [ ] `xlrm` can analyze which variable/relationship to evaluate.

## Usage

### `xlrm.StaticModel`

```python
import xlrm

with xlrm.StaticModel() as model:
    # External variables (X)
    is_raining = xlrm.BooleanVariable("Is it raining?", type="X")
    # model.add_variable(is_raining)

    # Levers (L)
    will_take_umbrella = xlrm.BooleanVariable("Will I take an umbrella?", type="L")
    will_take_travel_umrella = xlrm.BooleanVariable("Will I take a travel umbrella?", type="L")

    # Performance metrics (M)
    wetness = xlrm.NumericVariable("Wetness", type="M", unit=None, lower_bound=0, upper_bound=1)
    convenience = xlrm.NumericVariable("Convenience", type="M", unit=None, lower_bound=0, upper_bound=1)

    # Relationships (R)
    @xlrm.relationship((is_raining, will_take_umbrella, will_take_travel_umbrella), wetness)
    def how_wet_will_i_get(is_raining, will_take_umbrella, will_take_travel_umbrella):
        if is_raining:
            if will_take_umbrella:
                return 0
            elif will_take_travel_umbrella:
                return 0.5
            else:
                return 1
        else:
            return 0

    # @xlrm.relationship((will_take_umbrella, will_take_travel_umbrella), convenience)
    def how_convenient_will_it_be(will_take_umbrella, will_take_travel_umbrella):
        if will_take_umbrella:
            return 0
        elif will_take_travel_umbrella:
            return 0.5
        else:
            return 0

    # The relationship function can be None. In that case, the relationship is marked as unknown.
    # model.add_relationship(how_convenient_will_it_be, (will_take_umbrella, will_take_travel_umbrella), convenience)

graph = model.as_graph()

print(f"Model is evaluatable: {model.is_evaluatable()}")

scenarios = model.generate_scenarios()
decisions = model.generate_decisions()

results = model.evaluate(scenarios, decisions)

print(results)
[
  Case(
    scenario={
      'Is it raining?': True,
    },
    decision={
      'Will I take an umbrella?': True,
      'Will I take a travel umbrella?': False,
    },
    results={
      'Wetness': 0,
      'Convenience': 0,
    }
  )
]
```

### `xlrm.DynamicModel`

In the dynamic model, the time dimension is added. So it's essentially a Markov Decision Process with no randomness.

The decision can be made at each time step based on the knowledge of the previous time steps.
