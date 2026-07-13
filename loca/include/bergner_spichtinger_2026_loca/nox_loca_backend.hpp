#pragma once

#include "bergner_spichtinger_2026_loca/model.hpp"

#include <LOCA_LAPACK_Interface.H>
#include <LOCA_Parameter_Vector.H>
#include <NOX_LAPACK_Matrix.H>
#include <NOX_LAPACK_Vector.H>

#include <array>
#include <cmath>
#include <string>

namespace bs2026_loca {

// Minimal dense NOX/LOCA adapter for the validated 3-variable equilibrium
// residual.  The state vector is (log_n, log_q, s), and LOCA parameters are
// physical/environment controls.  log_w is the continuation parameter used by
// the Figure 1/2/3 workflows; T is exposed too so later two-parameter Hopf work
// can reuse the same interface without changing equations.
class NoxLocaProblem : public LOCA::LAPACK::Interface {
 public:
  NoxLocaProblem(const std::array<double, 3>& initial_log_state, const Environment& env)
      : initial_guess_(3), env_(env) {
    for (int i = 0; i < 3; ++i) initial_guess_(i) = initial_log_state[i];
    params_.addParameter("log_w", std::log(env_.w));
    params_.addParameter("T", env_.T);
    params_.addParameter("p", env_.p);
    params_.addParameter("F", env_.F);
    params_.addParameter("N_a", env_.N_a);
    params_.addParameter("dz", env_.dz);
  }

  const NOX::LAPACK::Vector& getInitialGuess() override { return initial_guess_; }

  bool computeF(NOX::LAPACK::Vector& rhs, const NOX::LAPACK::Vector& x) override {
    const auto values = residual_values(vector_to_array(x), current_log_w(), current_environment());
    for (int i = 0; i < 3; ++i) rhs(i) = values[i];
    return true;
  }

  bool computeJacobian(NOX::LAPACK::Matrix<double>& J, const NOX::LAPACK::Vector& x) override {
    const auto values = state_jacobian(vector_to_array(x), current_log_w(), current_environment());
    for (int row = 0; row < 3; ++row) {
      for (int col = 0; col < 3; ++col) J(row, col) = values[row][col];
    }
    return true;
  }

  void setParams(const LOCA::ParameterVector& p) override { params_ = p; }

  void setParameter(const std::string& name, double value) {
    if (params_.isParameter(name)) params_.setValue(name, value);
    else params_.addParameter(name, value);
  }

  double parameter(const std::string& name) const { return params_.getValue(name); }

  const LOCA::ParameterVector& parameters() const { return params_; }

  Environment current_environment() const {
    Environment env = env_;
    if (params_.isParameter("p")) env.p = params_.getValue("p");
    if (params_.isParameter("T")) env.T = params_.getValue("T");
    if (params_.isParameter("F")) env.F = params_.getValue("F");
    if (params_.isParameter("N_a")) env.N_a = params_.getValue("N_a");
    if (params_.isParameter("dz")) env.dz = params_.getValue("dz");
    env.w = std::exp(current_log_w());
    return env;
  }

  double current_log_w() const {
    return params_.isParameter("log_w") ? params_.getValue("log_w") : std::log(env_.w);
  }

  static std::array<double, 3> vector_to_array(const NOX::LAPACK::Vector& x) {
    return {x(0), x(1), x(2)};
  }

 private:
  NOX::LAPACK::Vector initial_guess_;
  Environment env_;
  LOCA::ParameterVector params_;
};

inline bool nox_loca_headers_available() { return true; }

}  // namespace bs2026_loca
