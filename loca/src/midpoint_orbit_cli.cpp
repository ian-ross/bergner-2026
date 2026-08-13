#include "bergner_spichtinger_2026_loca/midpoint_nox.hpp"

#include <Teuchos_DefaultComm.hpp>
#include <Tpetra_Core.hpp>

#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using bs2026_loca::Environment;
using bs2026_loca::midpoint::Assembler;
using bs2026_loca::midpoint::OrbitLayout;
using bs2026_loca::midpoint::PhaseReference;
using bs2026_loca::midpoint::AcceptanceInputs;
using bs2026_loca::midpoint::SolveResult;
using bs2026_loca::midpoint::copy_vector_by_global_id;
using bs2026_loca::midpoint::make_vector;
using bs2026_loca::midpoint::matrix_type;
using bs2026_loca::midpoint::vector_type;

struct Fixture {
  std::string case_id;
  Environment environment;
  PhaseReference reference;
  std::vector<double> unknowns;
  double log_w_lower = std::log(0.01);
  double log_w_upper = std::log(0.25);
  double spine_derivative = 0.037;
};

Fixture read_fixture(const std::string& path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open fixture: " + path);
  Fixture fixture;
  std::string magic;
  std::size_t count = 0;
  input >> magic >> fixture.case_id >> count;
  if (magic != "BS2026_MIDPOINT_FIXTURE_V1" || count == 0) throw std::runtime_error("invalid fixture header");
  input >> fixture.environment.p >> fixture.environment.T >> fixture.environment.w
        >> fixture.environment.F >> fixture.environment.N_a >> fixture.environment.dz;
  fixture.environment.include_evaporation = false;
  input >> fixture.log_w_lower >> fixture.log_w_upper >> fixture.spine_derivative;
  for (double& scale : fixture.reference.state_scaling) input >> scale;
  fixture.reference.boundaries.resize(count + 1);
  fixture.reference.stage_values.resize(count);
  fixture.reference.stage_derivatives.resize(count);
  fixture.unknowns.resize(6 * count + 1);
  for (double& value : fixture.reference.boundaries) input >> value;
  for (auto& row : fixture.reference.stage_values) for (double& value : row) input >> value;
  for (auto& row : fixture.reference.stage_derivatives) for (double& value : row) input >> value;
  for (double& value : fixture.unknowns) input >> value;
  if (!input) throw std::runtime_error("truncated or malformed midpoint fixture");
  return fixture;
}

void write_vector(const std::string& label, const vector_type& vector) {
  const auto values = copy_vector_by_global_id(vector);
  std::cout << label << " " << values.size();
  for (double value : values) std::cout << " " << value;
  std::cout << "\n";
}

Teuchos::RCP<vector_type> shifted_vector(const OrbitLayout& layout,
                                         const vector_type& source,
                                         const vector_type& direction,
                                         double factor) {
  auto result = Teuchos::rcp(new vector_type(layout.domain_map()));
  const auto source_values = copy_vector_by_global_id(source);
  const auto direction_values = copy_vector_by_global_id(direction);
  for (std::size_t gid = 0; gid < source_values.size(); ++gid) {
    result->replaceGlobalValue(static_cast<long long>(gid),
                               source_values[gid] + factor * direction_values[gid]);
  }
  return result;
}

void write_solve_result(const SolveResult& result, const OrbitLayout& layout) {
  std::cout << std::setprecision(17) << std::scientific;
  std::cout << "solver " << bs2026_loca::midpoint::nox_solver_version << "\n";
  std::cout << "solver_constants "
            << bs2026_loca::midpoint::nox_norm_f_tolerance << " "
            << bs2026_loca::midpoint::nox_max_iterations << " "
            << bs2026_loca::midpoint::accepted_stage_update_tolerance << " "
            << bs2026_loca::midpoint::accepted_phase_tolerance << " "
            << bs2026_loca::midpoint::corrected_solution_parity_tolerance << "\n";
  std::cout << "thyra_system " << layout.unknown_size() << " " << layout.unknown_size()
            << " " << layout.log_period_index() << " " << layout.phase_row() << "\n";
  std::cout << "nox " << (result.nox_converged ? "converged" : "not_converged") << " "
            << result.nonlinear_iterations << " " << result.nox_residual_norm << "\n";
  std::cout << "linear " << result.linear.backend << " "
            << (result.linear.reported ? "reported" : "unreported") << " "
            << result.linear.symbolic_factorizations << " "
            << result.linear.numeric_factorizations << " " << result.linear.solves << " "
            << (result.linear.symbolic_complete ? "true" : "false") << " "
            << (result.linear.numeric_complete ? "true" : "false") << " "
            << (result.linear.solve_complete ? "true" : "false") << "\n";
  write_vector("solution", *result.unknowns);
  write_vector("final_residual", *result.residual);
  std::cout << "period " << result.period << "\n";
  std::cout << "diagnostics " << result.diagnostics.stage_max << " " << result.diagnostics.stage_rms << " "
            << result.diagnostics.update_max << " " << result.diagnostics.update_rms << " "
            << result.diagnostics.phase_abs << " " << result.diagnostics.phase_energy << "\n";
  std::cout << "positivity " << (result.physical_states_positive_finite ? "true" : "false") << " "
            << (result.period_positive_finite ? "true" : "false") << "\n";
  std::cout << "accepted " << (result.acceptance.accepted ? "true" : "false") << "\n";
  std::cout << "rejection_reasons " << result.acceptance.rejection_reasons.size();
  for (const auto& reason : result.acceptance.rejection_reasons) std::cout << " " << reason;
  std::cout << "\n";
}

void write_graph(const matrix_type& matrix, const OrbitLayout& layout) {
  std::cout << "graph " << matrix.getGlobalNumEntries() << " " << layout.unknown_size() << "\n";
  for (std::size_t row = 0; row < layout.unknown_size(); ++row) {
    const std::size_t entries = matrix.getNumEntriesInGlobalRow(static_cast<long long>(row));
    matrix_type::nonconst_global_inds_host_view_type columns("columns", entries);
    matrix_type::nonconst_values_host_view_type values("values", entries);
    std::size_t copied = 0;
    matrix.getGlobalRowCopy(static_cast<long long>(row), columns, values, copied);
    std::cout << "row " << row << " " << copied;
    for (std::size_t i = 0; i < copied; ++i) std::cout << " " << columns(i);
    std::cout << "\n";
  }
}

}  // namespace

int main(int argc, char** argv) {
  Tpetra::ScopeGuard scope(&argc, &argv);
  try {
    if (argc == 2 && std::string(argv[1]) == "guard-one-interval") {
      const auto comm = Teuchos::DefaultComm<int>::getComm();
      try {
        OrbitLayout invalid_layout(1, comm);
      } catch (const std::invalid_argument&) {
        std::cout << "one_interval_rejected true\n";
        return 0;
      }
      throw std::runtime_error("one-interval layout was not rejected");
    }
    const std::string command = argc > 1 ? argv[1] : "";
    const bool fixture_command = command == "inspect" || command == "evaluate" ||
        command == "solve" || command == "guard-nonfinite-reference" ||
        command == "guard-invalid-period";
    const bool valid_arity = (fixture_command && argc == 3) ||
        (command == "acceptance-guard" && argc == 4);
    if (!valid_arity) {
      std::cerr << "Usage: bs2026_midpoint_orbit inspect|evaluate|solve|guard-nonfinite-reference|guard-invalid-period fixture.txt\n"
                << "       bs2026_midpoint_orbit acceptance-guard block|phase|positivity|period|phase-energy|linear fixture.txt\n"
                << "       bs2026_midpoint_orbit guard-one-interval\n";
      return 2;
    }
    const std::string fixture_path = command == "acceptance-guard" ? argv[3] : argv[2];
    Fixture fixture = read_fixture(fixture_path);
    const auto comm = Teuchos::DefaultComm<int>::getComm();
    if (command == "guard-nonfinite-reference") {
      fixture.reference.stage_values[0][0] = std::numeric_limits<double>::quiet_NaN();
      try {
        Assembler invalid_assembler(OrbitLayout(fixture.reference.stage_values.size(), comm),
                                    fixture.environment, fixture.reference);
      } catch (const std::invalid_argument&) {
        std::cout << "nonfinite_reference_rejected true\n";
        return 0;
      }
      throw std::runtime_error("nonfinite phase reference was not rejected");
    }
    if (command == "guard-invalid-period") {
      fixture.unknowns.back() = std::numeric_limits<double>::infinity();
      Assembler guard_assembler(OrbitLayout(fixture.reference.stage_values.size(), comm),
                                fixture.environment, fixture.reference);
      auto invalid_unknowns = make_vector(guard_assembler.layout(), fixture.unknowns);
      try {
        guard_assembler.jacobian(*invalid_unknowns);
      } catch (const std::invalid_argument&) {
        std::cout << "invalid_period_rejected true\n";
        return 0;
      }
      throw std::runtime_error("invalid physical period was not rejected");
    }
    OrbitLayout layout(fixture.reference.stage_values.size(), comm);
    Assembler assembler(layout, fixture.environment, fixture.reference);
    auto unknowns = make_vector(layout, fixture.unknowns);
    if (command == "solve") {
      auto assembler_ptr = Teuchos::rcp(new Assembler(std::move(assembler)));
      write_solve_result(bs2026_loca::midpoint::solve_fixed_parameter(assembler_ptr, *unknowns), layout);
      return 0;
    }
    if (command == "acceptance-guard") {
      if (argc != 4) throw std::invalid_argument("acceptance-guard requires a failure class");
      AcceptanceInputs inputs;
      inputs.nox_converged = true;
      inputs.residual = assembler.diagnostics(*assembler.residual(*unknowns));
      inputs.physical_states_positive_finite = true;
      inputs.period_positive_finite = true;
      inputs.linear = {"KLU2", 1, 1, 1, true, true, true, true};
      const std::string failure = argv[2];
      if (failure == "block") inputs.residual.stage_max = 2.0e-9;
      else if (failure == "phase") inputs.residual.phase_abs = 2.0e-10;
      else if (failure == "positivity") inputs.physical_states_positive_finite = false;
      else if (failure == "period") inputs.period_positive_finite = false;
      else if (failure == "phase-energy") inputs.residual.phase_energy = 0.0;
      else if (failure == "linear") inputs.linear.solve_complete = false;
      else throw std::invalid_argument("unknown acceptance failure class: " + failure);
      const auto acceptance = bs2026_loca::midpoint::evaluate_acceptance(inputs);
      std::cout << "accepted " << (acceptance.accepted ? "true" : "false") << "\n";
      std::cout << "rejection_reasons " << acceptance.rejection_reasons.size();
      for (const auto& reason : acceptance.rejection_reasons) std::cout << " " << reason;
      std::cout << "\n";
      return 0;
    }
    auto residual = assembler.residual(*unknowns);
    auto jacobian = assembler.jacobian(*unknowns);
    auto second_jacobian = assembler.create_jacobian();
    assembler.fill_jacobian(*unknowns, *second_jacobian);
    assembler.fill_jacobian(*unknowns, *second_jacobian);
    const auto columns = assembler.parameter_columns(*unknowns, fixture.log_w_lower,
                                                     fixture.log_w_upper, fixture.spine_derivative);
    const auto diagnostics = assembler.diagnostics(*residual);

    std::cout << std::setprecision(17) << std::scientific;
    std::cout << "case " << fixture.case_id << "\n";
    std::cout << "constants " << bs2026_loca::midpoint::formulation_version << " "
              << bs2026_loca::midpoint::formulation_parity_tolerance << " "
              << bs2026_loca::midpoint::formulation_parity_absolute_floor << " "
              << bs2026_loca::midpoint::directional_relative_tolerance << "\n";
    std::cout << "layout " << layout.interval_count() << " " << layout.unknown_size() << " "
              << layout.endpoint_index(0, 0) << " " << layout.stage_index(0, 0) << " "
              << layout.log_period_index() << " " << layout.phase_row() << "\n";
    const bool graph_reused =
        jacobian->getCrsGraph().getRawPtr() == assembler.graph().getRawPtr() &&
        second_jacobian->getCrsGraph().getRawPtr() == assembler.graph().getRawPtr();
    std::cout << "graph_reused " << (graph_reused ? "true" : "false") << "\n";
    write_graph(*jacobian, layout);
    if (command == "evaluate") {
      write_vector("residual", *residual);
      auto direction = Teuchos::rcp(new vector_type(layout.domain_map()));
      for (std::size_t gid = 0; gid < layout.unknown_size(); ++gid) {
        direction->replaceGlobalValue(static_cast<long long>(gid), std::sin(static_cast<double>(gid) + 0.73));
      }
      direction->scale(1.0 / direction->norm2());
      auto jacobian_action = Teuchos::rcp(new vector_type(layout.range_map()));
      jacobian->apply(*direction, *jacobian_action);
      write_vector("jacobian_action", *jacobian_action);
      constexpr double epsilon = 2.0e-7;
      const auto plus_unknowns = shifted_vector(layout, *unknowns, *direction, epsilon);
      const auto minus_unknowns = shifted_vector(layout, *unknowns, *direction, -epsilon);
      const auto plus_residual = assembler.residual(*plus_unknowns);
      const auto minus_residual = assembler.residual(*minus_unknowns);
      auto centered_difference = Teuchos::rcp(new vector_type(layout.range_map()));
      centered_difference->update(1.0 / (2.0 * epsilon), *plus_residual,
                                  -1.0 / (2.0 * epsilon), *minus_residual, 0.0);
      write_vector("centered_difference", *centered_difference);
      write_vector("rho", *columns.first);
      write_vector("temperature_hat", *columns.second);
      std::cout << "diagnostics " << diagnostics.stage_max << " " << diagnostics.stage_rms << " "
                << diagnostics.update_max << " " << diagnostics.update_rms << " "
                << diagnostics.phase_abs << " " << diagnostics.phase_energy << " "
                << diagnostics.largest_stage.interval << " " << diagnostics.largest_stage.component << " "
                << diagnostics.largest_update.interval << " " << diagnostics.largest_update.component;
      for (double scale : diagnostics.state_scaling) std::cout << " " << scale;
      std::cout << "\n";
    } else if (command != "inspect") {
      throw std::invalid_argument("unknown command: " + command);
    }
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "bs2026_midpoint_orbit: " << error.what() << "\n";
    return 2;
  }
}
