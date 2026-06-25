#include "bergner_spichtinger_2026_loca/model.hpp"

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using bs2026_loca::Environment;

[[noreturn]] void usage() {
  std::cerr << "Usage:\n"
            << "  bs2026_loca_model residual log_n log_q s log_w [--p Pa] [--T K] [--F value] "
               "[--N-a m^-3] [--dz m] [--include-evaporation]\n"
            << "  bs2026_loca_model jacobian log_n log_q s log_w [same options]\n";
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

Environment parse_options(const std::vector<std::string>& args, size_t first) {
  Environment env;
  for (size_t i = first; i < args.size(); ++i) {
    const std::string& flag = args[i];
    auto require_value = [&](const char* name) -> double {
      if (i + 1 >= args.size()) {
        throw std::invalid_argument(std::string("missing value for ") + name);
      }
      return parse_double(args[++i]);
    };
    if (flag == "--p") env.p = require_value("--p");
    else if (flag == "--T") env.T = require_value("--T");
    else if (flag == "--F") env.F = require_value("--F");
    else if (flag == "--N-a") env.N_a = require_value("--N-a");
    else if (flag == "--dz") env.dz = require_value("--dz");
    else if (flag == "--include-evaporation") env.include_evaporation = true;
    else throw std::invalid_argument("unknown option: " + flag);
  }
  return env;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc < 6) usage();
    const std::vector<std::string> args(argv + 1, argv + argc);
    const std::string command = args[0];
    if (command != "residual" && command != "jacobian") usage();

    const std::array<double, 3> x = {parse_double(args[1]), parse_double(args[2]), parse_double(args[3])};
    const double log_w = parse_double(args[4]);
    const Environment env = parse_options(args, 5);

    std::cout << std::setprecision(17) << std::scientific;
    if (command == "residual") {
      const auto r = bs2026_loca::residual_values(x, log_w, env);
      std::cout << r[0] << " " << r[1] << " " << r[2] << "\n";
    } else {
      const auto J = bs2026_loca::state_jacobian(x, log_w, env);
      for (const auto& row : J) {
        std::cout << row[0] << " " << row[1] << " " << row[2] << "\n";
      }
    }
    return 0;
  } catch (const std::exception& e) {
    std::cerr << "bs2026_loca_model: " << e.what() << "\n";
    return 2;
  }
}
