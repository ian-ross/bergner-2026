#include "bergner_spichtinger_2026_loca/model.hpp"
#include "bergner_spichtinger_2026_loca/nox_loca_backend.hpp"

#include <LOCA_GlobalData.H>
#include <LOCA_LAPACK_Group.H>
#include <NOX_LAPACK_Matrix.H>
#include <NOX_LAPACK_Vector.H>
#include <NOX_Solver_Factory.H>
#include <NOX_Solver_Generic.H>
#include <NOX_StatusTest_Combo.H>
#include <NOX_StatusTest_MaxIters.H>
#include <NOX_StatusTest_NormF.H>
#include <Teuchos_LAPACK.hpp>
#include <Teuchos_ParameterList.hpp>
#include <Teuchos_RCP.hpp>

#include <algorithm>
#include <cmath>
#include <complex>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using bs2026_loca::Environment;

struct Options {
  Environment env;
  double log_w_end = std::numeric_limits<double>::quiet_NaN();
  int steps = 80;
  int max_newton_iterations = 20;
  double tolerance = 1.0e-10;
};

[[noreturn]] void usage() {
  std::cerr << "Usage:\n"
            << "  bs2026_loca_model residual log_n log_q s log_w [--p Pa] [--T K] [--F value] "
               "[--N-a m^-3] [--dz m] [--include-evaporation]\n"
            << "  bs2026_loca_model jacobian log_n log_q s log_w [same options]\n"
            << "  bs2026_loca_model physical-rhs n q s w [same environment options]\n"
            << "  bs2026_loca_model physical-jacobian n q s w [same environment options]\n"
            << "  bs2026_loca_model eigenvalues n q s w [same environment options]\n"
            << "  bs2026_loca_model continue log_n log_q s log_w_start --log-w-end value "
               "[--steps N] [--tol value] [--max-newton-iterations N] [same environment options]\n"
            << "  bs2026_loca_model nox-loca-continue log_n log_q s log_w_start --log-w-end value "
               "[--steps N] [--tol value] [--max-newton-iterations N] [same environment options]\n"
            << "  bs2026_loca_model nox-loca-smoke log_n log_q s log_w [same environment options]\n";
  std::exit(2);
}

double parse_double(const std::string& text) {
  size_t used = 0;
  const double value = std::stod(text, &used);
  if (used != text.size()) {
    throw std::invalid_argument("not a pure floating-point value: " + text);
  }
  return value;
}

int parse_int(const std::string& text) {
  size_t used = 0;
  const int value = std::stoi(text, &used);
  if (used != text.size()) {
    throw std::invalid_argument("not a pure integer value: " + text);
  }
  return value;
}

Options parse_options(const std::vector<std::string>& args, size_t first) {
  Options options;
  for (size_t i = first; i < args.size(); ++i) {
    const std::string& flag = args[i];
    auto require_value = [&](const char* name) -> std::string {
      if (i + 1 >= args.size()) {
        throw std::invalid_argument(std::string("missing value for ") + name);
      }
      return args[++i];
    };
    if (flag == "--p") options.env.p = parse_double(require_value("--p"));
    else if (flag == "--T") options.env.T = parse_double(require_value("--T"));
    else if (flag == "--F") options.env.F = parse_double(require_value("--F"));
    else if (flag == "--N-a") options.env.N_a = parse_double(require_value("--N-a"));
    else if (flag == "--dz") options.env.dz = parse_double(require_value("--dz"));
    else if (flag == "--include-evaporation") options.env.include_evaporation = true;
    else if (flag == "--log-w-end") options.log_w_end = parse_double(require_value("--log-w-end"));
    else if (flag == "--steps") options.steps = parse_int(require_value("--steps"));
    else if (flag == "--max-newton-iterations") options.max_newton_iterations = parse_int(require_value("--max-newton-iterations"));
    else if (flag == "--tol") options.tolerance = parse_double(require_value("--tol"));
    else throw std::invalid_argument("unknown option: " + flag);
  }
  return options;
}

double norm2(const std::array<double, 3>& values) {
  return std::sqrt(values[0] * values[0] + values[1] * values[1] + values[2] * values[2]);
}

std::array<double, 3> solve_3x3(std::array<std::array<double, 3>, 3> A, std::array<double, 3> b) {
  for (int k = 0; k < 3; ++k) {
    int pivot = k;
    double pivot_abs = std::abs(A[k][k]);
    for (int i = k + 1; i < 3; ++i) {
      const double candidate = std::abs(A[i][k]);
      if (candidate > pivot_abs) {
        pivot = i;
        pivot_abs = candidate;
      }
    }
    if (pivot_abs == 0.0) {
      throw std::runtime_error("singular 3x3 Jacobian in continuation corrector");
    }
    if (pivot != k) {
      std::swap(A[pivot], A[k]);
      std::swap(b[pivot], b[k]);
    }
    for (int i = k + 1; i < 3; ++i) {
      const double factor = A[i][k] / A[k][k];
      A[i][k] = 0.0;
      for (int j = k + 1; j < 3; ++j) {
        A[i][j] -= factor * A[k][j];
      }
      b[i] -= factor * b[k];
    }
  }

  std::array<double, 3> x{};
  for (int i = 2; i >= 0; --i) {
    double sum = b[i];
    for (int j = i + 1; j < 3; ++j) {
      sum -= A[i][j] * x[j];
    }
    x[i] = sum / A[i][i];
  }
  return x;
}

struct Eigenvalue {
  double real;
  double imag;
};

struct EigenClassification {
  std::string regime;
  std::string stability;
};

std::array<Eigenvalue, 3> compute_physical_eigenvalues(const std::array<double, 3>& physical_state,
                                                       const Environment& env) {
  const auto J = bs2026_loca::physical_jacobian(physical_state, env);
  // Teuchos::LAPACK wraps the same GEEV routine as direct LAPACK dgeev; the wrapper
  // is preferred here so the executable stays within the Trilinos CMake contract.
  Teuchos::LAPACK<int, double> lapack;
  constexpr int n = 3;
  constexpr int lda = 3;
  double A[n * n]{};
  for (int row = 0; row < n; ++row) {
    for (int col = 0; col < n; ++col) {
      A[row + col * lda] = J[row][col];
    }
  }
  double wr[n]{};
  double wi[n]{};
  double vl[1]{};
  double vr[1]{};
  double work[128]{};
  int info = 0;
  lapack.GEEV('N', 'N', n, A, lda, wr, wi, vl, 1, vr, 1, work, 128, &info);
  if (info != 0) {
    throw std::runtime_error("Teuchos::LAPACK GEEV failed with info=" + std::to_string(info));
  }
  return {{{wr[0], wi[0]}, {wr[1], wi[1]}, {wr[2], wi[2]}}};
}

std::array<Eigenvalue, 3> canonical_eigenvalues(std::array<Eigenvalue, 3> values,
                                                double imag_tol = 1.0e-10) {
  for (auto& value : values) {
    if (std::abs(value.imag) <= imag_tol) value.imag = 0.0;
  }
  std::vector<int> complex_indices;
  for (int i = 0; i < 3; ++i) {
    if (std::abs(values[i].imag) > imag_tol) complex_indices.push_back(i);
  }
  if (complex_indices.size() >= 2) {
    std::sort(complex_indices.begin(), complex_indices.end(), [&](int a, int b) {
      return values[a].imag > values[b].imag;
    });
    int remaining = 0;
    for (; remaining < 3; ++remaining) {
      if (remaining != complex_indices[0] && remaining != complex_indices[1]) break;
    }
    return {{{values[complex_indices[0]].real, values[complex_indices[0]].imag},
             {values[complex_indices[1]].real, values[complex_indices[1]].imag},
             {values[remaining].real, values[remaining].imag}}};
  }
  std::sort(values.begin(), values.end(), [](const Eigenvalue& a, const Eigenvalue& b) {
    return a.real > b.real;
  });
  return values;
}

EigenClassification classify_eigenvalues(const std::array<Eigenvalue, 3>& canonical,
                                         double real_tol = 1.0e-10,
                                         double imag_tol = 1.0e-10) {
  const bool complex_pair = std::abs(canonical[0].imag) > imag_tol && std::abs(canonical[1].imag) > imag_tol;
  bool all_stable = true;
  bool any_unstable = false;
  for (const auto& value : canonical) {
    all_stable = all_stable && value.real < -real_tol;
    any_unstable = any_unstable || value.real > real_tol;
  }
  return {complex_pair ? "complex_pair" : "three_real", all_stable ? "stable" : (any_unstable ? "unstable" : "mixed")};
}

struct NewtonResult {
  std::array<double, 3> x;
  double residual_norm;
  bool converged;
  int iterations;
};

NewtonResult newton_correct(std::array<double, 3> x, double log_w, const Environment& env,
                            int max_iterations, double tolerance) {
  double residual_norm = std::numeric_limits<double>::infinity();
  int iteration = 0;
  for (; iteration <= max_iterations; ++iteration) {
    const auto residual = bs2026_loca::residual_values(x, log_w, env);
    residual_norm = norm2(residual);
    if (residual_norm <= tolerance) {
      return {x, residual_norm, true, iteration};
    }
    if (iteration == max_iterations) break;

    const auto jacobian = bs2026_loca::state_jacobian(x, log_w, env);
    const std::array<double, 3> rhs = {-residual[0], -residual[1], -residual[2]};
    const auto delta = solve_3x3(jacobian, rhs);

    double alpha = 1.0;
    bool accepted = false;
    for (int backtrack = 0; backtrack < 12; ++backtrack) {
      const std::array<double, 3> candidate = {x[0] + alpha * delta[0],
                                               x[1] + alpha * delta[1],
                                               x[2] + alpha * delta[2]};
      const double candidate_norm = norm2(bs2026_loca::residual_values(candidate, log_w, env));
      if (std::isfinite(candidate_norm) && candidate_norm < residual_norm) {
        x = candidate;
        accepted = true;
        break;
      }
      alpha *= 0.5;
    }
    if (!accepted) {
      x = {x[0] + delta[0], x[1] + delta[1], x[2] + delta[2]};
    }
  }
  return {x, residual_norm, false, iteration};
}

void write_continuation_csv(const std::array<double, 3>& x0, double log_w_start,
                            const Options& options,
                            const std::string& continuation_mode = "natural_parameter_predictor_corrector") {
  if (!std::isfinite(options.log_w_end)) {
    throw std::invalid_argument("continue requires --log-w-end");
  }
  if (options.steps < 1) {
    throw std::invalid_argument("continue requires --steps >= 1");
  }

  std::cout << "backend_step_index,log_w,log_n,log_q,s,residual_norm,converged,newton_iterations,continuation_status,step_size,loca_continuation_mode,lambda1_real,lambda1_imag,lambda2_real,lambda2_imag,lambda3_real,lambda3_imag,eigenvalue_regime,stability_classification,eigenvalue_source,jacobian_coordinate_system,physical_jacobian_11,physical_jacobian_12,physical_jacobian_13,physical_jacobian_21,physical_jacobian_22,physical_jacobian_23,physical_jacobian_31,physical_jacobian_32,physical_jacobian_33\n";
  std::array<double, 3> previous = x0;
  std::array<double, 3> current = x0;
  const double step_size = (options.log_w_end - log_w_start) / static_cast<double>(options.steps);
  for (int i = 0; i <= options.steps; ++i) {
    const double log_w = log_w_start + step_size * static_cast<double>(i);
    std::array<double, 3> predictor = current;
    if (i > 1) {
      predictor = {current[0] + (current[0] - previous[0]),
                   current[1] + (current[1] - previous[1]),
                   current[2] + (current[2] - previous[2])};
    }
    const auto corrected = newton_correct(predictor, log_w, options.env,
                                          options.max_newton_iterations, options.tolerance);
    previous = current;
    current = corrected.x;
    Environment point_env = options.env;
    point_env.w = std::exp(log_w);
    const std::array<double, 3> physical_state = {std::exp(current[0]), std::exp(current[1]), current[2]};
    const auto physical_J = bs2026_loca::physical_jacobian(physical_state, point_env);
    const auto eig = canonical_eigenvalues(compute_physical_eigenvalues(physical_state, point_env));
    const auto classification = classify_eigenvalues(eig);
    std::cout << i << "," << log_w << "," << current[0] << "," << current[1] << ","
              << current[2] << "," << corrected.residual_norm << ","
              << (corrected.converged ? "true" : "false") << "," << corrected.iterations
              << "," << (corrected.converged ? "converged" : "failed") << "," << step_size
              << "," << continuation_mode << "," << eig[0].real << "," << eig[0].imag
              << "," << eig[1].real << "," << eig[1].imag << "," << eig[2].real << ","
              << eig[2].imag << "," << classification.regime << "," << classification.stability
              << ",teuchos_lapack_geev,physical_ode_state";
    for (const auto& row : physical_J) {
      for (double value : row) std::cout << "," << value;
    }
    std::cout << "\n";
  }
}

struct NoxLocaSolveResult {
  std::array<double, 3> x;
  double residual_norm;
  bool converged;
  int iterations;
};

NoxLocaSolveResult solve_with_nox_loca(const std::array<double, 3>& initial_guess,
                                       double log_w,
                                       const Environment& base_env,
                                       int max_iterations,
                                       double tolerance,
                                       const Teuchos::RCP<LOCA::GlobalData>& global_data) {
  Environment env = base_env;
  env.w = std::exp(log_w);
  bs2026_loca::NoxLocaProblem problem(initial_guess, env);
  problem.setParameter("log_w", log_w);

  Teuchos::RCP<LOCA::LAPACK::Group> group = Teuchos::rcp(new LOCA::LAPACK::Group(global_data, problem));
  group->setParams(problem.parameters());
  group->setParam("log_w", log_w);
  NOX::LAPACK::Vector nox_initial(3);
  for (int i = 0; i < 3; ++i) nox_initial(i) = initial_guess[i];
  group->setX(nox_initial);

  Teuchos::RCP<NOX::StatusTest::NormF> norm_f =
      Teuchos::rcp(new NOX::StatusTest::NormF(tolerance, NOX::StatusTest::NormF::Unscaled));
  Teuchos::RCP<NOX::StatusTest::MaxIters> max_iters =
      Teuchos::rcp(new NOX::StatusTest::MaxIters(max_iterations));
  Teuchos::RCP<NOX::StatusTest::Combo> status =
      Teuchos::rcp(new NOX::StatusTest::Combo(NOX::StatusTest::Combo::OR, norm_f, max_iters));

  Teuchos::RCP<Teuchos::ParameterList> params = Teuchos::rcp(new Teuchos::ParameterList);
  params->set("Nonlinear Solver", "Line Search Based");
  params->sublist("Printing").set("Output Information", 0);
  params->sublist("Direction").set("Method", "Newton");
  params->sublist("Line Search").set("Method", "Full Step");

  Teuchos::RCP<NOX::Solver::Generic> solver = NOX::Solver::buildSolver(group, status, params);
  const NOX::StatusTest::StatusType solve_status = solver->solve();
  const auto& solution_vector = dynamic_cast<const NOX::LAPACK::Vector&>(solver->getSolutionGroup().getX());
  std::array<double, 3> x = {solution_vector(0), solution_vector(1), solution_vector(2)};
  const double residual_norm = norm2(bs2026_loca::residual_values(x, log_w, base_env));
  return {x, residual_norm, solve_status == NOX::StatusTest::Converged, solver->getNumIterations()};
}

void write_nox_loca_continuation_csv(const std::array<double, 3>& x0, double log_w_start,
                                     const Options& options) {
  if (!std::isfinite(options.log_w_end)) {
    throw std::invalid_argument("nox-loca-continue requires --log-w-end");
  }
  if (options.steps < 1) {
    throw std::invalid_argument("nox-loca-continue requires --steps >= 1");
  }

  Teuchos::RCP<Teuchos::ParameterList> loca_params = Teuchos::rcp(new Teuchos::ParameterList);
  Teuchos::RCP<LOCA::GlobalData> global_data = LOCA::createGlobalData(loca_params);

  std::cout << "backend_step_index,log_w,log_n,log_q,s,residual_norm,converged,newton_iterations,continuation_status,step_size,loca_continuation_mode,lambda1_real,lambda1_imag,lambda2_real,lambda2_imag,lambda3_real,lambda3_imag,eigenvalue_regime,stability_classification,eigenvalue_source,jacobian_coordinate_system,physical_jacobian_11,physical_jacobian_12,physical_jacobian_13,physical_jacobian_21,physical_jacobian_22,physical_jacobian_23,physical_jacobian_31,physical_jacobian_32,physical_jacobian_33\n";
  std::array<double, 3> previous = x0;
  std::array<double, 3> current = x0;
  const double step_size = (options.log_w_end - log_w_start) / static_cast<double>(options.steps);
  for (int i = 0; i <= options.steps; ++i) {
    const double log_w = log_w_start + step_size * static_cast<double>(i);
    std::array<double, 3> predictor = current;
    if (i > 1) {
      predictor = {current[0] + (current[0] - previous[0]),
                   current[1] + (current[1] - previous[1]),
                   current[2] + (current[2] - previous[2])};
    }
    const auto solved = solve_with_nox_loca(predictor, log_w, options.env,
                                            options.max_newton_iterations, options.tolerance,
                                            global_data);
    previous = current;
    current = solved.x;
    Environment point_env = options.env;
    point_env.w = std::exp(log_w);
    const std::array<double, 3> physical_state = {std::exp(current[0]), std::exp(current[1]), current[2]};
    const auto physical_J = bs2026_loca::physical_jacobian(physical_state, point_env);
    const auto eig = canonical_eigenvalues(compute_physical_eigenvalues(physical_state, point_env));
    const auto classification = classify_eigenvalues(eig);
    std::cout << i << "," << log_w << "," << current[0] << "," << current[1] << ","
              << current[2] << "," << solved.residual_norm << ","
              << (solved.converged ? "true" : "false") << "," << solved.iterations
              << "," << (solved.converged ? "converged" : "failed") << "," << step_size
              << ",nox_loca_lapack_group_nox_solver," << eig[0].real << "," << eig[0].imag
              << "," << eig[1].real << "," << eig[1].imag << "," << eig[2].real << ","
              << eig[2].imag << "," << classification.regime << "," << classification.stability
              << ",teuchos_lapack_geev,physical_ode_state";
    for (const auto& row : physical_J) {
      for (double value : row) std::cout << "," << value;
    }
    std::cout << "\n";
  }
  LOCA::destroyGlobalData(global_data);
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc < 6) usage();
    const std::vector<std::string> args(argv + 1, argv + argc);
    const std::string command = args[0];
    if (command != "residual" && command != "jacobian" && command != "physical-rhs" &&
        command != "physical-jacobian" && command != "eigenvalues" && command != "continue" &&
        command != "nox-loca-continue" && command != "nox-loca-smoke") {
      usage();
    }

    const std::array<double, 3> x = {parse_double(args[1]), parse_double(args[2]), parse_double(args[3])};
    const double control = parse_double(args[4]);
    Options options = parse_options(args, 5);

    std::cout << std::setprecision(17) << std::scientific;
    if (command == "residual") {
      const auto r = bs2026_loca::residual_values(x, control, options.env);
      std::cout << r[0] << " " << r[1] << " " << r[2] << "\n";
    } else if (command == "jacobian") {
      const auto J = bs2026_loca::state_jacobian(x, control, options.env);
      for (const auto& row : J) {
        std::cout << row[0] << " " << row[1] << " " << row[2] << "\n";
      }
    } else if (command == "physical-rhs") {
      options.env.w = control;
      const auto rhs = bs2026_loca::physical_vector_field_values(x, options.env);
      std::cout << rhs[0] << " " << rhs[1] << " " << rhs[2] << "\n";
    } else if (command == "physical-jacobian") {
      options.env.w = control;
      const auto J = bs2026_loca::physical_jacobian(x, options.env);
      for (const auto& row : J) {
        std::cout << row[0] << " " << row[1] << " " << row[2] << "\n";
      }
    } else if (command == "eigenvalues") {
      options.env.w = control;
      const auto eig = canonical_eigenvalues(compute_physical_eigenvalues(x, options.env));
      const auto classification = classify_eigenvalues(eig);
      std::cout << "eigen_index,eigenvalue_real,eigenvalue_imag,eigenvalue_regime,stability_classification,eigenvalue_source,jacobian_coordinate_system\n";
      for (int i = 0; i < 3; ++i) {
        std::cout << (i + 1) << "," << eig[i].real << "," << eig[i].imag << ","
                  << classification.regime << "," << classification.stability
                  << ",teuchos_lapack_geev,physical_ode_state\n";
      }
    } else if (command == "nox-loca-smoke") {
      bs2026_loca::NoxLocaProblem problem(x, options.env);
      problem.setParameter("log_w", control);
      NOX::LAPACK::Vector state(3);
      for (int i = 0; i < 3; ++i) state(i) = x[i];
      NOX::LAPACK::Vector residual(3);
      NOX::LAPACK::Matrix<double> jacobian(3, 3);
      if (!problem.computeF(residual, state) || !problem.computeJacobian(jacobian, state)) {
        throw std::runtime_error("NOX/LOCA residual or Jacobian callback failed");
      }
      std::cout << "backend,interface,state_dimension,continuation_parameter,residual_norm,jacobian_00\n"
                << "nox_loca,LOCA::LAPACK::Interface,3,log_w,"
                << norm2({residual(0), residual(1), residual(2)}) << "," << jacobian(0, 0) << "\n";
    } else if (command == "nox-loca-continue") {
      write_nox_loca_continuation_csv(x, control, options);
    } else {
      write_continuation_csv(x, control, options);
    }
    return 0;
  } catch (const std::exception& e) {
    std::cerr << "bs2026_loca_model: " << e.what() << "\n";
    return 2;
  }
}
