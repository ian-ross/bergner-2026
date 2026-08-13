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
inline constexpr char gauss_formulation_version[] = "explicit-stage-gauss-fixed-mesh-v1";
inline constexpr double formulation_parity_tolerance = 1.0e-11;
inline constexpr double formulation_parity_absolute_floor = 1.0e-13;
inline constexpr double directional_relative_tolerance = 1.0e-6;
inline constexpr int state_dimension = 3;
inline constexpr int maximum_stage_count = 3;

using scalar_type = double;
using local_ordinal_type = Tpetra::Map<>::local_ordinal_type;
using global_ordinal_type = Tpetra::Map<>::global_ordinal_type;
using node_type = Tpetra::Map<>::node_type;
using map_type = Tpetra::Map<local_ordinal_type, global_ordinal_type, node_type>;
using vector_type = Tpetra::Vector<scalar_type, local_ordinal_type, global_ordinal_type, node_type>;
using graph_type = Tpetra::CrsGraph<local_ordinal_type, global_ordinal_type, node_type>;
using matrix_type = Tpetra::CrsMatrix<scalar_type, local_ordinal_type, global_ordinal_type, node_type>;

struct CollocationRule {
  int stage_count = 1;
  int formal_order = 2;
  std::array<double, maximum_stage_count> nodes{};
  std::array<double, maximum_stage_count> quadrature_weights{};
  std::array<std::array<double, maximum_stage_count>, maximum_stage_count> stage_coefficients{};
  std::string family = "gauss-legendre";
};

template <std::size_t Stages>
inline CollocationRule make_rule() {
  static_assert(Stages >= 1 && Stages <= 3, "only one-, two-, and three-stage Gauss rules are frozen");
  CollocationRule rule;
  rule.stage_count = static_cast<int>(Stages);
  rule.formal_order = static_cast<int>(collocation::GaussLegendreRule<Stages>::formal_order);
  for (std::size_t j = 0; j < Stages; ++j) {
    rule.nodes[j] = collocation::GaussLegendreRule<Stages>::nodes[j];
    rule.quadrature_weights[j] = collocation::GaussLegendreRule<Stages>::quadrature_weights[j];
    for (std::size_t k = 0; k < Stages; ++k)
      rule.stage_coefficients[j][k] = collocation::GaussLegendreRule<Stages>::stage_coefficients[j][k];
  }
  return rule;
}

inline CollocationRule gauss_legendre_rule(int stages) {
  switch (stages) {
    case 1: return make_rule<1>();
    case 2: return make_rule<2>();
    case 3: return make_rule<3>();
    default: throw std::invalid_argument("Gauss stage count must be one, two, or three");
  }
}

class OrbitLayout {
 public:
  OrbitLayout(std::size_t interval_count, const Teuchos::RCP<const Teuchos::Comm<int>>& comm)
      : OrbitLayout(interval_count, 1, comm) {}
  OrbitLayout(std::size_t interval_count, int stage_count,
              const Teuchos::RCP<const Teuchos::Comm<int>>& comm)
      : interval_count_(interval_count), rule_(gauss_legendre_rule(stage_count)), comm_(comm) {
    if (interval_count_ < 2) throw std::invalid_argument("interval count must be at least two");
    if (comm_.is_null()) throw std::invalid_argument("OrbitLayout requires a communicator");
    if (comm_->getSize() != 1)
      throw std::invalid_argument("Gauss OrbitLayout currently requires a one-rank communicator");
    const auto size = static_cast<Tpetra::global_size_t>(unknown_size());
    domain_map_ = Teuchos::rcp(new map_type(size, 0, comm_));
    range_map_ = Teuchos::rcp(new map_type(size, 0, comm_));
    if (domain_map_->getLocalNumElements() != size || range_map_->getLocalNumElements() != size)
      throw std::runtime_error("serial OrbitLayout maps do not own every global index");
  }

  std::size_t interval_count() const { return interval_count_; }
  int stage_count() const { return rule_.stage_count; }
  int formal_order() const { return rule_.formal_order; }
  const CollocationRule& rule() const { return rule_; }
  global_ordinal_type endpoint_index(std::size_t interval, int component) const {
    check_interval(interval); check_component(component);
    return static_cast<global_ordinal_type>(state_dimension * interval + component);
  }
  global_ordinal_type cyclic_endpoint_index(std::size_t interval, int component) const {
    return endpoint_index(interval % interval_count_, component);
  }
  global_ordinal_type stage_index(std::size_t interval, int component) const {
    require_midpoint_compatibility("two-argument stage_index");
    return stage_index(interval, 0, component);
  }
  global_ordinal_type stage_index(std::size_t interval, int stage, int component) const {
    check_interval(interval); check_stage(stage); check_component(component);
    return static_cast<global_ordinal_type>(endpoint_size() +
        state_dimension * (interval * static_cast<std::size_t>(stage_count()) + static_cast<std::size_t>(stage)) + component);
  }
  global_ordinal_type log_period_index() const {
    return static_cast<global_ordinal_type>(endpoint_size() + stage_size());
  }
  global_ordinal_type stage_row(std::size_t interval, int component) const {
    require_midpoint_compatibility("two-argument stage_row");
    return stage_row(interval, 0, component);
  }
  global_ordinal_type stage_row(std::size_t interval, int stage, int component) const {
    check_interval(interval); check_stage(stage); check_component(component);
    return static_cast<global_ordinal_type>(state_dimension *
        (interval * static_cast<std::size_t>(stage_count()) + static_cast<std::size_t>(stage)) + component);
  }
  global_ordinal_type update_row(std::size_t interval, int component) const {
    check_interval(interval); check_component(component);
    return static_cast<global_ordinal_type>(stage_size() + state_dimension * interval + component);
  }
  global_ordinal_type phase_row() const { return log_period_index(); }
  std::size_t endpoint_size() const { return state_dimension * interval_count_; }
  std::size_t stage_size() const { return endpoint_size() * static_cast<std::size_t>(stage_count()); }
  std::size_t unknown_size() const { return endpoint_size() + stage_size() + 1; }
  const Teuchos::RCP<const map_type>& domain_map() const { return domain_map_; }
  const Teuchos::RCP<const map_type>& range_map() const { return range_map_; }

  local_ordinal_type owned_domain_local(global_ordinal_type gid) const {
    const auto lid = domain_map_->getLocalElement(gid);
    if (lid == Teuchos::OrdinalTraits<local_ordinal_type>::invalid())
      throw std::runtime_error("required domain index is not locally owned");
    return lid;
  }
  local_ordinal_type owned_range_local(global_ordinal_type gid) const {
    const auto lid = range_map_->getLocalElement(gid);
    if (lid == Teuchos::OrdinalTraits<local_ordinal_type>::invalid())
      throw std::runtime_error("required residual row is not locally owned");
    return lid;
  }

 private:
  void check_interval(std::size_t interval) const {
    if (interval >= interval_count_) throw std::out_of_range("interval index out of range");
  }
  void check_stage(int stage) const {
    if (stage < 0 || stage >= stage_count()) throw std::out_of_range("stage index out of range");
  }
  void require_midpoint_compatibility(const char* operation) const {
    if (stage_count() != 1)
      throw std::logic_error(std::string(operation) + " is valid only for one-stage midpoint layouts");
  }
  static void check_component(int component) {
    if (component < 0 || component >= state_dimension) throw std::out_of_range("component index out of range");
  }
  std::size_t interval_count_;
  CollocationRule rule_;
  Teuchos::RCP<const Teuchos::Comm<int>> comm_;
  Teuchos::RCP<const map_type> domain_map_;
  Teuchos::RCP<const map_type> range_map_;
};

struct PhaseReference {
  std::vector<double> boundaries;
  // Flattened interval-major/stage-major. For midpoint this retains the historical N-entry shape.
  std::vector<std::array<double, state_dimension>> stage_values;
  std::vector<std::array<double, state_dimension>> stage_derivatives;
  std::array<double, state_dimension> state_scaling{};
};

struct ResidualIdentifier {
  // Preserve the historical aggregate field order; stage is appended for
  // higher-order diagnostics without misbinding old three-field initializers.
  std::size_t interval = 0;
  int component = 0;
  double absolute_value = 0.0;
  int stage = 0;
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
    validate_reference(); compute_phase_energy(); build_graph();
  }

  const OrbitLayout& layout() const { return layout_; }
  const Environment& environment() const { return environment_; }
  const PhaseReference& phase_reference() const { return reference_; }
  double phase_energy() const { return phase_energy_; }
  const Teuchos::RCP<const graph_type>& graph() const { return graph_; }
  void set_environment(const Environment& environment) { validate_environment(environment); environment_ = environment; }

  Teuchos::RCP<vector_type> residual(const vector_type& unknowns) const {
    require_vector_map(unknowns, layout_.domain_map(), "unknown");
    const double period = physical_period(unknowns);
    auto result = Teuchos::rcp(new vector_type(layout_.range_map())); result->putScalar(0.0);
    double phase_numerator = 0.0;
    for (std::size_t interval = 0; interval < layout_.interval_count(); ++interval) {
      const double width = interval_width(interval);
      std::array<LocalDerivatives, maximum_stage_count> local{};
      for (int stage = 0; stage < layout_.stage_count(); ++stage)
        local[stage] = local_derivatives(stage_state(unknowns, interval, stage), environment_.T,
                                         std::log(environment_.w), environment_);
      for (int stage = 0; stage < layout_.stage_count(); ++stage) {
        for (int row = 0; row < state_dimension; ++row) {
          double weighted = 0.0;
          for (int coupled = 0; coupled < layout_.stage_count(); ++coupled)
            weighted += layout_.rule().stage_coefficients[stage][coupled] * local[coupled].values[row];
          const double scale = reference_.state_scaling[row];
          result->replaceGlobalValue(layout_.stage_row(interval, stage, row), scale *
              (value(unknowns, layout_.stage_index(interval, stage, row), true) -
               value(unknowns, layout_.endpoint_index(interval, row), true) - width * period * weighted));
          const auto ref_index = stage_reference_index(interval, stage);
          phase_numerator += width * layout_.rule().quadrature_weights[stage] * scale * scale *
              (value(unknowns, layout_.stage_index(interval, stage, row), true) - reference_.stage_values[ref_index][row]) *
              reference_.stage_derivatives[ref_index][row];
        }
      }
      for (int row = 0; row < state_dimension; ++row) {
        double weighted = 0.0;
        for (int stage = 0; stage < layout_.stage_count(); ++stage)
          weighted += layout_.rule().quadrature_weights[stage] * local[stage].values[row];
        const double scale = reference_.state_scaling[row];
        result->replaceGlobalValue(layout_.update_row(interval, row), scale *
            (value(unknowns, layout_.cyclic_endpoint_index(interval + 1, row), true) -
             value(unknowns, layout_.endpoint_index(interval, row), true) - width * period * weighted));
      }
    }
    result->replaceGlobalValue(layout_.phase_row(), phase_numerator / phase_energy_);
    return result;
  }

  Teuchos::RCP<matrix_type> create_jacobian() const { return Teuchos::rcp(new matrix_type(graph_)); }
  Teuchos::RCP<matrix_type> jacobian(const vector_type& unknowns) const {
    auto matrix = create_jacobian(); fill_jacobian(unknowns, *matrix); return matrix;
  }

  void fill_jacobian(const vector_type& unknowns, matrix_type& matrix) const {
    require_vector_map(unknowns, layout_.domain_map(), "unknown");
    if (matrix.getCrsGraph().getRawPtr() != graph_.getRawPtr())
      throw std::invalid_argument("Jacobian matrix does not use the retained Gauss graph");
    const double period = physical_period(unknowns);
    if (matrix.isFillComplete()) matrix.resumeFill();
    matrix.setAllToScalar(0.0);
    for (std::size_t interval = 0; interval < layout_.interval_count(); ++interval) {
      const double width = interval_width(interval);
      std::array<LocalDerivatives, maximum_stage_count> local{};
      for (int stage = 0; stage < layout_.stage_count(); ++stage)
        local[stage] = local_derivatives(stage_state(unknowns, interval, stage), environment_.T,
                                         std::log(environment_.w), environment_);
      for (int stage = 0; stage < layout_.stage_count(); ++stage) {
        for (int row = 0; row < state_dimension; ++row) {
          const double scale = reference_.state_scaling[row];
          std::vector<global_ordinal_type> columns{layout_.endpoint_index(interval, row)};
          std::vector<double> values{-scale};
          double log_period_value = 0.0;
          for (int coupled = 0; coupled < layout_.stage_count(); ++coupled) {
            const double coefficient = layout_.rule().stage_coefficients[stage][coupled];
            log_period_value -= scale * width * period * coefficient * local[coupled].values[row];
            for (int col = 0; col < state_dimension; ++col) {
              columns.push_back(layout_.stage_index(interval, coupled, col));
              values.push_back(scale * ((stage == coupled && row == col ? 1.0 : 0.0) -
                  width * period * coefficient * local[coupled].state_jacobian[row][col]));
            }
          }
          columns.push_back(layout_.log_period_index()); values.push_back(log_period_value);
          replace_row(matrix, layout_.stage_row(interval, stage, row), columns, values);
        }
      }
      for (int row = 0; row < state_dimension; ++row) {
        const double scale = reference_.state_scaling[row];
        std::vector<global_ordinal_type> columns{layout_.endpoint_index(interval, row),
          layout_.cyclic_endpoint_index(interval + 1, row)};
        std::vector<double> values{-scale, scale};
        double log_period_value = 0.0;
        for (int stage = 0; stage < layout_.stage_count(); ++stage) {
          const double weight = layout_.rule().quadrature_weights[stage];
          log_period_value -= scale * width * period * weight * local[stage].values[row];
          for (int col = 0; col < state_dimension; ++col) {
            columns.push_back(layout_.stage_index(interval, stage, col));
            values.push_back(-scale * width * period * weight * local[stage].state_jacobian[row][col]);
          }
        }
        columns.push_back(layout_.log_period_index()); values.push_back(log_period_value);
        replace_row(matrix, layout_.update_row(interval, row), columns, values);
      }
    }
    std::vector<global_ordinal_type> phase_columns;
    std::vector<double> phase_values;
    for (std::size_t interval = 0; interval < layout_.interval_count(); ++interval) {
      const double width = interval_width(interval);
      for (int stage = 0; stage < layout_.stage_count(); ++stage) {
        const auto ref_index = stage_reference_index(interval, stage);
        for (int component = 0; component < state_dimension; ++component) {
          const double scale = reference_.state_scaling[component];
          phase_columns.push_back(layout_.stage_index(interval, stage, component));
          phase_values.push_back(width * layout_.rule().quadrature_weights[stage] * scale * scale *
                                 reference_.stage_derivatives[ref_index][component] / phase_energy_);
        }
      }
    }
    replace_row(matrix, layout_.phase_row(), phase_columns, phase_values);
    matrix.fillComplete(layout_.domain_map(), layout_.range_map());
  }

  std::pair<Teuchos::RCP<vector_type>, Teuchos::RCP<vector_type>> parameter_columns(
      const vector_type& unknowns, double log_w_lower, double log_w_upper,
      double spine_log_w_temperature_derivative) const {
    require_vector_map(unknowns, layout_.domain_map(), "unknown");
    const double period = physical_period(unknowns);
    if (!std::isfinite(log_w_lower) || !std::isfinite(log_w_upper) || !(log_w_upper > log_w_lower) ||
        !std::isfinite(spine_log_w_temperature_derivative))
      throw std::invalid_argument("parameter-column controls must be finite with lower < upper");
    auto rho = Teuchos::rcp(new vector_type(layout_.range_map())); rho->putScalar(0.0);
    auto temperature_hat = Teuchos::rcp(new vector_type(layout_.range_map())); temperature_hat->putScalar(0.0);
    for (std::size_t interval = 0; interval < layout_.interval_count(); ++interval) {
      const double width = interval_width(interval);
      std::array<std::array<double, state_dimension>, maximum_stage_count> rho_local{}, temperature_local{};
      for (int stage = 0; stage < layout_.stage_count(); ++stage) {
        const auto local = local_derivatives(stage_state(unknowns, interval, stage), environment_.T,
                                             std::log(environment_.w), environment_);
        rho_local[stage] = rho_parameter_derivative(local, log_w_lower, log_w_upper);
        temperature_local[stage] = temperature_hat_parameter_derivative(local, spine_log_w_temperature_derivative);
      }
      for (int stage = 0; stage < layout_.stage_count(); ++stage) {
        for (int row = 0; row < state_dimension; ++row) {
          double rho_value = 0.0, temperature_value = 0.0;
          for (int coupled = 0; coupled < layout_.stage_count(); ++coupled) {
            rho_value += layout_.rule().stage_coefficients[stage][coupled] * rho_local[coupled][row];
            temperature_value += layout_.rule().stage_coefficients[stage][coupled] * temperature_local[coupled][row];
          }
          const double factor = -reference_.state_scaling[row] * width * period;
          rho->replaceGlobalValue(layout_.stage_row(interval, stage, row), factor * rho_value);
          temperature_hat->replaceGlobalValue(layout_.stage_row(interval, stage, row), factor * temperature_value);
        }
      }
      for (int row = 0; row < state_dimension; ++row) {
        double rho_value = 0.0, temperature_value = 0.0;
        for (int stage = 0; stage < layout_.stage_count(); ++stage) {
          rho_value += layout_.rule().quadrature_weights[stage] * rho_local[stage][row];
          temperature_value += layout_.rule().quadrature_weights[stage] * temperature_local[stage][row];
        }
        const double factor = -reference_.state_scaling[row] * width * period;
        rho->replaceGlobalValue(layout_.update_row(interval, row), factor * rho_value);
        temperature_hat->replaceGlobalValue(layout_.update_row(interval, row), factor * temperature_value);
      }
    }
    return {rho, temperature_hat};
  }

  Diagnostics diagnostics(const vector_type& residual_vector) const {
    require_vector_map(residual_vector, layout_.range_map(), "residual");
    Diagnostics out; out.phase_energy = phase_energy_; out.state_scaling = reference_.state_scaling;
    double stage_squared = 0.0, update_squared = 0.0;
    for (std::size_t interval = 0; interval < layout_.interval_count(); ++interval) {
      for (int stage = 0; stage < layout_.stage_count(); ++stage) {
        for (int component = 0; component < state_dimension; ++component) {
          const double item = value(residual_vector, layout_.stage_row(interval, stage, component), false);
          stage_squared += item * item;
          if (std::abs(item) > out.stage_max) {
            out.stage_max = std::abs(item);
            out.largest_stage.interval = interval;
            out.largest_stage.stage = stage;
            out.largest_stage.component = component;
            out.largest_stage.absolute_value = out.stage_max;
          }
        }
      }
      for (int component = 0; component < state_dimension; ++component) {
        const double item = value(residual_vector, layout_.update_row(interval, component), false);
        update_squared += item * item;
        if (std::abs(item) > out.update_max) {
          out.update_max = std::abs(item);
          out.largest_update.interval = interval;
          out.largest_update.component = component;
          out.largest_update.absolute_value = out.update_max;
          out.largest_update.stage = 0;
        }
      }
    }
    out.stage_rms = std::sqrt(stage_squared / static_cast<double>(state_dimension * layout_.interval_count() * layout_.stage_count()));
    out.update_rms = std::sqrt(update_squared / static_cast<double>(state_dimension * layout_.interval_count()));
    out.phase_abs = std::abs(value(residual_vector, layout_.phase_row(), false));
    return out;
  }

 private:
  static void require_vector_map(const vector_type& vector, const Teuchos::RCP<const map_type>& expected, const char* name) {
    if (!vector.getMap()->isSameAs(*expected)) throw std::invalid_argument(std::string(name) + " vector map mismatch");
  }
  double value(const vector_type& vector, global_ordinal_type gid, bool domain) const {
    const auto lid = domain ? layout_.owned_domain_local(gid) : layout_.owned_range_local(gid);
    return vector.getData(0)[static_cast<std::size_t>(lid)];
  }
  double interval_width(std::size_t interval) const { return reference_.boundaries[interval + 1] - reference_.boundaries[interval]; }
  std::size_t stage_reference_index(std::size_t interval, int stage) const {
    return interval * static_cast<std::size_t>(layout_.stage_count()) + static_cast<std::size_t>(stage);
  }
  double physical_period(const vector_type& unknowns) const {
    const double log_period = value(unknowns, layout_.log_period_index(), true);
    if (!std::isfinite(log_period)) throw std::invalid_argument("log-period must be finite");
    const double period = std::exp(log_period);
    if (!std::isfinite(period) || period <= 0.0) throw std::invalid_argument("period must be positive and finite");
    return period;
  }
  std::array<double, state_dimension> stage_state(const vector_type& unknowns, std::size_t interval, int stage) const {
    std::array<double, state_dimension> state{};
    for (int component = 0; component < state_dimension; ++component)
      state[component] = value(unknowns, layout_.stage_index(interval, stage, component), true);
    for (double component : state) if (!std::isfinite(component)) throw std::invalid_argument("stage state must be finite");
    return state;
  }
  static void replace_row(matrix_type& matrix, global_ordinal_type row,
                          const std::vector<global_ordinal_type>& columns, const std::vector<double>& values) {
    const auto replaced = matrix.replaceGlobalValues(row, Teuchos::arrayViewFromVector(columns), Teuchos::arrayViewFromVector(values));
    if (replaced != static_cast<local_ordinal_type>(columns.size()))
      throw std::runtime_error("fixed Gauss graph is missing an assembled entry");
  }
  void validate_reference() const {
    const std::size_t count = layout_.interval_count();
    const std::size_t stage_samples = count * static_cast<std::size_t>(layout_.stage_count());
    if (reference_.boundaries.size() != count + 1 || reference_.stage_values.size() != stage_samples ||
        reference_.stage_derivatives.size() != stage_samples)
      throw std::invalid_argument("phase-reference shape mismatch");
    if (reference_.boundaries.front() != 0.0 || reference_.boundaries.back() != 1.0)
      throw std::invalid_argument("mesh boundaries must span [0,1]");
    for (std::size_t i = 0; i < count; ++i)
      if (!std::isfinite(reference_.boundaries[i]) || !std::isfinite(reference_.boundaries[i + 1]) ||
          !(reference_.boundaries[i + 1] > reference_.boundaries[i]))
        throw std::invalid_argument("mesh boundaries must be finite with positive widths");
    for (std::size_t i = 0; i < stage_samples; ++i)
      for (int component = 0; component < state_dimension; ++component)
        if (!std::isfinite(reference_.stage_values[i][component]) || !std::isfinite(reference_.stage_derivatives[i][component]))
          throw std::invalid_argument("phase-reference samples must be finite");
    for (double scale : reference_.state_scaling)
      if (!std::isfinite(scale) || scale <= 0.0) throw std::invalid_argument("state scaling must be positive and finite");
    validate_environment(environment_);
  }
  static void validate_environment(const Environment& environment) {
    const std::array<double, 6> values{environment.p, environment.T, environment.w, environment.F, environment.N_a, environment.dz};
    for (double parameter : values)
      if (!std::isfinite(parameter) || parameter <= 0.0)
        throw std::invalid_argument("environment parameters must be positive and finite");
    if (environment.include_evaporation) throw std::invalid_argument("assembler requires the smooth no-evaporation environment");
  }
  void compute_phase_energy() {
    phase_energy_ = 0.0;
    for (std::size_t interval = 0; interval < layout_.interval_count(); ++interval) {
      const double width = interval_width(interval);
      for (int stage = 0; stage < layout_.stage_count(); ++stage) {
        const auto index = stage_reference_index(interval, stage);
        for (int component = 0; component < state_dimension; ++component) {
          const double scaled = reference_.state_scaling[component] * reference_.stage_derivatives[index][component];
          phase_energy_ += width * layout_.rule().quadrature_weights[stage] * scaled * scaled;
        }
      }
    }
    if (!std::isfinite(phase_energy_) || phase_energy_ <= 0.0)
      throw std::invalid_argument("phase energy must be positive and finite");
  }
  void build_graph() {
    const std::size_t stage_capacity = 2 + state_dimension * static_cast<std::size_t>(layout_.stage_count());
    const std::size_t update_capacity = 3 + state_dimension * static_cast<std::size_t>(layout_.stage_count());
    std::vector<std::size_t> row_capacity(layout_.unknown_size(), std::max(stage_capacity, update_capacity));
    row_capacity[static_cast<std::size_t>(layout_.phase_row())] = layout_.stage_size();
    auto graph = Teuchos::rcp(new graph_type(layout_.range_map(), Teuchos::arrayViewFromVector(row_capacity)));
    for (std::size_t interval = 0; interval < layout_.interval_count(); ++interval) {
      for (int stage = 0; stage < layout_.stage_count(); ++stage) {
        for (int row = 0; row < state_dimension; ++row) {
          std::vector<global_ordinal_type> columns{layout_.endpoint_index(interval, row)};
          for (int coupled = 0; coupled < layout_.stage_count(); ++coupled)
            for (int col = 0; col < state_dimension; ++col)
              columns.push_back(layout_.stage_index(interval, coupled, col));
          columns.push_back(layout_.log_period_index());
          graph->insertGlobalIndices(layout_.stage_row(interval, stage, row), Teuchos::arrayViewFromVector(columns));
        }
      }
      for (int row = 0; row < state_dimension; ++row) {
        std::vector<global_ordinal_type> columns{layout_.endpoint_index(interval, row), layout_.cyclic_endpoint_index(interval + 1, row)};
        for (int stage = 0; stage < layout_.stage_count(); ++stage)
          for (int col = 0; col < state_dimension; ++col)
            columns.push_back(layout_.stage_index(interval, stage, col));
        columns.push_back(layout_.log_period_index());
        graph->insertGlobalIndices(layout_.update_row(interval, row), Teuchos::arrayViewFromVector(columns));
      }
    }
    std::vector<global_ordinal_type> phase_columns;
    for (std::size_t interval = 0; interval < layout_.interval_count(); ++interval)
      for (int stage = 0; stage < layout_.stage_count(); ++stage)
        for (int component = 0; component < state_dimension; ++component)
          phase_columns.push_back(layout_.stage_index(interval, stage, component));
    graph->insertGlobalIndices(layout_.phase_row(), Teuchos::arrayViewFromVector(phase_columns));
    graph->fillComplete(layout_.domain_map(), layout_.range_map()); graph_ = graph;
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
  const auto map = vector.getMap(); std::vector<double> values(map->getGlobalNumElements());
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
