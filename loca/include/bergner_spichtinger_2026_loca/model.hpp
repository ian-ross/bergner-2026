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

template <typename Scalar>
struct ModelEnvironment {
  Scalar p;
  Scalar T;
  Scalar w;
  Scalar F;
  Scalar N_a;
  Scalar dz;
  bool include_evaporation;
};

template <typename Scalar>
ModelEnvironment<Scalar> promote_environment(const Environment& env) {
  return {Scalar(env.p), Scalar(env.T), Scalar(env.w), Scalar(env.F),
          Scalar(env.N_a), Scalar(env.dz), env.include_evaporation};
}

template <typename Scalar>
struct ModelCoefficients {
  Scalar rho;
  Scalar D;
  Scalar p_si;
  Scalar p1e;
  Scalar p2;
  Scalar A_n;
  Scalar A_q;
  Scalar A_s;
  Scalar B_q;
  Scalar B_s;
  Scalar C_n;
  Scalar C_q;
};

using Coefficients = ModelCoefficients<double>;

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

template <typename Scalar>
Scalar rho_air(const Scalar& p, const Scalar& T) {
  return p / (constants::R_d * T);
}

template <typename Scalar>
Scalar latent_heat(const Scalar& T) {
  using std::exp;
  return (constants::l0 + constants::l1 * T + constants::l2 * T * T +
          constants::l3 * exp(-((T / constants::T_l) * (T / constants::T_l)))) /
         constants::M_mol_v;
}

template <typename Scalar>
Scalar saturation_pressure_ice(const Scalar& T) {
  using std::exp;
  using std::log;
  return exp(constants::b0 + constants::b1 / T + constants::b2 * log(T) +
             constants::b3 * T);
}

template <typename Scalar>
Scalar vapor_diffusivity(const Scalar& T, const Scalar& p) {
  using std::pow;
  return constants::D_v0 * pow(T / constants::T0, 2.0) * (constants::p0 / p);
}

template <typename Scalar>
Scalar thermal_conductivity(const Scalar& T) {
  using std::pow;
  return (constants::a_K * pow(T, constants::b_K)) /
         (T + constants::T_K * pow(10.0, constants::c_K / T));
}

template <typename Scalar>
Scalar growth_factor(const Scalar& T, const Scalar& p) {
  const Scalar L = latent_heat(T);
  return 1.0 / ((((L / (constants::R_v * T)) - 1.0) * L * vapor_diffusivity(T, p) /
                 (T * thermal_conductivity(T))) +
                constants::R_v * T / saturation_pressure_ice(T));
}

template <typename Scalar>
Scalar cooling_coefficient(const Scalar& T) {
  const Scalar L = latent_heat(T);
  return ((L / (constants::c_p * constants::R_v * T * T)) -
          (1.0 / (constants::R_d * T))) *
         constants::g;
}

template <typename Scalar>
Scalar nucleation_p1e(const Scalar& T) {
  using std::log;
  return log(10.0) * (constants::p1_a0 + constants::p1_a1 * T);
}

template <typename Scalar>
Scalar nucleation_p2(const Scalar& T) {
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

template <typename Scalar>
Scalar fall_speed_correction(const Scalar& p, const Scalar& T) {
  using std::pow;
  return pow(p / constants::p_c, constants::a_c) * pow(T / constants::T_c, constants::b_c);
}

template <typename Scalar>
ModelCoefficients<Scalar> coefficients(const ModelEnvironment<Scalar>& env) {
  using std::pow;
  const Scalar rho = rho_air(env.p, env.T);
  const Scalar psi = saturation_pressure_ice(env.T);
  const Scalar A_n = (env.N_a / rho) * solution_droplet_volume() * constants::J0;
  const Scalar A_q = constants::m_nuc * A_n;
  const Scalar A_s = A_q * env.p / (constants::eps * psi);
  const Scalar B_q = 4.0 * 3.141592653589793238462643383279502884 *
                     growth_factor(env.T, env.p) * vapor_diffusivity(env.T, env.p) *
                     radius_mass_coefficient() * pow(constants::r0, -1.0 / 9.0);
  const Scalar B_s = B_q * env.p / (constants::eps * psi);
  const Scalar cf = fall_speed_correction(env.p, env.T);
  const Scalar C_n = cf * constants::a_sed * pow(constants::r0, -1.0 / 9.0) / env.dz;
  const Scalar C_q = cf * constants::a_sed * pow(constants::r0, 5.0 / 9.0) / env.dz;
  return {rho, cooling_coefficient(env.T), psi, nucleation_p1e(env.T), nucleation_p2(env.T),
          A_n, A_q, A_s, B_q, B_s, C_n, C_q};
}

inline Coefficients coefficients(const Environment& env) {
  return coefficients(promote_environment<double>(env));
}

template <typename Scalar>
std::array<Scalar, 3> physical_vector_field(const std::array<Scalar, 3>& physical_state,
                                            const ModelEnvironment<Scalar>& env) {
  using std::exp;
  using std::pow;
  const ModelCoefficients<Scalar> c = coefficients(env);

  const Scalar n = physical_state[0];       // ice number [kg_dry_air^-1]
  const Scalar q = physical_state[1];       // ice mass mixing ratio [kg kg_dry_air^-1]
  const Scalar s = physical_state[2];       // saturation ratio over ice [1]
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
  return {dn, dq, ds};
}

template <typename Scalar>
std::array<Scalar, 3> physical_vector_field(const std::array<Scalar, 3>& physical_state,
                                            const Environment& env) {
  return physical_vector_field(physical_state, promote_environment<Scalar>(env));
}

// Generalized transformed dynamics for a small local scalar type.  Temperature
// and log(w) are explicit scalar inputs so Sacado can differentiate every
// temperature-dependent coefficient and the physical control mapping w=exp(log_w).
template <typename Scalar>
std::array<Scalar, 3> transformed_vector_field(const std::array<Scalar, 3>& log_state,
                                               const Scalar& temperature,
                                               const Scalar& log_w,
                                               const Environment& base_env) {
  using std::exp;
  ModelEnvironment<Scalar> env = promote_environment<Scalar>(base_env);
  env.T = temperature;
  env.w = exp(log_w);
  const std::array<Scalar, 3> physical_state = {exp(log_state[0]), exp(log_state[1]),
                                                log_state[2]};
  const auto rhs = physical_vector_field(physical_state, env);
  // Transformed dynamics are [dn/dt / n, dq/dt / q, ds/dt].
  return {rhs[0] / physical_state[0], rhs[1] / physical_state[1], rhs[2]};
}

template <typename Scalar>
std::array<Scalar, 3> residual(const std::array<Scalar, 3>& log_state, double log_w,
                               const Environment& base_env) {
  return transformed_vector_field(log_state, Scalar(base_env.T), Scalar(log_w), base_env);
}

using Fad = Sacado::Fad::DFad<double>;

struct LocalDerivatives {
  std::array<double, 3> values{};
  std::array<std::array<double, 3>, 3> state_jacobian{};
  std::array<double, 3> temperature_derivative{};
  std::array<double, 3> log_w_derivative{};
};

// Differentiate one three-state model evaluation, never a packed orbit vector.
// Derivative slots are (log(n), log(q), s, T, log(w)).
inline LocalDerivatives local_derivatives(const std::array<double, 3>& x, double temperature,
                                          double log_w, const Environment& base_env) {
  if (base_env.include_evaporation) {
    throw std::invalid_argument(
        "local derivatives require the smooth no-evaporation model");
  }
  constexpr int derivative_count = 5;
  std::array<Fad, 3> ad_x = {Fad(derivative_count, 0, x[0]),
                             Fad(derivative_count, 1, x[1]),
                             Fad(derivative_count, 2, x[2])};
  const Fad ad_temperature(derivative_count, 3, temperature);
  const Fad ad_log_w(derivative_count, 4, log_w);
  const auto ad_g = transformed_vector_field(ad_x, ad_temperature, ad_log_w, base_env);

  LocalDerivatives result;
  for (int row = 0; row < 3; ++row) {
    result.values[row] = ad_g[row].val();
    for (int column = 0; column < 3; ++column) {
      result.state_jacobian[row][column] = ad_g[row].dx(column);
    }
    result.temperature_derivative[row] = ad_g[row].dx(3);
    result.log_w_derivative[row] = ad_g[row].dx(4);
  }
  return result;
}

inline std::array<double, 3> rho_parameter_derivative(
    const LocalDerivatives& local, double log_w_lower, double log_w_upper) {
  std::array<double, 3> result{};
  const double factor = 0.5 * (log_w_upper - log_w_lower);
  for (int row = 0; row < 3; ++row) result[row] = factor * local.log_w_derivative[row];
  return result;
}

inline std::array<double, 3> temperature_hat_parameter_derivative(
    const LocalDerivatives& local, double spine_log_w_temperature_derivative) {
  std::array<double, 3> result{};
  for (int row = 0; row < 3; ++row) {
    result[row] = 25.0 * (local.temperature_derivative[row] +
                          spine_log_w_temperature_derivative * local.log_w_derivative[row]);
  }
  return result;
}

inline std::array<double, 3> residual_values(const std::array<double, 3>& log_state,
                                             double log_w, const Environment& env) {
  return residual<double>(log_state, log_w, env);
}

inline std::array<double, 3> physical_vector_field_values(const std::array<double, 3>& physical_state,
                                                          const Environment& env) {
  return physical_vector_field<double>(physical_state, env);
}

inline std::array<std::array<double, 3>, 3> physical_jacobian(const std::array<double, 3>& physical_state,
                                                             const Environment& env) {
  std::array<Fad, 3> ad_y = {Fad(3, 0, physical_state[0]), Fad(3, 1, physical_state[1]),
                             Fad(3, 2, physical_state[2])};
  const auto ad_rhs = physical_vector_field<Fad>(ad_y, env);
  std::array<std::array<double, 3>, 3> J{};
  for (int i = 0; i < 3; ++i) {
    for (int j = 0; j < 3; ++j) {
      J[i][j] = ad_rhs[i].dx(j);
    }
  }
  return J;
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
