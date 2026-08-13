#pragma once

#include "bergner_spichtinger_2026_loca/midpoint_nox.hpp"

#include <LOCA.H>
#include <LOCA_Parameter_Vector.H>
#include <LOCA_Stepper.H>
#include <LOCA_StatusTest_MaxIters.H>
#include <LOCA_Thyra.H>
#include <LOCA_Thyra_SaveDataStrategy.H>
#include <NOX_StatusTest_Combo.H>
#include <NOX_StatusTest_FiniteValue.H>
#include <NOX_StatusTest_MaxIters.H>
#include <NOX_StatusTest_NormF.H>
#include <NOX_Solver_Generic.H>
#include <Teuchos_DefaultComm.hpp>
#include <Thyra_DefaultSpmdVectorSpace.hpp>
#include <Thyra_DetachedMultiVectorView.hpp>
#include <Thyra_DetachedVectorView.hpp>
#include <Thyra_VectorStdOps.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <functional>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace bs2026_loca {
namespace midpoint {

inline constexpr char loca_continuation_version[] = "native-loca-midpoint-pseudo-arclength-v2";
inline constexpr char loca_metric_version[] = "endpoint-stage-half-weighted-l2-v1";
inline constexpr char loca_parity_version[] = "native-python-all-point-parity-v1";
inline constexpr double loca_period_relative_tolerance = 2.0e-7;
inline constexpr double loca_weighted_orbit_tolerance = 2.0e-7;
inline constexpr double bootstrap_minimum_coordinate_step = 1.0e-5;
inline constexpr int bootstrap_max_halvings = 12;

struct PhysicalCoordinates {
  double coordinate = 0.0;
  double temperature_hat = 0.0;
  double rho = 0.0;
  double temperature = 0.0;
  double log_w = 0.0;
};

class ContinuationPath {
 public:
  virtual ~ContinuationPath() = default;
  virtual const char* name() const = 0;
  virtual PhysicalCoordinates coordinates(double coordinate) const = 0;
  virtual double log_w_lower(double coordinate) const = 0;
  virtual double log_w_upper(double coordinate) const = 0;
  virtual double spine_log_w_temperature_derivative(double coordinate) const = 0;
};

class FixedTemperatureRhoPath final : public ContinuationPath {
 public:
  FixedTemperatureRhoPath(double temperature, double lower, double upper)
      : temperature_(temperature), lower_(lower), upper_(upper) {
    if (!(std::isfinite(temperature_) && std::isfinite(lower_) && std::isfinite(upper_) && lower_ < upper_))
      throw std::invalid_argument("invalid fixed-temperature rho path");
  }
  const char* name() const override { return "rho"; }
  PhysicalCoordinates coordinates(double rho) const override {
    const double log_w = 0.5 * (lower_ + upper_) + 0.5 * rho * (upper_ - lower_);
    return {rho, (temperature_ - 215.0) / 25.0, rho, temperature_, log_w};
  }
  double log_w_lower(double) const override { return lower_; }
  double log_w_upper(double) const override { return upper_; }
  double spine_log_w_temperature_derivative(double) const override { return 0.0; }
 private:
  double temperature_, lower_, upper_;
};

class SpineTemperaturePath final : public ContinuationPath {
 public:
  using ScalarFunction = std::function<double(double)>;
  SpineTemperaturePath(ScalarFunction lower, ScalarFunction upper, ScalarFunction derivative)
      : lower_(std::move(lower)), upper_(std::move(upper)), derivative_(std::move(derivative)) {}
  const char* name() const override { return "temperature_hat"; }
  PhysicalCoordinates coordinates(double temperature_hat) const override {
    const double temperature = 215.0 + 25.0 * temperature_hat;
    const double lower = lower_(temperature), upper = upper_(temperature);
    return {temperature_hat, temperature_hat, 0.0, temperature, 0.5 * (lower + upper)};
  }
  double log_w_lower(double coordinate) const override { return lower_(215.0 + 25.0 * coordinate); }
  double log_w_upper(double coordinate) const override { return upper_(215.0 + 25.0 * coordinate); }
  double spine_log_w_temperature_derivative(double coordinate) const override {
    return derivative_(215.0 + 25.0 * coordinate);
  }
 private:
  ScalarFunction lower_, upper_, derivative_;
};

inline Environment environment_on_path(const Environment& base, const ContinuationPath& path,
                                       double coordinate) {
  const auto physical = path.coordinates(coordinate);
  Environment result = base;
  result.T = physical.temperature;
  result.w = std::exp(physical.log_w);
  if (!(std::isfinite(result.T) && result.T > 0.0 && std::isfinite(result.w) && result.w > 0.0))
    throw std::invalid_argument("invalid path environment at coordinate " + std::to_string(coordinate));
  return result;
}

class ContinuationModelEvaluator final : public Thyra::StateFuncModelEvaluatorBase<double> {
 public:
  ContinuationModelEvaluator(Teuchos::RCP<Assembler> assembler,
                             std::shared_ptr<const ContinuationPath> path,
                             double initial_coordinate,
                             const vector_type& nominal_unknowns)
      : assembler_(std::move(assembler)), path_(std::move(path)),
        base_environment_(assembler_->environment()),
        x_space_(Thyra::createVectorSpace<double>(assembler_->layout().domain_map())),
        f_space_(Thyra::createVectorSpace<double>(assembler_->layout().range_map())),
        p_space_(Thyra::locallyReplicatedDefaultSpmdVectorSpace<double>(
            Teuchos::DefaultComm<Teuchos::Ordinal>::getComm(), 1)),
        nominal_x_(Thyra::createVector(Teuchos::rcp(new vector_type(nominal_unknowns)), x_space_)),
        nominal_p_(Thyra::createMember(p_space_)),
        lows_factory_(Teuchos::rcp(new Thyra::Amesos2LinearOpWithSolveFactory<double>(
            Thyra::Amesos2::KLU2, Thyra::Amesos2::REPIVOT_ON_REFACTORIZATION))) {
    lows_factory_->setParameterList(Teuchos::rcp(new Teuchos::ParameterList("Amesos2")));
    if (assembler_.is_null() || !path_) throw std::invalid_argument("continuation model requires assembler and path");
    { Thyra::DetachedVectorView<double> value(*nominal_p_); value[0] = initial_coordinate; }
    Thyra::ModelEvaluatorBase::InArgsSetup<double> in;
    in.setModelEvalDescription(description()); in.setSupports(Thyra::ModelEvaluatorBase::IN_ARG_x);
    in.set_Np(1); prototype_in_ = in;
    Thyra::ModelEvaluatorBase::OutArgsSetup<double> out;
    out.setModelEvalDescription(description()); out.set_Np_Ng(1, 0);
    out.setSupports(Thyra::ModelEvaluatorBase::OUT_ARG_f);
    out.setSupports(Thyra::ModelEvaluatorBase::OUT_ARG_W_op);
    out.setSupports(Thyra::ModelEvaluatorBase::OUT_ARG_DfDp, 0,
                    Thyra::ModelEvaluatorBase::DERIV_MV_BY_COL); prototype_out_ = out;
  }
  std::string description() const override { return "bs2026 square midpoint LOCA family"; }
  Teuchos::RCP<const Thyra::VectorSpaceBase<double>> get_x_space() const override { return x_space_; }
  Teuchos::RCP<const Thyra::VectorSpaceBase<double>> get_f_space() const override { return f_space_; }
  Teuchos::RCP<const Thyra::VectorSpaceBase<double>> get_p_space(int l) const override {
    if (l != 0) throw std::out_of_range("one continuation parameter only"); return p_space_;
  }
  Teuchos::RCP<const Teuchos::Array<std::string>> get_p_names(int l) const override {
    if (l != 0) throw std::out_of_range("one continuation parameter only");
    return Teuchos::rcp(new Teuchos::Array<std::string>(1, path_->name()));
  }
  Thyra::ModelEvaluatorBase::InArgs<double> createInArgs() const override { return prototype_in_; }
  Thyra::ModelEvaluatorBase::InArgs<double> getNominalValues() const override {
    auto values = prototype_in_; values.set_x(nominal_x_); values.set_p(0, nominal_p_); return values;
  }
  double last_evaluated_coordinate() const { return last_evaluated_coordinate_; }
  Teuchos::RCP<const Thyra::LinearOpWithSolveFactoryBase<double>> get_W_factory() const override {
    return lows_factory_;
  }
  Teuchos::RCP<Thyra::LinearOpBase<double>> create_W_op() const override {
    Teuchos::RCP<Tpetra::Operator<double, local_ordinal_type, global_ordinal_type, node_type>> op = assembler_->create_jacobian();
    return Thyra::createLinearOp<double>(op, f_space_, x_space_);
  }
 protected:
  Thyra::ModelEvaluatorBase::OutArgs<double> createOutArgsImpl() const override { return prototype_out_; }
  void evalModelImpl(const Thyra::ModelEvaluatorBase::InArgs<double>& in,
                     const Thyra::ModelEvaluatorBase::OutArgs<double>& out) const override {
    auto x = Thyra::TpetraOperatorVectorExtraction<double>::getConstTpetraVector(in.get_x());
    if (x.is_null()) throw std::invalid_argument("continuation model requires x");
    Thyra::ConstDetachedVectorView<double> nominal_value(*nominal_p_);
    double coordinate = nominal_value[0];
    if (!in.get_p(0).is_null()) {
      Thyra::ConstDetachedVectorView<double> parameter(*in.get_p(0)); coordinate = parameter[0];
    }
    last_evaluated_coordinate_ = coordinate;
    assembler_->set_environment(environment_on_path(base_environment_, *path_, coordinate));
    if (!out.get_f().is_null()) {
      auto f = Thyra::TpetraOperatorVectorExtraction<double>::getTpetraVector(out.get_f());
      f->assign(*assembler_->residual(*x));
    }
    if (!out.get_W_op().is_null()) {
      auto op = Thyra::TpetraOperatorVectorExtraction<double>::getTpetraOperator(out.get_W_op());
      assembler_->fill_jacobian(*x, *Teuchos::rcp_dynamic_cast<matrix_type>(op, true));
    }
    const auto derivative = out.get_DfDp(0).getMultiVector();
    if (!derivative.is_null()) {
      const auto columns = assembler_->parameter_columns(*x, path_->log_w_lower(coordinate),
          path_->log_w_upper(coordinate), path_->spine_log_w_temperature_derivative(coordinate));
      const auto selected = std::string(path_->name()) == "rho" ? columns.first : columns.second;
      Thyra::assign(derivative->col(0).ptr(),
          *Thyra::createVector(selected, f_space_));
    }
  }
 private:
  Teuchos::RCP<Assembler> assembler_;
  std::shared_ptr<const ContinuationPath> path_;
  Environment base_environment_;
  Teuchos::RCP<const Thyra::VectorSpaceBase<double>> x_space_, f_space_, p_space_;
  Teuchos::RCP<Thyra::VectorBase<double>> nominal_x_, nominal_p_;
  Teuchos::RCP<Thyra::Amesos2LinearOpWithSolveFactory<double>> lows_factory_;
  Thyra::ModelEvaluatorBase::InArgs<double> prototype_in_;
  Thyra::ModelEvaluatorBase::OutArgs<double> prototype_out_;
  mutable double last_evaluated_coordinate_ = 0.0;
};

inline void require_midpoint_loca_layout(const OrbitLayout& layout, const char* operation) {
  if (layout.stage_count() != 1)
    throw std::invalid_argument(std::string(operation) + " supports midpoint layouts only; higher-order LOCA is TASK-066 scope");
}

inline std::vector<double> continuation_metric_weights(const Assembler& assembler) {
  const auto& layout = assembler.layout(); require_midpoint_loca_layout(layout, "continuation metric");
  const auto& ref = assembler.phase_reference();
  std::vector<double> weights(layout.unknown_size() + 1, 0.0);
  for (std::size_t i = 0; i < layout.interval_count(); ++i) {
    const double width = ref.boundaries[i + 1] - ref.boundaries[i];
    const std::size_t previous = (i + layout.interval_count() - 1) % layout.interval_count();
    const double previous_width = ref.boundaries[previous + 1] - ref.boundaries[previous];
    for (int c = 0; c < state_dimension; ++c) {
      weights[layout.endpoint_index(i, c)] = 0.25 * (width + previous_width) * ref.state_scaling[c] * ref.state_scaling[c];
      weights[layout.stage_index(i, 0, c)] = 0.5 * width * ref.state_scaling[c] * ref.state_scaling[c];
    }
  }
  weights[layout.log_period_index()] = 1.0; weights.back() = 1.0; return weights;
}

inline double weighted_norm(const std::vector<double>& values, const std::vector<double>& weights) {
  if (values.size() != weights.size()) throw std::invalid_argument("weighted norm size mismatch");
  double sum = 0.0; for (std::size_t i = 0; i < values.size(); ++i) sum += weights[i] * values[i] * values[i];
  return std::sqrt(std::max(0.0, sum));
}

class WeightedThyraGroup final : public LOCA::Thyra::Group {
 public:
  WeightedThyraGroup(const Teuchos::RCP<LOCA::GlobalData>& data, const NOX::Thyra::Vector& initial,
                     const Teuchos::RCP<::Thyra::ModelEvaluator<double>>& model,
                     const LOCA::ParameterVector& parameters, std::vector<double> weights)
      : NOX::Thyra::Group(initial, model, Teuchos::null, Teuchos::null, Teuchos::null, false),
        LOCA::Abstract::Group(data),
        LOCA::Thyra::Group(data, initial, model, parameters, 0, true),
        weights_(std::move(weights)), save_data_(Teuchos::null) {}
  WeightedThyraGroup(const WeightedThyraGroup& source, NOX::CopyType type = NOX::DeepCopy)
      : NOX::Thyra::Group(source, type), LOCA::Abstract::Group(source, type),
        LOCA::Thyra::Group(source, type), weights_(source.weights_), save_data_(source.save_data_) {
    if (!save_data_.is_null()) setSaveDataStrategy(save_data_);
  }
  Teuchos::RCP<NOX::Abstract::Group> clone(NOX::CopyType type = NOX::DeepCopy) const override {
    return Teuchos::rcp(new WeightedThyraGroup(*this, type));
  }
  void installSaveDataStrategy(const Teuchos::RCP<LOCA::Thyra::SaveDataStrategy>& strategy) {
    save_data_ = strategy; setSaveDataStrategy(strategy);
  }
  double computeScaledDotProduct(const NOX::Abstract::Vector& a,
                                 const NOX::Abstract::Vector& b) const override {
    const auto& ta = dynamic_cast<const NOX::Thyra::Vector&>(a);
    const auto& tb = dynamic_cast<const NOX::Thyra::Vector&>(b);
    auto av = Thyra::TpetraOperatorVectorExtraction<double>::getConstTpetraVector(ta.getThyraRCPVector());
    auto bv = Thyra::TpetraOperatorVectorExtraction<double>::getConstTpetraVector(tb.getThyraRCPVector());
    const auto aa = copy_vector_by_global_id(*av), bb = copy_vector_by_global_id(*bv);
    if (aa.size() != weights_.size() || bb.size() != weights_.size())
      throw std::logic_error("LOCA state metric size mismatch");
    double result = 0.0; for (std::size_t i = 0; i < aa.size(); ++i) result += weights_[i] * aa[i] * bb[i];
    return result;
  }
 private:
  std::vector<double> weights_;
  Teuchos::RCP<LOCA::Thyra::SaveDataStrategy> save_data_;
};

struct SavedPoint { std::vector<double> unknowns; double coordinate = 0.0; };
struct StepEvent {
  std::string status;
  double attempted_coordinate = 0.0;
  double accepted_coordinate = 0.0;
  double attempted_coordinate_delta = 0.0;
  double retry_coordinate_delta = 0.0;
  bool initial_solve = false;
  bool final_target_solve = false;
};

class ContinuationRecorder final : public LOCA::Thyra::SaveDataStrategy {
 public:
  void saveSolution(const NOX::Abstract::Vector& x, double p) override {
    const auto& tx = dynamic_cast<const NOX::Thyra::Vector&>(x);
    auto vector = Thyra::TpetraOperatorVectorExtraction<double>::getConstTpetraVector(tx.getThyraRCPVector());
    points.push_back({copy_vector_by_global_id(*vector), p});
  }
  void preProcessContinuationStep(LOCA::Abstract::Iterator::StepStatus previous) override {
    previous_status_ = previous;
    points_before_attempt_ = points.size();
    coordinate_before_attempt_ = points.empty() ? initial_coordinate_ : points.back().coordinate;
  }
  void postProcessContinuationStep(LOCA::Abstract::Iterator::StepStatus status) override {
    const bool has_saved_point = points.size() > points_before_attempt_;
    const double attempted = has_saved_point ? points.back().coordinate : current_coordinate();
    const double attempted_coordinate_delta = attempted - coordinate_before_attempt_;
    const bool initial = events.empty() && points_before_attempt_ == 0;
    events.push_back({status == LOCA::Abstract::Iterator::Successful ? "accepted" : "rejected",
                      attempted, status == LOCA::Abstract::Iterator::Successful ? attempted : coordinate_before_attempt_,
                      attempted_coordinate_delta, 0.0, initial, false});
  }
  ContinuationRecorder(double initial_coordinate, double target_coordinate,
                       Teuchos::RCP<const ContinuationModelEvaluator> model)
      : initial_coordinate_(initial_coordinate), target_coordinate_(target_coordinate), model_(std::move(model)) {}
  void reconcile() {
    for (std::size_t i = 0; i + 1 < events.size(); ++i)
      if (events[i].status == "rejected") events[i].retry_coordinate_delta = events[i + 1].attempted_coordinate_delta;
    if (!events.empty()) events.back().final_target_solve =
        std::abs(events.back().accepted_coordinate - target_coordinate_) <= 1.0e-14;
  }
  std::vector<SavedPoint> points; std::vector<StepEvent> events;
 private:
  double current_coordinate() const { return model_.is_null() ? initial_coordinate_ : model_->last_evaluated_coordinate(); }
  Teuchos::RCP<const ContinuationModelEvaluator> model_;
  double initial_coordinate_ = 0.0, target_coordinate_ = 0.0, coordinate_before_attempt_ = 0.0;
  LOCA::Abstract::Iterator::StepStatus previous_status_ = LOCA::Abstract::Iterator::Successful;
  std::size_t points_before_attempt_ = 0;
};

class RejectFirstConvergedSolve final : public NOX::StatusTest::Generic {
 public:
  explicit RejectFirstConvergedSolve(Teuchos::RCP<NOX::StatusTest::Generic> underlying)
      : underlying_(std::move(underlying)) {}
  NOX::StatusTest::StatusType checkStatus(const NOX::Solver::Generic& problem,
                                         NOX::StatusTest::CheckType type) override {
    status_ = underlying_->checkStatus(problem, type);
    // The initial fixed-parameter solve is iteration zero. Reject the first
    // converged nontrivial corrector once, then allow LOCA to reduce/retry.
    if (status_ == NOX::StatusTest::Converged) {
      ++converged_solves_;
      if (!rejected_ && converged_solves_ == 2) { rejected_ = true; status_ = NOX::StatusTest::Failed; }
    }
    return status_;
  }
  NOX::StatusTest::StatusType getStatus() const override { return status_; }
  std::ostream& print(std::ostream& stream, int indent = 0) const override {
    return stream << std::string(indent, ' ') << "Reject first converged native corrector once";
  }
 private:
  Teuchos::RCP<NOX::StatusTest::Generic> underlying_;
  NOX::StatusTest::StatusType status_ = NOX::StatusTest::Unevaluated;
  bool rejected_ = false;
  int converged_solves_ = 0;
};

struct NativeRunResult {
  std::vector<SavedPoint> points; std::vector<StepEvent> events;
  LOCA::Abstract::Iterator::IteratorStatus status = LOCA::Abstract::Iterator::Failed;
  int raw_step_number = 0, raw_failed_step_count = 0, raw_total_step_count = 0;
  std::size_t base_dimension = 0, extended_dimension = 0;
  std::string continuation_method = "Arc Length";
  std::string predictor_method = "Secant";
  std::string step_size_method = "Adaptive";
  bool used_bootstrap_restart_tangent = false;
};

inline Teuchos::RCP<LOCA::MultiContinuation::ExtendedVector> make_restart_tangent(
    const Teuchos::RCP<LOCA::GlobalData>& global, const NOX::Thyra::Vector& initial,
    const std::vector<double>& tangent) {
  if (tangent.size() != static_cast<std::size_t>(initial.length()) + 1)
    throw std::invalid_argument("restart tangent dimension mismatch");
  auto state = initial.clone(NOX::ShapeCopy); state->init(0.0);
  auto& thyra = dynamic_cast<NOX::Thyra::Vector&>(*state);
  auto tpetra = Thyra::TpetraOperatorVectorExtraction<double>::getTpetraVector(thyra.getThyraRCPVector());
  for (std::size_t gid = 0; gid + 1 < tangent.size(); ++gid)
    tpetra->replaceGlobalValue(static_cast<global_ordinal_type>(gid), tangent[gid]);
  auto extended = Teuchos::rcp(new LOCA::MultiContinuation::ExtendedVector(global, *state, 1));
  extended->setScalar(0, tangent.back());
  return extended;
}

inline NativeRunResult run_native_loca(const Teuchos::RCP<Assembler>& assembler,
                                       std::shared_ptr<const ContinuationPath> path,
                                       const vector_type& initial, double initial_coordinate,
                                       double target_coordinate, double initial_step,
                                       int maximum_steps = 80,
                                       const std::vector<double>* bootstrap_tangent = nullptr,
                                       bool force_first_native_rejection = false) {
  require_midpoint_loca_layout(assembler->layout(), "native LOCA continuation");
  NativeRunResult result; result.base_dimension = assembler->layout().unknown_size();
  auto model = Teuchos::rcp(new ContinuationModelEvaluator(assembler, path, initial_coordinate, initial));
  NOX::Thyra::Vector nox_initial(*model->getNominalValues().get_x());
  LOCA::ParameterVector parameters; parameters.addParameter(path->name(), initial_coordinate);
  auto top = Teuchos::rcp(new Teuchos::ParameterList);
  top->sublist("LOCA").sublist("Stepper").set("Continuation Method", "Arc Length");
  auto& stepper = top->sublist("LOCA").sublist("Stepper");
  stepper.set("Continuation Parameter", std::string(path->name()));
  stepper.set("Initial Value", initial_coordinate);
  stepper.set("Min Value", std::min(initial_coordinate, target_coordinate));
  stepper.set("Max Value", std::max(initial_coordinate, target_coordinate));
  stepper.set("Max Steps", maximum_steps); stepper.set("Compute Eigenvalues", false);
  stepper.set("Enable Arc Length Scaling", false);
  auto& predictor = top->sublist("LOCA").sublist("Predictor");
  predictor.set("Method", "Secant");
  auto& step_size = top->sublist("LOCA").sublist("Step Size"); step_size.set("Method", "Adaptive");
  step_size.set("Initial Step Size", std::copysign(std::abs(initial_step), target_coordinate - initial_coordinate));
  stepper.set("Continuation Parameter", std::string(path->name()));
  step_size.set("Min Step Size", 1.0e-8); step_size.set("Max Step Size", 0.04);
  step_size.set("Aggressiveness", 0.5);
  auto& nox = top->sublist("NOX"); nox.set("Nonlinear Solver", "Line Search Based");
  nox.sublist("Printing").set("Output Information", 0);
  nox.sublist("Direction").set("Method", "Newton"); nox.sublist("Line Search").set("Method", "Backtrack");
  auto global = LOCA::createGlobalData(top);
  if (bootstrap_tangent != nullptr) {
    auto oriented_tangent = *bootstrap_tangent;
    if (oriented_tangent.back() < 0.0)
      for (double& value : oriented_tangent) value = -value;
    auto restart = make_restart_tangent(global, nox_initial, oriented_tangent);
    auto& first = predictor.sublist("First Step Predictor");
    first.set("Method", "Restart"); first.set("Restart Vector", restart);
    result.used_bootstrap_restart_tangent = true;
  }
  auto group = Teuchos::rcp(new WeightedThyraGroup(global, nox_initial, model, parameters,
                                                    [&]() { auto weights = continuation_metric_weights(*assembler); weights.pop_back(); return weights; }()));
  auto recorder = Teuchos::rcp(new ContinuationRecorder(initial_coordinate, target_coordinate, model)); group->installSaveDataStrategy(recorder);
  auto norm = Teuchos::rcp(new NOX::StatusTest::NormF(nox_norm_f_tolerance, NOX::StatusTest::NormF::Unscaled));
  auto maxit = Teuchos::rcp(new NOX::StatusTest::MaxIters(nox_max_iterations));
  auto finite = Teuchos::rcp(new NOX::StatusTest::FiniteValue(NOX::StatusTest::FiniteValue::FVector));
  auto nonlinear = Teuchos::rcp(new NOX::StatusTest::Combo(NOX::StatusTest::Combo::OR, norm, maxit));
  nonlinear->addStatusTest(finite);
  Teuchos::RCP<NOX::StatusTest::Generic> nonlinear_status = nonlinear;
  if (force_first_native_rejection)
    nonlinear_status = Teuchos::rcp(new RejectFirstConvergedSolve(nonlinear_status));
  // Use the stepper's parameter-bound stopping logic.  A standalone MaxIters
  // LOCA status test bypasses those bounds and leaves Stepper::targetValue at
  // its zero sentinel, causing finish() to attempt an unrelated natural step.
  stepper.set("Return Failed on Reaching Max Steps", false);
  LOCA::Stepper native(global, group, nonlinear_status, top);
  result.status = native.run(); result.raw_step_number = native.getStepNumber();
  result.raw_failed_step_count = native.getNumFailedSteps(); result.raw_total_step_count = native.getNumTotalSteps();
  recorder->reconcile(); result.points = recorder->points; result.events = recorder->events;
  result.extended_dimension = result.base_dimension + 1;
  LOCA::destroyGlobalData(global); return result;
}

struct BootstrapAttempt { int attempt = 0; double requested_step = 0.0; double coordinate = 0.0;
  double weighted_step = std::numeric_limits<double>::infinity(); bool accepted = false; std::vector<std::string> reasons; };
struct BootstrapResult { SolveResult neighbor; double coordinate = 0.0; std::vector<double> tangent; std::vector<BootstrapAttempt> attempts; };

inline BootstrapResult deterministic_bootstrap(const Teuchos::RCP<Assembler>& assembler,
                                                const ContinuationPath& path,
                                                const vector_type& origin, double origin_coordinate,
                                                int direction, double initial_coordinate_step,
                                                double maximum_weighted_step = 0.25) {
  if (direction != -1 && direction != 1) throw std::invalid_argument("bootstrap direction must be signed");
  BootstrapResult result; double step = initial_coordinate_step;
  const auto origin_values = copy_vector_by_global_id(origin); const auto weights = continuation_metric_weights(*assembler);
  for (int attempt = 0; attempt <= bootstrap_max_halvings; ++attempt) {
    const double coordinate = origin_coordinate + direction * step;
    assembler->set_environment(environment_on_path(assembler->environment(), path, coordinate));
    auto solved = solve_fixed_parameter(assembler, origin);
    std::vector<double> delta(weights.size()); const auto candidate = copy_vector_by_global_id(*solved.unknowns);
    for (std::size_t i = 0; i < candidate.size(); ++i) delta[i] = candidate[i] - origin_values[i];
    delta.back() = coordinate - origin_coordinate; const double change = weighted_norm(delta, weights);
    const bool accepted = solved.acceptance.accepted && change <= maximum_weighted_step;
    BootstrapAttempt event{attempt, direction * step, coordinate, change, accepted, solved.acceptance.rejection_reasons};
    if (change > maximum_weighted_step) event.reasons.push_back("excessive_weighted_bootstrap_step");
    result.attempts.push_back(event);
    if (accepted) {
      const double norm = weighted_norm(delta, weights); for (double& value : delta) value /= norm;
      result.neighbor = std::move(solved); result.coordinate = coordinate; result.tangent = std::move(delta); return result;
    }
    step *= 0.5; if (step < bootstrap_minimum_coordinate_step) break;
  }
  throw std::runtime_error("deterministic LOCA bootstrap failed");
}

inline PhaseReference refreshed_phase_reference(const Assembler& assembler,
                                                const vector_type& accepted_unknowns) {
  const auto& layout = assembler.layout(); require_midpoint_loca_layout(layout, "phase-reference refresh");
  const auto values = copy_vector_by_global_id(accepted_unknowns);
  const double period = std::exp(values.at(static_cast<std::size_t>(layout.log_period_index())));
  PhaseReference refreshed = assembler.phase_reference();
  const auto environment = assembler.environment();
  for (std::size_t interval = 0; interval < layout.interval_count(); ++interval) {
    std::array<double, state_dimension> stage{};
    for (int component = 0; component < state_dimension; ++component)
      stage[component] = values.at(static_cast<std::size_t>(layout.stage_index(interval, 0, component)));
    const auto derivatives = local_derivatives(stage, environment.T, std::log(environment.w), environment);
    refreshed.stage_values[interval] = stage;
    for (int component = 0; component < state_dimension; ++component)
      refreshed.stage_derivatives[interval][component] = period * derivatives.values[component];
  }
  return refreshed;
}

}  // namespace midpoint
}  // namespace bs2026_loca
