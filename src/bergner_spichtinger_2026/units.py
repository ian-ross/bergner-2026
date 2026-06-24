"""Pint-facing wrappers for the Bergner & Spichtinger (2026) core model."""

from __future__ import annotations

import pint

from .constants import Environment
from .core import vector_field

ureg = pint.UnitRegistry()
Q_ = ureg.Quantity


def environment_quantity(*, p, T, w, F: float, N_a=None, Δz=None, include_evaporation: bool = False) -> Environment:
    """Build an :class:`Environment` from Pint quantities.

    Canonical core units are Pa, K, m/s, m^-3, and m.
    """
    kwargs = {
        "p": p.to("pascal").magnitude,
        "T": T.to("kelvin").magnitude,
        "w": w.to("meter/second").magnitude,
        "F": float(F),
        "include_evaporation": include_evaporation,
    }
    if N_a is not None:
        kwargs["N_a"] = N_a.to("1/meter**3").magnitude
    if Δz is not None:
        kwargs["Δz"] = Δz.to("meter").magnitude
    return Environment(**kwargs)


def vector_field_quantity(n, q, s, env: Environment):
    """Evaluate RHS with Pint input quantities.

    ``n`` is expected as particles per kg dry air (dimension ``kg^-1``), ``q`` as
    dimensionless kg/kg dry air, and ``s`` dimensionless.
    """
    ydot = vector_field(
        n.to("1/kg").magnitude,
        q.to("dimensionless").magnitude,
        s.to("dimensionless").magnitude,
        env,
    )
    return (
        Q_(ydot[0], "1/kg/second"),
        Q_(ydot[1], "1/second"),
        Q_(ydot[2], "1/second"),
    )
