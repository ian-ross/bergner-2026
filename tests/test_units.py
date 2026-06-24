from bergner_spichtinger_2026.units import Q_, environment_quantity, vector_field_quantity


def test_quantity_wrapper_accepts_hpa_and_returns_rates():
    env = environment_quantity(p=Q_(300, "hectopascal"), T=Q_(225, "kelvin"), w=Q_(0.1, "m/s"), F=1.0)
    dn, dq, ds = vector_field_quantity(Q_(1e4, "1/kg"), Q_(1e-6, "dimensionless"), Q_(1.4, "dimensionless"), env)
    assert str(dn.units) == "1 / kilogram / second"
    assert str(dq.units) == "1 / second"
    assert str(ds.units) == "1 / second"
