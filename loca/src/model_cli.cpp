#include "bergner_spichtinger_2026_loca/model.hpp"

#include <cmath>
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
            << "  bs2026_loca_model continue log_n log_q s log_w_start --log-w-end value "
               "[--steps N] [--tol value] [--max-newton-iterations N] [same environment options]\n";
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
                            const Options& options) {
  if (!std::isfinite(options.log_w_end)) {
    throw std::invalid_argument("continue requires --log-w-end");
  }
  if (options.steps < 1) {
    throw std::invalid_argument("continue requires --steps >= 1");
  }

  std::cout << "backend_step_index,log_w,log_n,log_q,s,residual_norm,converged,newton_iterations,continuation_status,step_size,loca_continuation_mode\n";
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
    std::cout << i << "," << log_w << "," << current[0] << "," << current[1] << ","
              << current[2] << "," << corrected.residual_norm << ","
              << (corrected.converged ? "true" : "false") << "," << corrected.iterations
              << "," << (corrected.converged ? "converged" : "failed") << "," << step_size
              << ",natural_parameter_predictor_corrector\n";
  }
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc < 6) usage();
    const std::vector<std::string> args(argv + 1, argv + argc);
    const std::string command = args[0];
    if (command != "residual" && command != "jacobian" && command != "continue") usage();

    const std::array<double, 3> x = {parse_double(args[1]), parse_double(args[2]), parse_double(args[3])};
    const double log_w = parse_double(args[4]);
    const Options options = parse_options(args, 5);

    std::cout << std::setprecision(17) << std::scientific;
    if (command == "residual") {
      const auto r = bs2026_loca::residual_values(x, log_w, options.env);
      std::cout << r[0] << " " << r[1] << " " << r[2] << "\n";
    } else if (command == "jacobian") {
      const auto J = bs2026_loca::state_jacobian(x, log_w, options.env);
      for (const auto& row : J) {
        std::cout << row[0] << " " << row[1] << " " << row[2] << "\n";
      }
    } else {
      write_continuation_csv(x, log_w, options);
    }
    return 0;
  } catch (const std::exception& e) {
    std::cerr << "bs2026_loca_model: " << e.what() << "\n";
    return 2;
  }
}
