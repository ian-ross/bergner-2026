#pragma once

#include <Sacado.hpp>

#include <array>
#include <cmath>
#include <stdexcept>

namespace bs2026_loca {

template <typename Scalar>
double scalar_value(const Scalar& value) {
  return Sacado::ScalarValue<Scalar>::eval(value);
}

// Environment parameters are SI.  They mirror
// bergner_spichtinger_2026.constants.Environment and are independent of Python
// at runtime; log_w supplied by the CLI replaces w_m_s through exp(log_w).
struct Environment {
  double p = 30000.0;          // pressure [Pa]
  double T = 225.0;            // temperature [K]
  double w = 0.1;              // vertical velocity [m s^-1]
  double F = 1.0;              // sedimentation multiplier [1]
  double N_a = 3.0e8;          // aerosol number concentration [m^-3]
  double dz = 100.0;           // vertical box extent [m]
  bool include_evaporation = false;
};

struct Coefficients {
  double rho;
  double D;
  double p_si;
  double p1e;
  double p2;
  double A_n;
  double A_q;
  double A_s;
  double B_q;
  double B_s;
  double C_n;
  double C_q;
};

namespace constants {
constexpr double R_d = 287.058;
constexpr double R_v = 461.553;
constexpr double g = 9.81;
constexpr double c_p = 1004.0;
constexpr double eps = 0.622;
constexpr double M_mol_v = 18.01528e-3;
constexpr double l0 = 46782.5;
constexpr double l1 = 35.8925;
constexpr double l2 = -0.07414;
constexpr double l3 = 541.5;
constexpr double T_l = 123.75;
constexpr double b0 = 9.550426;
constexpr double b1 = -5723.265;
constexpr double b2 = 3.53068;
constexpr double b3 = -0.00728332;
constexpr double D_v0 = 2.1422e-5;
constexpr double T0 = 273.15;
constexpr double p0 = 101325.0;
constexpr double a_K = 0.002646;
constexpr double b_K = 1.5;
constexpr double T_K = 245.0;
constexpr double c_K = -12.0;
constexpr double rho_b = 810.0;
constexpr double r0 = 3.0;
constexpr double r_sol = 75e-9;
constexpr double sigma_r = 1.5;
constexpr double J0 = 1.0e16;
constexpr double m_nuc = 1.0e-16;
constexpr double p1_a0 = -50.4085;
constexpr double p1_a1 = 0.9368;
constexpr double p2_as2 = -1.36989e-5;
constexpr double p2_as1 = 0.00228;
constexpr double p2_as0 = 1.67469;
constexpr double p_c = 30000.0;
constexpr double T_c = 233.0;
constexpr double a_c = -0.178;
constexpr double b_c = -0.394;
constexpr double a_sed = 6.0e5;
}  // namespace constants

inline double rho_air(double p, double T) { return p / (constants::R_d * T); }

inline double latent_heat(double T) {
  using std::exp;
  return (constants::l0 + constants::l1 * T + constants::l2 * T * T +
          constants::l3 * exp(-((T / constants::T_l) * (T / constants::T_l)))) /
         constants::M_mol_v;
}

inline double saturation_pressure_ice(double T) {
  using std::exp;
  using std::log;
  return exp(constants::b0 + constants::b1 / T + constants::b2 * log(T) +
             constants::b3 * T);
}

inline double vapor_diffusivity(double T, double p) {
  using std::pow;
  return constants::D_v0 * pow(T / constants::T0, 2.0) * (constants::p0 / p);
}

inline double thermal_conductivity(double T) {
  using std::pow;
  return (constants::a_K * pow(T, constants::b_K)) /
         (T + constants::T_K * pow(10.0, constants::c_K / T));
}

inline double growth_factor(double T, double p) {
  const double L = latent_heat(T);
  return 1.0 / ((((L / (constants::R_v * T)) - 1.0) * L * vapor_diffusivity(T, p) /
                 (T * thermal_conductivity(T))) +
                constants::R_v * T / saturation_pressure_ice(T));
}

inline double cooling_coefficient(double T) {
  const double L = latent_heat(T);
  return ((L / (constants::c_p * constants::R_v * T * T)) -
          (1.0 / (constants::R_d * T))) *
         constants::g;
}

inline double nucleation_p1e(double T) {
  using std::log;
  return log(10.0) * (constants::p1_a0 + constants::p1_a1 * T);
}

inline double nucleation_p2(double T) {
  return constants::p2_as2 * T * T + constants::p2_as1 * T + constants::p2_as0;
}

inline double solution_droplet_volume() {
  constexpr double pi = 3.141592653589793238462643383279502884;
  using std::exp;
  using std::log;
  return (4.0 / 3.0) * pi * constants::r_sol * constants::r_sol * constants::r_sol *
         exp(4.5 * log(constants::sigma_r) * log(constants::sigma_r));
}

inline double radius_mass_coefficient() {
  constexpr double pi = 3.141592653589793238462643383279502884;
  using std::pow;
  return pow(3.0 / (4.0 * pi * constants::rho_b), 1.0 / 3.0);
}

inline double fall_speed_correction(double p, double T) {
  using std::pow;
  return pow(p / constants::p_c, constants::a_c) * pow(T / constants::T_c, constants::b_c);
}

inline Coefficients coefficients(const Environment& env) {
  using std::pow;
  const double rho = rho_air(env.p, env.T);
  const double psi = saturation_pressure_ice(env.T);
  const double A_n = (env.N_a / rho) * solution_droplet_volume() * constants::J0;
  const double A_q = constants::m_nuc * A_n;
  const double A_s = A_q * env.p / (constants::eps * psi);
  const double B_q = 4.0 * 3.141592653589793238462643383279502884 * growth_factor(env.T, env.p) *
                     vapor_diffusivity(env.T, env.p) * radius_mass_coefficient() *
                     pow(constants::r0, -1.0 / 9.0);
  const double B_s = B_q * env.p / (constants::eps * psi);
  const double cf = fall_speed_correction(env.p, env.T);
  const double C_n = cf * constants::a_sed * pow(constants::r0, -1.0 / 9.0) / env.dz;
  const double C_q = cf * constants::a_sed * pow(constants::r0, 5.0 / 9.0) / env.dz;
  return {rho, cooling_coefficient(env.T), psi, nucleation_p1e(env.T), nucleation_p2(env.T),
          A_n, A_q, A_s, B_q, B_s, C_n, C_q};
}

template <typename Scalar>
std::array<Scalar, 3> residual(const std::array<Scalar, 3>& log_state, double log_w,
                               const Environment& base_env) {
  using std::exp;
  using std::pow;
  Environment env = base_env;
  env.w = exp(log_w);
  const Coefficients c = coefficients(env);

  const Scalar n = exp(log_state[0]);       // ice number [kg_dry_air^-1]
  const Scalar q = exp(log_state[1]);       // ice mass mixing ratio [kg kg_dry_air^-1]
  const Scalar s = log_state[2];            // saturation ratio over ice [1]
  const Scalar expo = exp(c.p1e * (s - c.p2));

  // Eqs. (7)--(9)/(43)--(45): homogeneous nucleation source terms.
  const Scalar Nuc_n = c.A_n * expo;
  const Scalar Nuc_q = c.A_q * expo;
  const Scalar Nuc_s = -c.A_s * expo;
  // Eqs. (10)--(11)/(51)--(53): deposition growth, proportional to s-1.
  const Scalar Dep_q = c.B_q * pow(n, 2.0 / 3.0) * pow(q, 1.0 / 3.0) * (s - 1.0);
  const Scalar Dep_s = -c.B_s * pow(n, 2.0 / 3.0) * pow(q, 1.0 / 3.0) * (s - 1.0);
  // Eq. (12)/(54): optional ad-hoc evaporation switch, disabled by default as in Python.
  const Scalar Evap_n = (env.include_evaporation && scalar_value(s) < 1.0)
                            ? (n / q) * Dep_q
                            : Scalar(0.0);
  // Eqs. (13)--(15)/(69)--(70)/(38): sedimentation and vertical cooling.
  const Scalar Sed_n = -env.F * c.C_n * pow(n, 1.0 / 3.0) * pow(q, 2.0 / 3.0);
  const Scalar Sed_q = -env.F * c.C_q * pow(n, -2.0 / 3.0) * pow(q, 5.0 / 3.0);
  const Scalar Cool = c.D * env.w * s;

  const Scalar dn = Nuc_n + Evap_n + Sed_n;
  const Scalar dq = Nuc_q + Dep_q + Sed_q;
  const Scalar ds = Cool + Nuc_s + Dep_s;
  // Continuation residual uses log coordinates: [dn/dt / n, dq/dt / q, ds/dt].
  return {dn / n, dq / q, ds};
}

using Fad = Sacado::Fad::DFad<double>;

inline std::array<double, 3> residual_values(const std::array<double, 3>& log_state,
                                             double log_w, const Environment& env) {
  return residual<double>(log_state, log_w, env);
}

inline std::array<std::array<double, 3>, 3> state_jacobian(const std::array<double, 3>& x,
                                                           double log_w,
                                                           const Environment& env) {
  std::array<Fad, 3> ad_x = {Fad(3, 0, x[0]), Fad(3, 1, x[1]), Fad(3, 2, x[2])};
  const auto ad_r = residual<Fad>(ad_x, log_w, env);
  std::array<std::array<double, 3>, 3> J{};
  for (int i = 0; i < 3; ++i) {
    for (int j = 0; j < 3; ++j) {
      J[i][j] = ad_r[i].dx(j);
    }
  }
  return J;
}

}  // namespace bs2026_loca
