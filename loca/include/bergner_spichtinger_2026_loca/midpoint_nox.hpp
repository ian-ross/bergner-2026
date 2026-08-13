#pragma once

#include "bergner_spichtinger_2026_loca/midpoint_orbit.hpp"

#include <Amesos2_Status.hpp>
#include <NOX.H>
#include <NOX_Solver_Factory.H>
#include <NOX_StatusTest_Combo.H>
#include <NOX_StatusTest_FiniteValue.H>
#include <NOX_StatusTest_MaxIters.H>
#include <NOX_StatusTest_NormF.H>
#include <NOX_Thyra.H>
#include <Thyra_Amesos2LinearOpWithSolve_decl.hpp>
#include <Thyra_Amesos2LinearOpWithSolveFactory_decl.hpp>
#include <Thyra_StateFuncModelEvaluatorBase.hpp>
#include <Thyra_TpetraThyraWrappers.hpp>

#include <algorithm>
#include <cmath>
#include <limits>
#include <string>
#include <utility>
#include <vector>

namespace bs2026_loca {
namespace midpoint {

inline constexpr char nox_solver_version[] = "thyra-nox-amesos2-klu2-v1";
inline constexpr double corrected_solution_parity_tolerance = 1.0e-8;
inline constexpr double accepted_stage_update_tolerance = 1.0e-9;
inline constexpr double accepted_phase_tolerance = 1.0e-10;
inline constexpr double nox_norm_f_tolerance = 1.0e-11;
inline constexpr int nox_max_iterations = 40;
inline constexpr char nox_direction_method[] = "Newton";
inline constexpr char nox_line_search_method[] = "Backtrack";
inline constexpr double nox_default_step = 1.0;
inline constexpr double nox_minimum_step = 1.0e-10;
inline constexpr double nox_recovery_step = 1.0e-6;
inline constexpr char amesos2_refactorization_policy[] = "REPIVOT_ON_REFACTORIZATION";

class ThyraModelEvaluator final : public Thyra::StateFuncModelEvaluatorBase<double> {
 public:
  explicit ThyraModelEvaluator(Teuchos::RCP<const Assembler> assembler)
      : assembler_(require_assembler(std::move(assembler))),
        x_space_(Thyra::createVectorSpace<double>(assembler_->layout().domain_map())),
        f_space_(Thyra::createVectorSpace<double>(assembler_->layout().range_map())) {
    Thyra::ModelEvaluatorBase::InArgsSetup<double> in_args;
    in_args.setModelEvalDescription(description());
    in_args.setSupports(Thyra::ModelEvaluatorBase::IN_ARG_x);
    in_args.set_Np(0);
    prototype_in_args_ = in_args;

    Thyra::ModelEvaluatorBase::OutArgsSetup<double> out_args;
    out_args.setModelEvalDescription(description());
    out_args.set_Np_Ng(0, 0);
    out_args.setSupports(Thyra::ModelEvaluatorBase::OUT_ARG_f);
    out_args.setSupports(Thyra::ModelEvaluatorBase::OUT_ARG_W_op);
    prototype_out_args_ = out_args;
  }

  std::string description() const override { return "bs2026 Gauss collocation-plus-phase Thyra model"; }
  Teuchos::RCP<const Thyra::VectorSpaceBase<double>> get_x_space() const override { return x_space_; }
  Teuchos::RCP<const Thyra::VectorSpaceBase<double>> get_f_space() const override { return f_space_; }
  Thyra::ModelEvaluatorBase::InArgs<double> createInArgs() const override { return prototype_in_args_; }

  Teuchos::RCP<Thyra::LinearOpBase<double>> create_W_op() const override {
    Teuchos::RCP<Tpetra::Operator<double, local_ordinal_type, global_ordinal_type, node_type>> op =
        assembler_->create_jacobian();
    return Thyra::createLinearOp<double>(op, f_space_, x_space_);
  }

 protected:
  Thyra::ModelEvaluatorBase::OutArgs<double> createOutArgsImpl() const override {
    return prototype_out_args_;
  }

  void evalModelImpl(const Thyra::ModelEvaluatorBase::InArgs<double>& in_args,
                     const Thyra::ModelEvaluatorBase::OutArgs<double>& out_args) const override {
    const auto x = Thyra::TpetraOperatorVectorExtraction<double>::getConstTpetraVector(in_args.get_x());
    if (x.is_null()) throw std::invalid_argument("Thyra midpoint model requires x");
    if (!out_args.get_f().is_null()) {
      auto f = Thyra::TpetraOperatorVectorExtraction<double>::getTpetraVector(out_args.get_f());
      f->assign(*assembler_->residual(*x));
    }
    if (!out_args.get_W_op().is_null()) {
      auto op = Thyra::TpetraOperatorVectorExtraction<double>::getTpetraOperator(out_args.get_W_op());
      auto matrix = Teuchos::rcp_dynamic_cast<matrix_type>(op, true);
      assembler_->fill_jacobian(*x, *matrix);
    }
  }

 private:
  static Teuchos::RCP<const Assembler> require_assembler(Teuchos::RCP<const Assembler> assembler) {
    if (assembler.is_null()) throw std::invalid_argument("Thyra model requires an assembler");
    return assembler;
  }

  Teuchos::RCP<const Assembler> assembler_;
  Teuchos::RCP<const Thyra::VectorSpaceBase<double>> x_space_;
  Teuchos::RCP<const Thyra::VectorSpaceBase<double>> f_space_;
  Thyra::ModelEvaluatorBase::InArgs<double> prototype_in_args_;
  Thyra::ModelEvaluatorBase::OutArgs<double> prototype_out_args_;
};

struct LinearSolveDiagnostics {
  std::string backend = "unreported";
  int symbolic_factorizations = 0;
  int numeric_factorizations = 0;
  int solves = 0;
  bool symbolic_complete = false;
  bool numeric_complete = false;
  bool solve_complete = false;
  bool reported = false;
};

struct AcceptanceInputs {
  bool nox_converged = false;
  Diagnostics residual;
  bool physical_states_positive_finite = false;
  bool period_positive_finite = false;
  LinearSolveDiagnostics linear;
};

struct AcceptanceResult {
  bool accepted = false;
  std::vector<std::string> rejection_reasons;
};

inline AcceptanceResult evaluate_acceptance(const AcceptanceInputs& inputs) {
  AcceptanceResult result;
  if (!inputs.nox_converged) result.rejection_reasons.emplace_back("nox_not_converged");
  if (!(std::isfinite(inputs.residual.stage_max) && std::isfinite(inputs.residual.stage_rms) &&
        inputs.residual.stage_max <= accepted_stage_update_tolerance &&
        inputs.residual.stage_rms <= accepted_stage_update_tolerance &&
        std::isfinite(inputs.residual.update_max) && std::isfinite(inputs.residual.update_rms) &&
        inputs.residual.update_max <= accepted_stage_update_tolerance &&
        inputs.residual.update_rms <= accepted_stage_update_tolerance)) {
    result.rejection_reasons.emplace_back("block_residual_tolerance");
  }
  if (!(std::isfinite(inputs.residual.phase_abs) &&
        inputs.residual.phase_abs <= accepted_phase_tolerance)) {
    result.rejection_reasons.emplace_back("phase_tolerance");
  }
  if (!inputs.physical_states_positive_finite) {
    result.rejection_reasons.emplace_back("physical_state_positivity_or_finiteness");
  }
  if (!inputs.period_positive_finite) {
    result.rejection_reasons.emplace_back("period_positivity_or_finiteness");
  }
  if (!(std::isfinite(inputs.residual.phase_energy) && inputs.residual.phase_energy > 0.0)) {
    result.rejection_reasons.emplace_back("phase_energy_invalid");
  }
  if (!(inputs.linear.reported && inputs.linear.backend == "KLU2" &&
        inputs.linear.symbolic_complete && inputs.linear.numeric_complete &&
        inputs.linear.solve_complete && inputs.linear.symbolic_factorizations > 0 &&
        inputs.linear.numeric_factorizations > 0 && inputs.linear.solves > 0)) {
    result.rejection_reasons.emplace_back("linear_solve_diagnostics");
  }
  result.accepted = result.rejection_reasons.empty();
  return result;
}

struct SolveResult {
  Teuchos::RCP<vector_type> unknowns;
  Teuchos::RCP<vector_type> residual;
  Diagnostics diagnostics;
  LinearSolveDiagnostics linear;
  AcceptanceResult acceptance;
  bool nox_converged = false;
  bool residual_available = false;
  int nonlinear_iterations = 0;
  double nox_residual_norm = std::numeric_limits<double>::infinity();
  double period = std::numeric_limits<double>::quiet_NaN();
  bool physical_states_positive_finite = false;
  bool period_positive_finite = false;
};

inline bool finite_positive_exp(double exponent) {
  const double value = std::exp(exponent);
  return std::isfinite(value) && value > 0.0;
}

inline SolveResult solve_fixed_parameter_impl(const Teuchos::RCP<const Assembler>& assembler,
                                              const vector_type& initial_unknowns) {
  SolveResult result;
  result.unknowns = Teuchos::rcp(new vector_type(initial_unknowns));
  const auto model = Teuchos::rcp(new ThyraModelEvaluator(assembler));
  auto thyra_initial = Thyra::createVector(result.unknowns, model->get_x_space());
  NOX::Thyra::Vector nox_initial(thyra_initial);
  auto jacobian = model->create_W_op();
  const auto lows_factory = Teuchos::rcp(
      new Thyra::Amesos2LinearOpWithSolveFactory<double>(
          Thyra::Amesos2::KLU2, Thyra::Amesos2::REPIVOT_ON_REFACTORIZATION));
  lows_factory->setParameterList(Teuchos::rcp(new Teuchos::ParameterList("Amesos2")));
  Teuchos::RCP<const Thyra::ModelEvaluator<double>> model_base = model;
  Teuchos::RCP<const Thyra::LinearOpWithSolveFactoryBase<double>> lows_base = lows_factory;
  Teuchos::RCP<Thyra::PreconditionerBase<double>> no_preconditioner;
  Teuchos::RCP<Thyra::PreconditionerFactoryBase<double>> no_preconditioner_factory;
  auto group = Teuchos::rcp(new NOX::Thyra::Group(
      nox_initial, model_base, jacobian, lows_base, no_preconditioner, no_preconditioner_factory));

  auto norm_f = Teuchos::rcp(new NOX::StatusTest::NormF(
      nox_norm_f_tolerance, NOX::StatusTest::NormF::Unscaled));
  auto max_iters = Teuchos::rcp(new NOX::StatusTest::MaxIters(nox_max_iterations));
  auto finite_f = Teuchos::rcp(new NOX::StatusTest::FiniteValue(
      NOX::StatusTest::FiniteValue::FVector));
  auto finite_x = Teuchos::rcp(new NOX::StatusTest::FiniteValue(
      NOX::StatusTest::FiniteValue::SolutionVector));
  auto status = Teuchos::rcp(new NOX::StatusTest::Combo(NOX::StatusTest::Combo::OR, norm_f, max_iters));
  status->addStatusTest(finite_f).addStatusTest(finite_x);

  auto parameters = Teuchos::rcp(new Teuchos::ParameterList);
  parameters->set("Nonlinear Solver", "Line Search Based");
  parameters->sublist("Printing").set("Output Information", 0);
  parameters->sublist("Direction").set("Method", nox_direction_method);
  parameters->sublist("Line Search").set("Method", nox_line_search_method);
  parameters->sublist("Line Search").sublist("Backtrack").set("Default Step", nox_default_step);
  parameters->sublist("Line Search").sublist("Backtrack").set("Minimum Step", nox_minimum_step);
  parameters->sublist("Line Search").sublist("Backtrack").set("Recovery Step", nox_recovery_step);

  auto solver = NOX::Solver::buildSolver(group, status, parameters);
  result.residual = Teuchos::rcp(new vector_type(assembler->layout().range_map()));
  result.residual->putScalar(0.0);
  result.diagnostics.phase_energy = assembler->phase_energy();
  result.diagnostics.stage_max = result.diagnostics.stage_rms = std::numeric_limits<double>::infinity();
  result.diagnostics.update_max = result.diagnostics.update_rms = std::numeric_limits<double>::infinity();
  result.diagnostics.phase_abs = std::numeric_limits<double>::infinity();
  result.diagnostics.state_scaling = assembler->phase_reference().state_scaling;

  bool usable_final_group = false;
  bool solve_returned = false;
  try {
    const auto status_value = solver->solve();
    solve_returned = true;
    result.nox_converged = status_value == NOX::StatusTest::Converged;
    result.nonlinear_iterations = solver->getNumIterations();
    result.nox_residual_norm = solver->getSolutionGroup().getNormF();
    const auto* final_vector = dynamic_cast<const NOX::Thyra::Vector*>(&solver->getSolutionGroup().getX());
    if (final_vector != nullptr) {
      const auto final_tpetra = Thyra::TpetraOperatorVectorExtraction<double>::getConstTpetraVector(
          final_vector->getThyraRCPVector());
      if (!final_tpetra.is_null()) {
        result.unknowns->assign(*final_tpetra);
        result.residual = assembler->residual(*result.unknowns);
        result.diagnostics = assembler->diagnostics(*result.residual);
        result.residual_available = true;
        usable_final_group = true;
      }
    }
  } catch (const std::exception&) {
    // Model, nonlinear, or final-group failures are represented as a stable
    // rejected result. The safe initial vector and invalid diagnostics above
    // remain available to callers and no post-failure model evaluation occurs.
    result.nox_converged = false;
  }
  if (!usable_final_group) result.nox_converged = false;

  // A converged initial guess may perform no Newton solve and early failures may
  // not leave a previous Thyra group/Jacobian. Probe each polymorphic seam
  // without throwing; absent diagnostics remain unreported and fail acceptance.
  const auto* linear_group = solve_returned && result.nonlinear_iterations > 0
      ? dynamic_cast<const NOX::Thyra::Group*>(&solver->getPreviousSolutionGroup()) : nullptr;
  if (linear_group != nullptr) {
    const auto amesos_lows = Teuchos::rcp_dynamic_cast<const Thyra::Amesos2LinearOpWithSolve<double>>(
        linear_group->getJacobian(), false);
    if (!amesos_lows.is_null()) {
      const auto amesos_solver =
          const_cast<Thyra::Amesos2LinearOpWithSolve<double>*>(amesos_lows.get())->get_amesos2Solver();
      if (!amesos_solver.is_null()) {
        const auto& status_data = amesos_solver->getStatus();
        result.linear.backend = amesos_solver->name() == "KLU2" || amesos_solver->name() == "klu2"
            ? "KLU2" : amesos_solver->name();
        result.linear.symbolic_factorizations = status_data.getNumSymbolicFact();
        result.linear.numeric_factorizations = status_data.getNumNumericFact();
        result.linear.solves = status_data.getNumSolve();
        result.linear.symbolic_complete = status_data.symbolicFactorizationDone();
        result.linear.numeric_complete = status_data.numericFactorizationDone();
        result.linear.solve_complete = status_data.getNumSolve() > 0;
        result.linear.reported = true;
      }
    }
  }

  const auto values = copy_vector_by_global_id(*result.unknowns);
  result.period_positive_finite = finite_positive_exp(values.back());
  if (result.period_positive_finite) result.period = std::exp(values.back());
  result.physical_states_positive_finite = usable_final_group;
  for (std::size_t interval = 0; interval < assembler->layout().interval_count(); ++interval) {
    for (int component = 0; component < 2; ++component) {
      result.physical_states_positive_finite = result.physical_states_positive_finite &&
          finite_positive_exp(values[static_cast<std::size_t>(assembler->layout().endpoint_index(interval, component))]);
    }
    result.physical_states_positive_finite = result.physical_states_positive_finite &&
        std::isfinite(values[static_cast<std::size_t>(assembler->layout().endpoint_index(interval, 2))]);
    for (int stage = 0; stage < assembler->layout().stage_count(); ++stage) {
      for (int component = 0; component < 2; ++component) {
        result.physical_states_positive_finite = result.physical_states_positive_finite &&
            finite_positive_exp(values[static_cast<std::size_t>(assembler->layout().stage_index(interval, stage, component))]);
      }
      result.physical_states_positive_finite = result.physical_states_positive_finite &&
          std::isfinite(values[static_cast<std::size_t>(assembler->layout().stage_index(interval, stage, 2))]);
    }
  }
  AcceptanceInputs acceptance_inputs;
  acceptance_inputs.nox_converged = result.nox_converged;
  acceptance_inputs.residual = result.diagnostics;
  acceptance_inputs.physical_states_positive_finite = result.physical_states_positive_finite;
  acceptance_inputs.period_positive_finite = result.period_positive_finite;
  acceptance_inputs.linear = result.linear;
  result.acceptance = evaluate_acceptance(acceptance_inputs);
  return result;
}

inline SolveResult solve_fixed_parameter(const Teuchos::RCP<const Assembler>& assembler,
                                         const vector_type& initial_unknowns) {
  try {
    return solve_fixed_parameter_impl(assembler, initial_unknowns);
  } catch (const std::exception&) {
    // Some installed NOX/Amesos2 paths may throw while constructing or
    // destroying a failed solver, outside solver->solve(). Convert the entire
    // corrector boundary into the same stable rejected-result contract.
    SolveResult result;
    result.unknowns = Teuchos::rcp(new vector_type(initial_unknowns));
    result.residual = Teuchos::rcp(new vector_type(assembler->layout().range_map()));
    result.residual->putScalar(0.0);
    result.diagnostics.stage_max = result.diagnostics.stage_rms = std::numeric_limits<double>::infinity();
    result.diagnostics.update_max = result.diagnostics.update_rms = std::numeric_limits<double>::infinity();
    result.diagnostics.phase_abs = std::numeric_limits<double>::infinity();
    result.diagnostics.phase_energy = assembler->phase_energy();
    result.diagnostics.state_scaling = assembler->phase_reference().state_scaling;
    const auto values = copy_vector_by_global_id(*result.unknowns);
    result.period_positive_finite = finite_positive_exp(values.back());
    if (result.period_positive_finite) result.period = std::exp(values.back());
    AcceptanceInputs inputs;
    inputs.nox_converged = false;
    inputs.residual = result.diagnostics;
    inputs.physical_states_positive_finite = false;
    inputs.period_positive_finite = result.period_positive_finite;
    inputs.linear = result.linear;
    result.acceptance = evaluate_acceptance(inputs);
    return result;
  }
}

}  // namespace midpoint
}  // namespace bs2026_loca
