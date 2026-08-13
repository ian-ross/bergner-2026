#pragma once

#include "bergner_spichtinger_2026_loca/collocation_coefficients.hpp"
#include "bergner_spichtinger_2026_loca/model.hpp"

#include <Teuchos_Comm.hpp>
#include <Teuchos_OrdinalTraits.hpp>
#include <Teuchos_RCP.hpp>
#include <Tpetra_CrsGraph.hpp>
#include <Tpetra_CrsMatrix.hpp>
#include <Tpetra_Map.hpp>
#include <Tpetra_Vector.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace bs2026_loca {
namespace midpoint {

inline constexpr char formulation_version[] = "explicit-stage-midpoint-v1";
inline constexpr double formulation_parity_tolerance = 1.0e-11;
inline constexpr double formulation_parity_absolute_floor = 1.0e-13;
inline constexpr double directional_relative_tolerance = 1.0e-6;
inline constexpr int state_dimension = 3;

using scalar_type = double;
using local_ordinal_type = Tpetra::Map<>::local_ordinal_type;
using global_ordinal_type = Tpetra::Map<>::global_ordinal_type;
using node_type = Tpetra::Map<>::node_type;
using map_type = Tpetra::Map<local_ordinal_type, global_ordinal_type, node_type>;
using vector_type = Tpetra::Vector<scalar_type, local_ordinal_type, global_ordinal_type, node_type>;
using graph_type = Tpetra::CrsGraph<local_ordinal_type, global_ordinal_type, node_type>;
using matrix_type = Tpetra::CrsMatrix<scalar_type, local_ordinal_type, global_ordinal_type, node_type>;

class OrbitLayout {
 public:
  OrbitLayout(std::size_t interval_count, const Teuchos::RCP<const Teuchos::Comm<int>>& comm)
      : interval_count_(interval_count), comm_(comm) {
    if (interval_count_ < 2) throw std::invalid_argument("interval count must be at least two");
    if (comm_.is_null()) throw std::invalid_argument("OrbitLayout requires a communicator");
    if (comm_->getSize() != 1) {
      throw std::invalid_argument("midpoint OrbitLayout currently requires a one-rank communicator");
    }
    const auto size = static_cast<Tpetra::global_size_t>(unknown_size());
    domain_map_ = Teuchos::rcp(new map_type(size, 0, comm_));
    range_map_ = Teuchos::rcp(new map_type(size, 0, comm_));
    if (domain_map_->getLocalNumElements() != size || range_map_->getLocalNumElements() != size) {
      throw std::runtime_error("serial OrbitLayout maps do not own every global index");
    }
  }

  std::size_t interval_count() const { return interval_count_; }
  global_ordinal_type endpoint_index(std::size_t interval, int component) const {
    check_interval(interval); check_component(component);
    return static_cast<global_ordinal_type>(state_dimension * interval + component);
  }
  global_ordinal_type cyclic_endpoint_index(std::size_t interval, int component) const {
    return endpoint_index(interval % interval_count_, component);
  }
  global_ordinal_type stage_index(std::size_t interval, int component) const {
    check_interval(interval); check_component(component);
    return static_cast<global_ordinal_type>(endpoint_size() + state_dimension * interval + component);
  }
  global_ordinal_type log_period_index() const {
    return static_cast<global_ordinal_type>(2 * endpoint_size());
  }
  global_ordinal_type stage_row(std::size_t interval, int component) const {
    return endpoint_index(interval, component);
  }
  global_ordinal_type update_row(std::size_t interval, int component) const {
    check_interval(interval); check_component(component);
    return static_cast<global_ordinal_type>(endpoint_size() + state_dimension * interval + component);
  }
  global_ordinal_type phase_row() const { return log_period_index(); }
  std::size_t endpoint_size() const { return state_dimension * interval_count_; }
  std::size_t unknown_size() const { return 2 * endpoint_size() + 1; }
  const Teuchos::RCP<const map_type>& domain_map() const { return domain_map_; }
  const Teuchos::RCP<const map_type>& range_map() const { return range_map_; }

  local_ordinal_type owned_domain_local(global_ordinal_type gid) const {
    const auto lid = domain_map_->getLocalElement(gid);
    if (lid == Teuchos::OrdinalTraits<local_ordinal_type>::invalid()) {
      throw std::runtime_error("required domain index is not locally owned");
    }
    return lid;
  }
  local_ordinal_type owned_range_local(global_ordinal_type gid) const {
    const auto lid = range_map_->getLocalElement(gid);
    if (lid == Teuchos::OrdinalTraits<local_ordinal_type>::invalid()) {
      throw std::runtime_error("required residual row is not locally owned");
    }
    return lid;
  }

 private:
  void check_interval(std::size_t interval) const {
    if (interval >= interval_count_) throw std::out_of_range("interval index out of range");
  }
  static void check_component(int component) {
    if (component < 0 || component >= state_dimension) throw std::out_of_range("component index out of range");
  }
  std::size_t interval_count_;
  Teuchos::RCP<const Teuchos::Comm<int>> comm_;
  Teuchos::RCP<const map_type> domain_map_;
  Teuchos::RCP<const map_type> range_map_;
};

struct PhaseReference {
  std::vector<double> boundaries;
  std::vector<std::array<double, state_dimension>> stage_values;
  std::vector<std::array<double, state_dimension>> stage_derivatives;
  std::array<double, state_dimension> state_scaling{};
};

struct ResidualIdentifier {
  std::size_t interval = 0;
  int component = 0;
  double absolute_value = 0.0;
};

struct Diagnostics {
  double stage_max = 0.0;
  double stage_rms = 0.0;
  double update_max = 0.0;
  double update_rms = 0.0;
  double phase_abs = 0.0;
  double phase_energy = 0.0;
  std::array<double, state_dimension> state_scaling{};
  ResidualIdentifier largest_stage;
  ResidualIdentifier largest_update;
};

class Assembler {
 public:
  Assembler(OrbitLayout layout, const Environment& environment, PhaseReference reference)
      : layout_(std::move(layout)), environment_(environment), reference_(std::move(reference)) {
    validate_reference();
    compute_phase_energy();
    build_graph();
  }

  const OrbitLayout& layout() const { return layout_; }
  double phase_energy() const { return phase_energy_; }
  const Teuchos::RCP<const graph_type>& graph() const { return graph_; }

  Teuchos::RCP<vector_type> residual(const vector_type& unknowns) const {
    require_vector_map(unknowns, layout_.domain_map(), "unknown");
    const double period = physical_period(unknowns);
    auto result = Teuchos::rcp(new vector_type(layout_.range_map()));
    result->putScalar(0.0);
    double phase_numerator = 0.0;
    for (std::size_t interval = 0; interval < layout_.interval_count(); ++interval) {
      const double width = reference_.boundaries[interval + 1] - reference_.boundaries[interval];
      const auto x = stage_state(unknowns, interval);
      const auto local = local_derivatives(x, environment_.T, std::log(environment_.w), environment_);
      for (int row = 0; row < state_dimension; ++row) {
        const double endpoint = value(unknowns, layout_.endpoint_index(interval, row), true);
        const double next_endpoint = value(unknowns, layout_.cyclic_endpoint_index(interval + 1, row), true);
        const double stage = x[row];
        const double scale = reference_.state_scaling[row];
        result->replaceGlobalValue(layout_.stage_row(interval, row),
          scale * (stage - endpoint - 0.5 * width * period * local.values[row]));
        result->replaceGlobalValue(layout_.update_row(interval, row),
          scale * (next_endpoint - endpoint - width * period * local.values[row]));
        const double delta = stage - reference_.stage_values[interval][row];
        phase_numerator += width * delta * reference_.stage_derivatives[interval][row] * scale * scale;
      }
    }
    result->replaceGlobalValue(layout_.phase_row(), phase_numerator / phase_energy_);
    return result;
  }

  Teuchos::RCP<matrix_type> jacobian(const vector_type& unknowns) const {
    require_vector_map(unknowns, layout_.domain_map(), "unknown");
    const double period = physical_period(unknowns);
    auto matrix = Teuchos::rcp(new matrix_type(graph_));
    matrix->resumeFill();
    matrix->setAllToScalar(0.0);
    for (std::size_t interval = 0; interval < layout_.interval_count(); ++interval) {
      const double width = reference_.boundaries[interval + 1] - reference_.boundaries[interval];
      const auto local = local_derivatives(stage_state(unknowns, interval), environment_.T,
                                           std::log(environment_.w), environment_);
      for (int row = 0; row < state_dimension; ++row) {
        const double scale = reference_.state_scaling[row];
        std::vector<global_ordinal_type> stage_cols{layout_.endpoint_index(interval, row)};
        std::vector<double> stage_vals{-scale};
        for (int col = 0; col < state_dimension; ++col) {
          stage_cols.push_back(layout_.stage_index(interval, col));
          stage_vals.push_back(scale * ((row == col ? 1.0 : 0.0) - 0.5 * width * period * local.state_jacobian[row][col]));
        }
        stage_cols.push_back(layout_.log_period_index());
        stage_vals.push_back(-scale * 0.5 * width * period * local.values[row]);
        replace_row(*matrix, layout_.stage_row(interval, row), stage_cols, stage_vals);

        std::vector<global_ordinal_type> update_cols{layout_.endpoint_index(interval, row),
          layout_.cyclic_endpoint_index(interval + 1, row)};
        std::vector<double> update_vals{-scale, scale};
        for (int col = 0; col < state_dimension; ++col) {
          update_cols.push_back(layout_.stage_index(interval, col));
          update_vals.push_back(-scale * width * period * local.state_jacobian[row][col]);
        }
        update_cols.push_back(layout_.log_period_index());
        update_vals.push_back(-scale * width * period * local.values[row]);
        replace_row(*matrix, layout_.update_row(interval, row), update_cols, update_vals);
      }
    }
    std::vector<global_ordinal_type> phase_cols;
    std::vector<double> phase_vals;
    for (std::size_t interval = 0; interval < layout_.interval_count(); ++interval) {
      const double width = reference_.boundaries[interval + 1] - reference_.boundaries[interval];
      for (int component = 0; component < state_dimension; ++component) {
        phase_cols.push_back(layout_.stage_index(interval, component));
        const double scale = reference_.state_scaling[component];
        phase_vals.push_back(width * scale * scale * reference_.stage_derivatives[interval][component] / phase_energy_);
      }
    }
    replace_row(*matrix, layout_.phase_row(), phase_cols, phase_vals);
    matrix->fillComplete(layout_.domain_map(), layout_.range_map());
    return matrix;
  }

  std::pair<Teuchos::RCP<vector_type>, Teuchos::RCP<vector_type>> parameter_columns(
      const vector_type& unknowns, double log_w_lower, double log_w_upper,
      double spine_log_w_temperature_derivative) const {
    require_vector_map(unknowns, layout_.domain_map(), "unknown");
    const double period = physical_period(unknowns);
    if (!std::isfinite(log_w_lower) || !std::isfinite(log_w_upper) ||
        !(log_w_upper > log_w_lower) ||
        !std::isfinite(spine_log_w_temperature_derivative)) {
      throw std::invalid_argument("parameter-column controls must be finite with lower < upper");
    }
    auto rho = Teuchos::rcp(new vector_type(layout_.range_map()));
    auto temperature_hat = Teuchos::rcp(new vector_type(layout_.range_map()));
    rho->putScalar(0.0); temperature_hat->putScalar(0.0);
    for (std::size_t interval = 0; interval < layout_.interval_count(); ++interval) {
      const double width = reference_.boundaries[interval + 1] - reference_.boundaries[interval];
      const auto local = local_derivatives(stage_state(unknowns, interval), environment_.T,
                                           std::log(environment_.w), environment_);
      const auto rho_local = rho_parameter_derivative(local, log_w_lower, log_w_upper);
      const auto temperature_local = temperature_hat_parameter_derivative(local, spine_log_w_temperature_derivative);
      for (int row = 0; row < state_dimension; ++row) {
        const double factor = -reference_.state_scaling[row] * width * period;
        rho->replaceGlobalValue(layout_.stage_row(interval, row), 0.5 * factor * rho_local[row]);
        rho->replaceGlobalValue(layout_.update_row(interval, row), factor * rho_local[row]);
        temperature_hat->replaceGlobalValue(layout_.stage_row(interval, row), 0.5 * factor * temperature_local[row]);
        temperature_hat->replaceGlobalValue(layout_.update_row(interval, row), factor * temperature_local[row]);
      }
    }
    return {rho, temperature_hat};
  }

  Diagnostics diagnostics(const vector_type& residual_vector) const {
    require_vector_map(residual_vector, layout_.range_map(), "residual");
    Diagnostics out;
    out.phase_energy = phase_energy_;
    out.state_scaling = reference_.state_scaling;
    double stage_squared = 0.0, update_squared = 0.0;
    for (std::size_t interval = 0; interval < layout_.interval_count(); ++interval) {
      for (int component = 0; component < state_dimension; ++component) {
        const double stage_value = value(residual_vector, layout_.stage_row(interval, component), false);
        const double update_value = value(residual_vector, layout_.update_row(interval, component), false);
        stage_squared += stage_value * stage_value;
        update_squared += update_value * update_value;
        if (std::abs(stage_value) > out.stage_max) {
          out.stage_max = std::abs(stage_value); out.largest_stage = {interval, component, out.stage_max};
        }
        if (std::abs(update_value) > out.update_max) {
          out.update_max = std::abs(update_value); out.largest_update = {interval, component, out.update_max};
        }
      }
    }
    const double count = static_cast<double>(state_dimension * layout_.interval_count());
    out.stage_rms = std::sqrt(stage_squared / count);
    out.update_rms = std::sqrt(update_squared / count);
    out.phase_abs = std::abs(value(residual_vector, layout_.phase_row(), false));
    return out;
  }

 private:
  static void require_vector_map(const vector_type& vector, const Teuchos::RCP<const map_type>& expected,
                                 const char* name) {
    if (!vector.getMap()->isSameAs(*expected)) throw std::invalid_argument(std::string(name) + " vector map mismatch");
  }
  double value(const vector_type& vector, global_ordinal_type gid, bool domain) const {
    const auto lid = domain ? layout_.owned_domain_local(gid) : layout_.owned_range_local(gid);
    return vector.getData(0)[static_cast<std::size_t>(lid)];
  }
  double physical_period(const vector_type& unknowns) const {
    const double log_period = value(unknowns, layout_.log_period_index(), true);
    if (!std::isfinite(log_period)) {
      throw std::invalid_argument("log-period must be finite");
    }
    const double period = std::exp(log_period);
    if (!std::isfinite(period) || period <= 0.0) {
      throw std::invalid_argument("period must be positive and finite");
    }
    return period;
  }
  std::array<double, state_dimension> stage_state(const vector_type& unknowns, std::size_t interval) const {
    const std::array<double, state_dimension> state = {
        value(unknowns, layout_.stage_index(interval, 0), true),
        value(unknowns, layout_.stage_index(interval, 1), true),
        value(unknowns, layout_.stage_index(interval, 2), true)};
    for (double component : state) {
      if (!std::isfinite(component)) throw std::invalid_argument("stage state must be finite");
    }
    return state;
  }
  static void replace_row(matrix_type& matrix, global_ordinal_type row,
                          const std::vector<global_ordinal_type>& columns,
                          const std::vector<double>& values) {
    const auto replaced = matrix.replaceGlobalValues(row, Teuchos::arrayViewFromVector(columns),
                                                      Teuchos::arrayViewFromVector(values));
    if (replaced != static_cast<local_ordinal_type>(columns.size())) {
      throw std::runtime_error("fixed midpoint graph is missing an assembled entry");
    }
  }
  void validate_reference() const {
    const std::size_t count = layout_.interval_count();
    if (reference_.boundaries.size() != count + 1 || reference_.stage_values.size() != count ||
        reference_.stage_derivatives.size() != count) throw std::invalid_argument("phase-reference shape mismatch");
    if (reference_.boundaries.front() != 0.0 || reference_.boundaries.back() != 1.0)
      throw std::invalid_argument("mesh boundaries must span [0,1]");
    for (std::size_t i = 0; i < count; ++i) {
      if (!std::isfinite(reference_.boundaries[i]) ||
          !std::isfinite(reference_.boundaries[i + 1]) ||
          !(reference_.boundaries[i + 1] > reference_.boundaries[i])) {
        throw std::invalid_argument("mesh boundaries must be finite with positive widths");
      }
      for (int component = 0; component < state_dimension; ++component) {
        if (!std::isfinite(reference_.stage_values[i][component]) ||
            !std::isfinite(reference_.stage_derivatives[i][component])) {
          throw std::invalid_argument("phase-reference samples must be finite");
        }
      }
    }
    for (double scale : reference_.state_scaling) {
      if (!std::isfinite(scale) || scale <= 0.0) throw std::invalid_argument("state scaling must be positive and finite");
    }
    const std::array<double, 6> environment_values = {
        environment_.p, environment_.T, environment_.w,
        environment_.F, environment_.N_a, environment_.dz};
    for (double parameter : environment_values) {
      if (!std::isfinite(parameter) || parameter <= 0.0) {
        throw std::invalid_argument("environment parameters must be positive and finite");
      }
    }
    if (environment_.include_evaporation)
      throw std::invalid_argument("assembler requires the smooth no-evaporation environment");
  }
  void compute_phase_energy() {
    phase_energy_ = 0.0;
    for (std::size_t interval = 0; interval < layout_.interval_count(); ++interval) {
      const double width = reference_.boundaries[interval + 1] - reference_.boundaries[interval];
      for (int component = 0; component < state_dimension; ++component) {
        const double scaled = reference_.state_scaling[component] * reference_.stage_derivatives[interval][component];
        phase_energy_ += width * scaled * scaled;
      }
    }
    if (!std::isfinite(phase_energy_) || phase_energy_ <= 0.0)
      throw std::invalid_argument("phase energy must be positive and finite");
  }
  void build_graph() {
    std::vector<std::size_t> row_capacity(layout_.unknown_size(), 6);
    row_capacity[static_cast<std::size_t>(layout_.phase_row())] = layout_.endpoint_size();
    auto graph = Teuchos::rcp(new graph_type(layout_.range_map(),
        Teuchos::arrayViewFromVector(row_capacity)));
    for (std::size_t interval = 0; interval < layout_.interval_count(); ++interval) {
      for (int row = 0; row < state_dimension; ++row) {
        std::vector<global_ordinal_type> stage_cols{layout_.endpoint_index(interval, row)};
        for (int col = 0; col < state_dimension; ++col) stage_cols.push_back(layout_.stage_index(interval, col));
        stage_cols.push_back(layout_.log_period_index());
        graph->insertGlobalIndices(layout_.stage_row(interval, row), Teuchos::arrayViewFromVector(stage_cols));
        std::vector<global_ordinal_type> update_cols{layout_.endpoint_index(interval, row),
          layout_.cyclic_endpoint_index(interval + 1, row)};
        for (int col = 0; col < state_dimension; ++col) update_cols.push_back(layout_.stage_index(interval, col));
        update_cols.push_back(layout_.log_period_index());
        graph->insertGlobalIndices(layout_.update_row(interval, row), Teuchos::arrayViewFromVector(update_cols));
      }
    }
    std::vector<global_ordinal_type> phase_cols;
    for (std::size_t interval = 0; interval < layout_.interval_count(); ++interval)
      for (int component = 0; component < state_dimension; ++component)
        phase_cols.push_back(layout_.stage_index(interval, component));
    graph->insertGlobalIndices(layout_.phase_row(), Teuchos::arrayViewFromVector(phase_cols));
    graph->fillComplete(layout_.domain_map(), layout_.range_map());
    graph_ = graph;
  }

  OrbitLayout layout_;
  Environment environment_;
  PhaseReference reference_;
  double phase_energy_ = 0.0;
  Teuchos::RCP<const graph_type> graph_;
};

inline Teuchos::RCP<vector_type> make_vector(const OrbitLayout& layout, const std::vector<double>& values) {
  if (values.size() != layout.unknown_size()) throw std::invalid_argument("packed vector size mismatch");
  auto vector = Teuchos::rcp(new vector_type(layout.domain_map()));
  for (std::size_t gid = 0; gid < values.size(); ++gid)
    vector->replaceGlobalValue(static_cast<global_ordinal_type>(gid), values[gid]);
  return vector;
}

inline std::vector<double> copy_vector_by_global_id(const vector_type& vector) {
  const auto map = vector.getMap();
  std::vector<double> values(map->getGlobalNumElements());
  const auto data = vector.getData(0);
  for (global_ordinal_type gid = map->getMinAllGlobalIndex(); gid <= map->getMaxAllGlobalIndex(); ++gid) {
    const auto lid = map->getLocalElement(gid);
    if (lid == Teuchos::OrdinalTraits<local_ordinal_type>::invalid())
      throw std::runtime_error("copy_vector_by_global_id requires local ownership");
    values[static_cast<std::size_t>(gid)] = data[static_cast<std::size_t>(lid)];
  }
  return values;
}

}  // namespace midpoint
}  // namespace bs2026_loca
