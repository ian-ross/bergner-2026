"""Constants and parameter definitions for Bergner & Spichtinger (2026).

All numeric values are SI unless stated otherwise. References are to
Bergner & Spichtinger (2026), "Ice clouds as nonlinear oscillators".
"""

from __future__ import annotations

from dataclasses import dataclass


# Appendix A, Eq. (A23); dry air and water-vapor gas constants.
R_d = 287.058  # J kg^-1 K^-1
R_v = 461.553  # J kg^-1 K^-1
# Appendix A, text below Eq. (A23).
g = 9.81  # m s^-2
# Specific heat at constant pressure for dry air; used in Eq. (15)/(30)/(38).
# The paper uses c_p without listing it in the extracted Appendix A constants.
c_p = 1004.0  # J kg^-1 K^-1

# Ratio of molar masses M_mol,v / M_mol,d, Sec. III.B / Eq. (45), (53).
ε = 0.622
M_mol_v = 18.01528e-3  # kg mol^-1, Eq. (A29)

# Appendix A, Eq. (A24)--(A28): latent heat of sublimation coefficients.
l0 = 46_782.5  # J mol^-1
l1 = 35.8925  # J mol^-1 K^-1
l2 = -0.07414  # J mol^-1 K^-2
l3 = 541.5  # J mol^-1
T_l = 123.75  # K

# Appendix A, Eq. (A30)--(A33): saturation vapor pressure over hexagonal ice.
b0 = 9.550426
b1 = -5723.265  # K
b2 = 3.53068
b3 = -0.00728332  # K^-1

# Appendix A, Eq. (47)--(49): vapor diffusivity.
D_v0 = 2.1422e-5  # m^2 s^-1
T0 = 273.15  # K
p0 = 101_325.0  # Pa

# Appendix A, Eq. (A34)--(A36): heat conduction of air.
a_K = 0.002646  # W m^-1 K^(1-b_K)
b_K = 1.5
T_K = 245.0  # K
c_K = -12.0  # K

# Sec. III.C / Eq. (31): bulk density of ice.
ρ_b = 810.0  # kg m^-3

# Sec. III.D / Eq. (36): fixed moment ratio for ice particle distribution.
r0 = 3.0

# Appendix A, Eq. (A15)--(A17): solution-droplet nucleation parameters.
r_sol = 75e-9  # m
σ_r = 1.5
N_a_typical = 3.0e8  # m^-3, 300 cm^-3; Appendix A2 typical upper-troposphere value.
N_a_figure1_high = 1.0e10  # m^-3, 10000 cm^-3; inferred Figure 1 reproduction value.
N_a_default = N_a_typical
J0 = 1.0e16  # m^-3 s^-1
m_nuc = 1.0e-16  # kg

# Appendix A, Eq. (A18)--(A22): homogeneous freezing fit.
p1_a0 = -50.4085
p1_a1 = 0.9368  # K^-1
p2_as2 = -1.36989e-5  # K^-2
p2_as1 = 0.00228  # K^-1
p2_as0 = 1.67469

# Sec. III.E.4, Eq. (55)--(59), (66)--(70): sedimentation.
p_c = 30_000.0  # Pa
T_c = 233.0  # K
a_c = -0.178
b_c = -0.394
a_sed = 6.0e5  # m s^-1 kg^(-2/3)
Δz_default = 100.0  # m


@dataclass(frozen=True)
class Environment:
    """Fixed environmental/model parameters for Eqs. (4)--(6).

    Attributes:
        p: pressure [Pa]
        T: temperature [K]
        w: vertical velocity [m s^-1]
        F: sedimentation parameter [1], 0 < F <= 1
        N_a: aerosol/solution-droplet number concentration per volume [m^-3]
        Δz: vertical box extent [m]
        include_evaporation: include the ad hoc Eq. (12)/(54) term for s <= 1
    """

    p: float
    T: float
    w: float
    F: float
    N_a: float = N_a_default
    Δz: float = Δz_default
    include_evaporation: bool = False
