# mypy: disable-error-code="no-redef"
import marimo

__generated_with = "0.8.19"
app = marimo.App(width="medium")


@app.cell
def __():
    import xlrm

    return (xlrm,)


@app.cell(hide_code=True)
def __(mo):
    mo.md(r"""## Construct the static model""")
    return


@app.cell
def __(xlrm):
    model = xlrm.StaticModel()

    # External variables (X)
    is_raining = xlrm.BooleanVariable("Is it raining?", type="X")
    model.add_variable(is_raining)

    # Levers (L)
    will_take_umbrella = xlrm.BooleanVariable("Will I take an umbrella?", type="L")
    will_take_travel_umbrella = xlrm.BooleanVariable("Will I take a travel umbrella?", type="L")
    model.add_variable(will_take_umbrella)
    model.add_variable(will_take_travel_umbrella)

    # Performance metrics (M)
    wetness = xlrm.NumericVariable("Wetness", type="M", unit=None, lower_bound=0, upper_bound=1)
    convenience = xlrm.NumericVariable("Convenience", type="M", unit=None, lower_bound=0, upper_bound=1)
    model.add_variable(wetness)
    model.add_variable(convenience)

    # Relationships (R)
    # @xlrm.relationship((is_raining, will_take_umbrella, will_take_travel_umbrella), wetness)
    def how_wet_will_i_get(is_raining: bool, will_take_umbrella: bool, will_take_travel_umbrella: bool) -> float:
        if is_raining:
            if will_take_umbrella:
                return 0
            elif will_take_travel_umbrella:
                return 0.5
            else:
                return 1
        else:
            return 0

    model.add_relationship(how_wet_will_i_get, (is_raining, will_take_umbrella, will_take_travel_umbrella), wetness)

    # @xlrm.relationship((will_take_umbrella, will_take_travel_umbrella), convenience)
    def how_convenient_will_it_be(will_take_umbrella: bool, will_take_travel_umbrella: bool) -> float:
        convenience = 0.0

        if will_take_umbrella:
            convenience -= 1.0

        if will_take_travel_umbrella:
            convenience -= 0.5

        return convenience

    # The relationship function can be None. In that case, the relationship is marked as unknown.
    model.add_relationship(how_convenient_will_it_be, (will_take_umbrella, will_take_travel_umbrella), convenience)

    return (
        convenience,
        how_convenient_will_it_be,
        how_wet_will_i_get,
        is_raining,
        model,
        wetness,
        will_take_travel_umbrella,
        will_take_umbrella,
    )


@app.cell
def __(model):
    scenarios = model.sample_scenarios(size=10)
    print(f"Scenarios: {scenarios}")

    decisions = model.sample_decisions(size=10)
    print(f"Decisions: {decisions}")

    results = model.evaluate(scenarios, decisions)
    print(f"Results: {results}")

    return decisions, results, scenarios


@app.cell
def __(mo, results):
    import pandas as pd
    import numpy as np
    import altair as alt

    df = pd.DataFrame({variable.name: results[variable].flatten() for variable in results})

    df["Decision option"] = np.where(df["Will I take an umbrella?"], "Y", "N") + np.where(
        df["Will I take a travel umbrella?"], "y", "n"
    )

    chart = mo.ui.altair_chart(
        alt.Chart(df)
        .mark_point(size=400.0)
        .encode(
            x="Convenience",
            y="Wetness",
            color="Decision option",
        )
    )

    return alt, chart, df, np, pd


@app.cell
def __(chart, mo):
    mo.vstack([chart, mo.ui.table(chart.value)])
    return


@app.cell
def __():
    import marimo as mo

    return (mo,)


if __name__ == "__main__":
    app.run()
