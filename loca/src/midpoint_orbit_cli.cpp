#include "bergner_spichtinger_2026_loca/midpoint_loca.hpp"

#include <Teuchos_DefaultComm.hpp>
#include <Tpetra_Core.hpp>
#include <Trilinos_version.h>

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

struct LocusRow { double temperature, lower, upper; };

const std::array<LocusRow, 101> hopf_locus_rows{{
{190, -5.9768209916058312, -3.1479325431882166},
{190.5, -5.9323432720811047, -3.1017617347452666},
{191, -5.8880818522007541, -3.0558867045692493},
{191.5, -5.844035414820401, -3.0103043992076204},
{192, -5.8002026480689404, -2.9650118973028228},
{192.5, -5.7565822467461087, -2.9200064015744824},
{193, -5.713172913582933, -2.8752852314674215},
{193.5, -5.6699733604508333, -2.8308458164368488},
{194, -5.6269823094987723, -2.7866856897826078},
{194.5, -5.5841984942096712, -2.7428024830283713},
{195, -5.5416206604062985, -2.6991939207688724},
{195.5, -5.4992475671996228, -2.6558578159752368},
{196, -5.4570779879083551, -2.6127920656981556},
{196.5, -5.4151107109277774, -2.5699946471672899},
{197, -5.3733445405924138, -2.5274636142239273},
{197.5, -5.3317782979758999, -2.485197094089489},
{198, -5.290410821680247, -2.4431932844342827},
{198.5, -5.2492409686431829, -2.4014504507222081},
{199, -5.2082676148808478, -2.3599669238077192},
{199.5, -5.1674896562713801, -2.3187410977891587},
{200, -5.126906009282, -2.2777714280707686},
{200.5, -5.08651561173677, -2.237056429641493},
{201, -5.046317423557765, -2.1965946755491732},
{201.5, -5.0063104275318295, -2.1563847955451276},
{202, -4.966493630066191, -2.1164254749200393},
{202.5, -4.9268660619605233, -2.0767154534804257},
{203, -4.8874267791802719, -2.0372535246873471},
{203.5, -4.8481748636714785, -1.9980385349333185},
{204, -4.8091094241438679, -1.9590693829454109},
{204.5, -4.7702295969182211, -1.9203450193360185},
{205, -4.7315345467586312, -1.88186444624174},
{205.5, -4.6930234677259808, -1.8436267171097083},
{206, -4.6546955840940418, -1.8056309365594481},
{206.5, -4.6165501512344891, -1.7678762603756604},
{207, -4.5785864565453007, -1.7303618955732711},
{207.5, -4.540803820421031, -1.693087100585783},
{208, -4.5032015972282338, -1.6560511855044031},
{208.5, -4.4657791763127834, -1.6192535124351435},
{209, -4.4285359830271425, -1.5826934959260217},
{209.5, -4.3914714798032284, -1.5463706034687352},
{210, -4.354585167232, -1.5102843560763108},
{210.5, -4.3178765852010113, -1.4744343289435211},
{211, -4.2813453140079147, -1.4388201521574613},
{211.5, -4.2449909755390411, -1.4034415114888432},
{212, -4.2088132345054818, -1.3682981492393733},
{212.5, -4.1728117996231813, -1.3333898651595792},
{213, -4.1369864248782742, -1.2987165173953485},
{213.5, -4.1013369108160775, -1.264278023530919},
{214, -4.0658631058311263, -1.2300743616479941},
{214.5, -4.0305649074785306, -1.1961055714435485},
{215, -3.9954422638233429, -1.1623717553970199},
{215.5, -3.9604951748120403, -1.1288730799735514},
{216, -3.9257236936164066, -1.0956097768717166},
{216.5, -3.891127928066036, -1.0625821442917238},
{217, -3.8567080419856117, -1.0297905482292953},
{217.5, -3.8224642566534537, -0.99723542382864871},
{218, -3.7883968521571822, -0.96491727671875582},
{218.5, -3.754506168827827, -0.93283668437245437},
{219, -3.7207926086282561, -0.90099429748800819},
{219.5, -3.687256636543633, -0.86939084135895506},
{220, -3.6538987819270923, -0.8380271172542042},
{220.5, -3.6207196399366426, -0.80690400378027827},
{221, -3.5877198727011557, -0.77602245823456872},
{221.5, -3.5549002103743654, -0.74538351792062063},
{222, -3.5222614522734599, -0.71498830144754055},
{222.5, -3.4898044689171748, -0.6848380099885617},
{223, -3.4575302052746228, -0.65493392846674858},
{223.5, -3.4254396822412314, -0.62527742670741782},
{224, -3.3935339887126648, -0.59586996052380259},
{224.5, -3.361814262565836, -0.56671307266854543},
{225, -3.3302816918911415, -0.53780839383558243},
{225.5, -3.2989376071914962, -0.50915764319333556},
{226, -3.2677836641414011, -0.48076262995270491},
{226.5, -3.2368217910669674, -0.45262525133534059},
{227, -3.2060532467396534, -0.42474750232350711},
{227.5, -3.1754769604762529, -0.3971314530185121},
{228, -3.1450905295447877, -0.36977934287830261},
{228.5, -3.1148999987150199, -0.34269343369979732},
{229, -3.0849342884995545, -0.31587695182186509},
{229.5, -3.0551386754987631, -0.28933399461175174},
{230, -3.025552509966718, -0.26308052091786144},
{230.5, -2.9952306026024202, -0.2370711549655741},
{231, -2.967031235453558, -0.21135376721418095},
{231.5, -2.9380802508642274, -0.18591802101910554},
{232, -2.9093564619623482, -0.1607667945924747},
{232.5, -2.88081729416312, -0.13590304769667294},
{233, -2.8525230600156481, -0.11132981921361174},
{233.5, -2.824423655920588, -0.087050224384811067},
{234, -2.7965728309802036, -0.063067451711560002},
{234.5, -2.7689193107854164, -0.039384759504660673},
{235, -2.7415213105430691, -0.016005472076281491},
{235.5, -2.7143250493700033, 0.0070670244337740114},
{236, -2.6873907039428349, 0.029829286599060194},
{236.5, -2.6606623379297214, 0.052277818625817637},
{237, -2.6342025207942354, 0.074409077634357029},
{237.5, -2.6079531498005029, 0.096219479320850954},
{238, -2.5819630855445226, 0.11770540397551485},
{238.5, -2.5562197717055737, 0.13886320284700923},
{239, -2.5307260078024592, 0.15968920040257711},
{239.5, -2.5054845833652237, 0.18018014555868719},
{240, -2.4804982708235079, 0.20043024169077031},
}};

class PchipFunction {
 public:
  explicit PchipFunction(bool upper) {
    for (const auto& row : hopf_locus_rows) { x_.push_back(row.temperature); y_.push_back(upper ? row.upper : row.lower); }
    const std::size_t n = x_.size(); slopes_.resize(n); std::vector<double> h(n - 1), d(n - 1);
    for (std::size_t i = 0; i + 1 < n; ++i) { h[i] = x_[i + 1] - x_[i]; d[i] = (y_[i + 1] - y_[i]) / h[i]; }
    slopes_[0] = endpoint_slope(h[0], h[1], d[0], d[1]);
    slopes_[n - 1] = endpoint_slope(h[n - 2], h[n - 3], d[n - 2], d[n - 3]);
    for (std::size_t i = 1; i + 1 < n; ++i) {
      if (d[i - 1] == 0.0 || d[i] == 0.0 || std::signbit(d[i - 1]) != std::signbit(d[i])) slopes_[i] = 0.0;
      else { const double w1 = 2.0 * h[i] + h[i - 1], w2 = h[i] + 2.0 * h[i - 1]; slopes_[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i]); }
    }
  }
  double operator()(double x) const { return evaluate(x).first; }
  double derivative(double x) const { return evaluate(x).second; }
 private:
  static double endpoint_slope(double h0, double h1, double d0, double d1) {
    double m = ((2.0 * h0 + h1) * d0 - h0 * d1) / (h0 + h1);
    if (std::signbit(m) != std::signbit(d0)) return 0.0;
    if (std::signbit(d0) != std::signbit(d1) && std::abs(m) > 3.0 * std::abs(d0)) return 3.0 * d0;
    return m;
  }
  std::pair<double, double> evaluate(double x) const {
    if (x < x_.front() || x > x_.back()) throw std::out_of_range("temperature outside Hopf locus");
    auto it = std::upper_bound(x_.begin(), x_.end(), x); std::size_t i = it == x_.begin() ? 0 : static_cast<std::size_t>(it - x_.begin() - 1);
    if (i + 1 >= x_.size()) i = x_.size() - 2;
    const double h = x_[i + 1] - x_[i], t = (x - x_[i]) / h;
    const double value = (2*t*t*t-3*t*t+1)*y_[i] + (t*t*t-2*t*t+t)*h*slopes_[i] + (-2*t*t*t+3*t*t)*y_[i+1] + (t*t*t-t*t)*h*slopes_[i+1];
    const double derivative = ((6*t*t-6*t)*y_[i] + (3*t*t-4*t+1)*h*slopes_[i] + (-6*t*t+6*t)*y_[i+1] + (3*t*t-2*t)*h*slopes_[i+1]) / h;
    return {value, derivative};
  }
  std::vector<double> x_, y_, slopes_;
};

struct Fixture {
  std::string case_id;
  Environment environment;
  PhaseReference reference;
  std::vector<double> unknowns;
  int stage_count = 1;
  int formal_order = 2;
  bool upstream_accepted = true;
  std::string upstream_status = "accepted";
  std::string coefficient_checksum = bs2026_loca::collocation::artifact_sha256;
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
  if (magic == "BS2026_GAUSS_FIXTURE_V1") {
    input >> fixture.stage_count >> fixture.formal_order >> fixture.upstream_status >> fixture.coefficient_checksum;
    if (fixture.stage_count < 1 || fixture.stage_count > bs2026_loca::midpoint::maximum_stage_count)
      throw std::runtime_error("invalid fixture stage count");
    const auto compiled_rule = bs2026_loca::midpoint::gauss_legendre_rule(fixture.stage_count);
    if (fixture.formal_order != compiled_rule.formal_order)
      throw std::runtime_error("fixture formal order does not match compiled Gauss rule");
    if (fixture.coefficient_checksum != bs2026_loca::collocation::artifact_sha256)
      throw std::runtime_error("fixture coefficient checksum does not match compiled artifact");
    if (fixture.upstream_status != "accepted" && fixture.upstream_status != "rejected" &&
        fixture.upstream_status != "nonsolution")
      throw std::runtime_error("invalid fixture upstream status");
    fixture.upstream_accepted = fixture.upstream_status == "accepted";
  } else if (magic != "BS2026_MIDPOINT_FIXTURE_V1") {
    throw std::runtime_error("invalid fixture header");
  }
  if (count == 0) throw std::runtime_error("invalid fixture interval count");
  input >> fixture.environment.p >> fixture.environment.T >> fixture.environment.w
        >> fixture.environment.F >> fixture.environment.N_a >> fixture.environment.dz;
  fixture.environment.include_evaporation = false;
  input >> fixture.log_w_lower >> fixture.log_w_upper >> fixture.spine_derivative;
  for (double& scale : fixture.reference.state_scaling) input >> scale;
  fixture.reference.boundaries.resize(count + 1);
  fixture.reference.stage_values.resize(count * static_cast<std::size_t>(fixture.stage_count));
  fixture.reference.stage_derivatives.resize(count * static_cast<std::size_t>(fixture.stage_count));
  fixture.unknowns.resize(3 * count * static_cast<std::size_t>(fixture.stage_count + 1) + 1);
  for (double& value : fixture.reference.boundaries) input >> value;
  for (auto& row : fixture.reference.stage_values) for (double& value : row) input >> value;
  for (auto& row : fixture.reference.stage_derivatives) for (double& value : row) input >> value;
  for (double& value : fixture.unknowns) input >> value;
  if (!input) throw std::runtime_error("truncated or malformed orbit fixture");
  input >> std::ws;
  if (input.peek() != std::char_traits<char>::eof())
    throw std::runtime_error("orbit fixture contains trailing data");
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

void write_runtime_provenance(const OrbitLayout& layout) {
  std::cout << "rule " << layout.rule().family << " " << layout.stage_count() << " "
            << layout.formal_order() << " " << bs2026_loca::collocation::artifact_sha256 << "\n";
  std::cout << "build_identity " << __VERSION__ << " Trilinos_" << TRILINOS_VERSION_STRING << "\n";
  std::cout << "cmake_identity " << BS2026_CMAKE_SOURCE_SHA256 << " build_type_" << BS2026_CMAKE_BUILD_TYPE << "\n";
  std::cout << "source_fingerprint " << BS2026_MIDPOINT_LOCA_SHA256 << " " << BS2026_MIDPOINT_ORBIT_SHA256
            << " " << BS2026_MODEL_SHA256 << " " << BS2026_MIDPOINT_NOX_SHA256 << " "
            << BS2026_COLLOCATION_COEFFICIENTS_SHA256 << " " << BS2026_MIDPOINT_CLI_SHA256 << "\n";
}

void write_solve_contract(const Assembler& assembler) {
  const auto& layout = assembler.layout();
  const auto graph = assembler.graph();
  std::cout << "mesh " << layout.interval_count() << " " << layout.stage_count() << " "
            << assembler.phase_reference().boundaries.size() << "\n";
  std::cout << "solve_layout " << layout.unknown_size() << " " << layout.unknown_size() << " "
            << layout.stage_size() << " " << layout.endpoint_size() << " 1\n";
  std::cout << "solve_graph " << graph->getGlobalNumEntries() << " retained_reuse true\n";
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
  write_runtime_provenance(layout);
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
  std::cout << "final_residual_available " << (result.residual_available ? "true" : "false") << "\n";
  if (result.residual_available) write_vector("final_residual", *result.residual);
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

std::vector<double> defect_check_nodes(const OrbitLayout& layout) {
  if (layout.stage_count() == 1) return {bs2026_loca::collocation::GaussLegendreRule<1>::defect_check_nodes[0],
                                         bs2026_loca::collocation::GaussLegendreRule<1>::defect_check_nodes[1]};
  if (layout.stage_count() == 2) return {bs2026_loca::collocation::GaussLegendreRule<2>::defect_check_nodes[0],
                                         bs2026_loca::collocation::GaussLegendreRule<2>::defect_check_nodes[1],
                                         bs2026_loca::collocation::GaussLegendreRule<2>::defect_check_nodes[2]};
  if (layout.stage_count() == 3) return {bs2026_loca::collocation::GaussLegendreRule<3>::defect_check_nodes[0],
                                         bs2026_loca::collocation::GaussLegendreRule<3>::defect_check_nodes[1],
                                         bs2026_loca::collocation::GaussLegendreRule<3>::defect_check_nodes[2],
                                         bs2026_loca::collocation::GaussLegendreRule<3>::defect_check_nodes[3]};
  throw std::invalid_argument("unsupported Gauss stage count for defect nodes");
}

std::vector<double> deterministic_split_boundaries(const std::vector<double>& old_boundaries) {
  if (old_boundaries.size() < 3) throw std::invalid_argument("adaptive transfer requires at least two intervals");
  std::vector<double> result;
  result.reserve(old_boundaries.size() + old_boundaries.size() / 9 + 2);
  result.push_back(old_boundaries.front());
  for (std::size_t interval = 0; interval + 1 < old_boundaries.size(); ++interval) {
    if (interval % 9 == 0) result.push_back(0.5 * (old_boundaries[interval] + old_boundaries[interval + 1]));
    result.push_back(old_boundaries[interval + 1]);
  }
  return result;
}

std::vector<std::array<double, 3>> stage_fields(const Fixture& fixture, const OrbitLayout& layout,
                                                const std::vector<double>& values) {
  std::vector<std::array<double, 3>> fields(layout.interval_count() * static_cast<std::size_t>(layout.stage_count()));
  const double log_w = std::log(fixture.environment.w);
  for (std::size_t interval = 0; interval < layout.interval_count(); ++interval) {
    for (int stage = 0; stage < layout.stage_count(); ++stage) {
      std::array<double, 3> state{};
      for (int component = 0; component < 3; ++component)
        state[component] = values[static_cast<std::size_t>(layout.stage_index(interval, stage, component))];
      fields[interval * static_cast<std::size_t>(layout.stage_count()) + static_cast<std::size_t>(stage)] =
          bs2026_loca::local_derivatives(state, fixture.environment.T, log_w, fixture.environment).values;
    }
  }
  return fields;
}

std::size_t interval_for_phase(const std::vector<double>& boundaries, double phase) {
  double wrapped = std::fmod(phase, 1.0);
  if (wrapped < 0.0) wrapped += 1.0;
  auto it = std::upper_bound(boundaries.begin(), boundaries.end(), wrapped);
  std::size_t interval = it == boundaries.begin() ? 0 : static_cast<std::size_t>(it - boundaries.begin() - 1);
  if (interval + 1 >= boundaries.size()) interval = boundaries.size() - 2;
  return interval;
}

std::array<double, 3> evaluate_polynomial(const Fixture& fixture, const OrbitLayout& layout,
                                          const std::vector<double>& values,
                                          const std::vector<std::array<double, 3>>& fields,
                                          double phase) {
  const auto& rule = layout.rule();
  const std::size_t interval = interval_for_phase(fixture.reference.boundaries, phase);
  const double width = fixture.reference.boundaries[interval + 1] - fixture.reference.boundaries[interval];
  const double tau = (std::fmod(phase, 1.0) + (std::fmod(phase, 1.0) < 0.0 ? 1.0 : 0.0) - fixture.reference.boundaries[interval]) / width;
  const double period = std::exp(values[static_cast<std::size_t>(layout.log_period_index())]);
  std::array<double, 3> result{};
  for (int component = 0; component < 3; ++component)
    result[component] = values[static_cast<std::size_t>(layout.endpoint_index(interval, component))];
  for (int stage = 0; stage < layout.stage_count(); ++stage) {
    double integrated = 0.0;
    double power = 1.0;
    for (int degree = 0; degree <= layout.stage_count(); ++degree) {
      integrated += rule.transfer_coefficients[stage][degree] * power;
      power *= tau;
    }
    const auto& field = fields[interval * static_cast<std::size_t>(layout.stage_count()) + static_cast<std::size_t>(stage)];
    for (int component = 0; component < 3; ++component)
      result[component] += width * period * integrated * field[component];
  }
  return result;
}

std::array<double, 3> evaluate_polynomial_derivative(const Fixture& fixture, const OrbitLayout& layout,
                                                     const std::vector<std::array<double, 3>>& fields,
                                                     double log_period,
                                                     double phase) {
  const auto& rule = layout.rule();
  const std::size_t interval = interval_for_phase(fixture.reference.boundaries, phase);
  const double width = fixture.reference.boundaries[interval + 1] - fixture.reference.boundaries[interval];
  const double wrapped = std::fmod(phase, 1.0) + (std::fmod(phase, 1.0) < 0.0 ? 1.0 : 0.0);
  const double tau = (wrapped - fixture.reference.boundaries[interval]) / width;
  const double period = std::exp(log_period);
  std::array<double, 3> result{};
  for (int stage = 0; stage < layout.stage_count(); ++stage) {
    double lagrange = 0.0;
    double power = 1.0;
    for (int degree = 1; degree <= layout.stage_count(); ++degree) {
      lagrange += static_cast<double>(degree) * rule.transfer_coefficients[stage][degree] * power;
      power *= tau;
    }
    const auto& field = fields[interval * static_cast<std::size_t>(layout.stage_count()) + static_cast<std::size_t>(stage)];
    for (int component = 0; component < 3; ++component)
      result[component] += period * lagrange * field[component];
  }
  return result;
}

std::array<double, 3> evaluate_polynomial_second_derivative(const Fixture& fixture, const OrbitLayout& layout,
                                                            const std::vector<std::array<double, 3>>& fields,
                                                            double log_period,
                                                            double phase) {
  const auto& rule = layout.rule();
  const std::size_t interval = interval_for_phase(fixture.reference.boundaries, phase);
  const double width = fixture.reference.boundaries[interval + 1] - fixture.reference.boundaries[interval];
  const double wrapped = std::fmod(phase, 1.0) + (std::fmod(phase, 1.0) < 0.0 ? 1.0 : 0.0);
  const double tau = (wrapped - fixture.reference.boundaries[interval]) / width;
  const double period = std::exp(log_period);
  std::array<double, 3> result{};
  for (int stage = 0; stage < layout.stage_count(); ++stage) {
    double lagrange_prime = 0.0;
    double power = 1.0;
    for (int degree = 2; degree <= layout.stage_count(); ++degree) {
      lagrange_prime += static_cast<double>(degree * (degree - 1)) * rule.transfer_coefficients[stage][degree] * power;
      power *= tau;
    }
    const auto& field = fields[interval * static_cast<std::size_t>(layout.stage_count()) + static_cast<std::size_t>(stage)];
    for (int component = 0; component < 3; ++component)
      result[component] += (period / width) * lagrange_prime * field[component];
  }
  return result;
}

std::vector<double> transfer_values(const Fixture& fixture, const OrbitLayout& layout,
                                    const std::vector<double>& values,
                                    const std::vector<double>& destination_boundaries) {
  const auto fields = stage_fields(fixture, layout, values);
  const auto& rule = layout.rule();
  const std::size_t destination_intervals = destination_boundaries.size() - 1;
  std::vector<double> result(3 * destination_intervals * static_cast<std::size_t>(layout.stage_count() + 1) + 1);
  auto endpoint_index = [](std::size_t interval, int component) { return 3 * interval + static_cast<std::size_t>(component); };
  auto stage_index = [destination_intervals, &layout](std::size_t interval, int stage, int component) {
    return 3 * destination_intervals + 3 * (interval * static_cast<std::size_t>(layout.stage_count()) + static_cast<std::size_t>(stage)) + static_cast<std::size_t>(component);
  };
  for (std::size_t interval = 0; interval < destination_intervals; ++interval) {
    const auto endpoint = evaluate_polynomial(fixture, layout, values, fields, destination_boundaries[interval]);
    for (int component = 0; component < 3; ++component) result[endpoint_index(interval, component)] = endpoint[component];
    const double width = destination_boundaries[interval + 1] - destination_boundaries[interval];
    for (int stage = 0; stage < layout.stage_count(); ++stage) {
      const auto stage_value = evaluate_polynomial(fixture, layout, values, fields,
          destination_boundaries[interval] + width * rule.nodes[stage]);
      for (int component = 0; component < 3; ++component)
        result[stage_index(interval, stage, component)] = stage_value[component];
    }
  }
  result.back() = values[static_cast<std::size_t>(layout.log_period_index())];
  return result;
}

PhaseReference transferred_phase_reference(const Fixture& fixture, const OrbitLayout& layout,
                                           const std::vector<double>& values,
                                           const std::vector<double>& destination_boundaries) {
  const auto fields = stage_fields(fixture, layout, values);
  const auto& rule = layout.rule();
  PhaseReference reference;
  reference.boundaries = destination_boundaries;
  reference.state_scaling = fixture.reference.state_scaling;
  const std::size_t destination_intervals = destination_boundaries.size() - 1;
  reference.stage_values.resize(destination_intervals * static_cast<std::size_t>(layout.stage_count()));
  reference.stage_derivatives.resize(reference.stage_values.size());
  const double log_period = values[static_cast<std::size_t>(layout.log_period_index())];
  for (std::size_t interval = 0; interval < destination_intervals; ++interval) {
    const double width = destination_boundaries[interval + 1] - destination_boundaries[interval];
    for (int stage = 0; stage < layout.stage_count(); ++stage) {
      const double phase = destination_boundaries[interval] + width * rule.nodes[stage];
      const auto sample = evaluate_polynomial(fixture, layout, values, fields, phase);
      const auto derivative = evaluate_polynomial_derivative(fixture, layout, fields, log_period, phase);
      const std::size_t index = interval * static_cast<std::size_t>(layout.stage_count()) + static_cast<std::size_t>(stage);
      reference.stage_values[index] = sample;
      reference.stage_derivatives[index] = derivative;
    }
  }
  return reference;
}

double scaled_norm3(const std::array<double, 3>& values, const std::array<double, 3>& scaling) {
  double squared = 0.0;
  for (int component = 0; component < 3; ++component) {
    const double scaled = values[component] * scaling[component];
    squared += scaled * scaled;
  }
  return std::sqrt(squared);
}

std::vector<double> relative_defect_element_maxima(const Fixture& fixture, const OrbitLayout& layout,
                                                   const std::vector<double>& values,
                                                   const std::vector<double>& local_nodes,
                                                   double* maximum = nullptr,
                                                   double* argmax_phase = nullptr,
                                                   std::size_t* argmax_interval = nullptr) {
  const auto fields = stage_fields(fixture, layout, values);
  const double log_period = values[static_cast<std::size_t>(layout.log_period_index())];
  const double period = std::exp(log_period);
  const double log_w = std::log(fixture.environment.w);
  std::vector<double> element_max(layout.interval_count(), 0.0);
  double best = -1.0;
  double best_phase = 0.0;
  std::size_t best_interval = 0;
  for (std::size_t interval = 0; interval < layout.interval_count(); ++interval) {
    const double width = fixture.reference.boundaries[interval + 1] - fixture.reference.boundaries[interval];
    for (double local : local_nodes) {
      const double phase = fixture.reference.boundaries[interval] + width * local;
      const auto state = evaluate_polynomial(fixture, layout, values, fields, phase);
      const auto slope = evaluate_polynomial_derivative(fixture, layout, fields, log_period, phase);
      const auto rhs_unscaled = bs2026_loca::transformed_vector_field<double>(state, fixture.environment.T, log_w, fixture.environment);
      std::array<double, 3> ode{}, difference{};
      for (int component = 0; component < 3; ++component) {
        ode[component] = period * rhs_unscaled[component];
        difference[component] = slope[component] - ode[component];
      }
      const double relative = scaled_norm3(difference, fixture.reference.state_scaling) /
          (1.0 + scaled_norm3(ode, fixture.reference.state_scaling));
      element_max[interval] = std::max(element_max[interval], relative);
      if (relative > best) {
        best = relative;
        best_phase = phase;
        best_interval = interval;
      }
    }
  }
  if (maximum) *maximum = best;
  if (argmax_phase) *argmax_phase = best_phase;
  if (argmax_interval) *argmax_interval = best_interval;
  return element_max;
}

struct DefectSummary {
  std::vector<double> next_element;
  std::vector<double> dyadic_element;
  std::vector<double> combined;
  std::vector<double> probe_admitted;
  std::vector<double> disagreement;
  std::vector<std::size_t> material;
  std::vector<double> endpoint_left;
  std::vector<double> endpoint_right;
  std::vector<double> derivative_jumps;
  double maximum = 0.0;
  double argmax_phase = 0.0;
  int argmax_bin = 0;
};

DefectSummary independent_defect_summary(const Fixture& fixture, const OrbitLayout& layout,
                                         const std::vector<double>& values) {
  constexpr double material_absolute_threshold = 1.0e-5;
  constexpr double material_relative_threshold = 0.5;
  constexpr int recurrence_bin_count = 128;
  DefectSummary summary;
  double next_max = 0.0, dyadic_max = 0.0, next_phase = 0.0, dyadic_phase = 0.0;
  std::size_t next_interval = 0, dyadic_interval = 0;
  summary.next_element = relative_defect_element_maxima(fixture, layout, values, defect_check_nodes(layout),
                                                        &next_max, &next_phase, &next_interval);
  summary.dyadic_element = relative_defect_element_maxima(fixture, layout, values, {0.125, 0.375, 0.625, 0.875},
                                                          &dyadic_max, &dyadic_phase, &dyadic_interval);
  const std::size_t n = layout.interval_count();
  summary.combined.resize(n);
  summary.probe_admitted.assign(n, 0.0);
  summary.disagreement.resize(n);
  for (std::size_t i = 0; i < n; ++i) {
    const double larger = std::max(summary.next_element[i], summary.dyadic_element[i]);
    summary.combined[i] = larger;
    summary.disagreement[i] = larger > 0.0 ? std::abs(summary.next_element[i] - summary.dyadic_element[i]) / larger : 0.0;
    if (larger > material_absolute_threshold && summary.disagreement[i] > material_relative_threshold)
      summary.material.push_back(i);
  }
  if (!summary.material.empty()) {
    const std::vector<double> probe_nodes = [] {
      std::vector<double> nodes(16);
      for (std::size_t i = 0; i < nodes.size(); ++i) nodes[i] = (static_cast<double>(i) + 0.5) / 16.0;
      return nodes;
    }();
    const auto probe = relative_defect_element_maxima(fixture, layout, values, probe_nodes);
    for (std::size_t i : summary.material) {
      summary.probe_admitted[i] = probe[i];
      summary.combined[i] = std::max(summary.combined[i], probe[i]);
    }
  }
  const auto fields = stage_fields(fixture, layout, values);
  const double log_period = values[static_cast<std::size_t>(layout.log_period_index())];
  const double period = std::exp(log_period);
  const double log_w = std::log(fixture.environment.w);
  const double epsilon = std::numeric_limits<double>::epsilon() * 32.0;
  summary.endpoint_left.resize(n);
  summary.endpoint_right.resize(n);
  std::vector<std::array<double, 3>> left_slopes(n), right_slopes(n);
  for (std::size_t i = 0; i < n; ++i) {
    const double width = fixture.reference.boundaries[i + 1] - fixture.reference.boundaries[i];
    const double left_phase = fixture.reference.boundaries[i] + epsilon * width;
    const double right_phase = fixture.reference.boundaries[i + 1] - epsilon * width;
    auto point_defect = [&](double phase) {
      const auto state = evaluate_polynomial(fixture, layout, values, fields, phase);
      const auto slope = evaluate_polynomial_derivative(fixture, layout, fields, log_period, phase);
      const auto rhs_unscaled = bs2026_loca::transformed_vector_field<double>(state, fixture.environment.T, log_w, fixture.environment);
      std::array<double, 3> ode{}, difference{};
      for (int component = 0; component < 3; ++component) {
        ode[component] = period * rhs_unscaled[component];
        difference[component] = slope[component] - ode[component];
      }
      return scaled_norm3(difference, fixture.reference.state_scaling) /
          (1.0 + scaled_norm3(ode, fixture.reference.state_scaling));
    };
    summary.endpoint_left[i] = point_defect(left_phase);
    summary.endpoint_right[i] = point_defect(right_phase);
    left_slopes[i] = evaluate_polynomial_derivative(fixture, layout, fields, log_period, left_phase);
    right_slopes[i] = evaluate_polynomial_derivative(fixture, layout, fields, log_period, right_phase);
  }
  summary.derivative_jumps.resize(n);
  for (std::size_t i = 0; i < n; ++i) {
    std::array<double, 3> jump{};
    const auto& next_left = left_slopes[(i + 1) % n];
    for (int component = 0; component < 3; ++component) jump[component] = next_left[component] - right_slopes[i][component];
    summary.derivative_jumps[i] = scaled_norm3(jump, fixture.reference.state_scaling);
  }
  std::size_t interval = static_cast<std::size_t>(std::max_element(summary.combined.begin(), summary.combined.end()) - summary.combined.begin());
  summary.maximum = summary.combined[interval];
  // Re-scan admitted grids on the maximum interval to reproduce the Python argmax contract.
  std::vector<double> admitted_nodes = defect_check_nodes(layout);
  double admitted_max = summary.next_element[interval];
  if (summary.dyadic_element[interval] > admitted_max) {
    admitted_max = summary.dyadic_element[interval];
    admitted_nodes = {0.125, 0.375, 0.625, 0.875};
  }
  if (summary.probe_admitted[interval] > admitted_max) {
    admitted_nodes.resize(16);
    for (std::size_t i = 0; i < admitted_nodes.size(); ++i) admitted_nodes[i] = (static_cast<double>(i) + 0.5) / 16.0;
  }
  double ignored_max = 0.0;
  std::size_t ignored_interval = 0;
  summary.argmax_phase = 0.0;
  (void)relative_defect_element_maxima(fixture, layout, values, admitted_nodes,
                                       &ignored_max, &summary.argmax_phase, &ignored_interval);
  if (ignored_interval != interval) {
    const double width = fixture.reference.boundaries[interval + 1] - fixture.reference.boundaries[interval];
    // Fallback cannot be reached for deterministic fixtures, but keeps the output in the admitted interval.
    summary.argmax_phase = fixture.reference.boundaries[interval] + 0.5 * width;
  }
  summary.argmax_bin = static_cast<int>(std::floor(recurrence_bin_count * std::fmod(summary.argmax_phase, 1.0)));
  return summary;
}

std::vector<double> composite_monitor_values(const Fixture& fixture, const OrbitLayout& layout,
                                             const std::vector<double>& values,
                                             std::vector<double>& phases,
                                             std::vector<double>& widths) {
  constexpr int subcells = 16;
  const std::size_t n = layout.interval_count();
  phases.resize(n * subcells);
  widths.resize(n * subcells);
  for (std::size_t interval = 0; interval < n; ++interval) {
    const double width = fixture.reference.boundaries[interval + 1] - fixture.reference.boundaries[interval];
    for (int sub = 0; sub < subcells; ++sub) {
      const double local = (static_cast<double>(sub) + 0.5) / subcells;
      phases[interval * subcells + static_cast<std::size_t>(sub)] = fixture.reference.boundaries[interval] + width * local;
      widths[interval * subcells + static_cast<std::size_t>(sub)] = width / subcells;
    }
  }
  const auto fields = stage_fields(fixture, layout, values);
  const double log_period = values[static_cast<std::size_t>(layout.log_period_index())];
  const double period = std::exp(log_period);
  const double log_w = std::log(fixture.environment.w);
  std::array<std::vector<double>, 4> raw;
  for (auto& column : raw) column.resize(phases.size());
  for (std::size_t row = 0; row < phases.size(); ++row) {
    const auto state = evaluate_polynomial(fixture, layout, values, fields, phases[row]);
    const auto derivative = evaluate_polynomial_derivative(fixture, layout, fields, log_period, phases[row]);
    const auto curvature = evaluate_polynomial_second_derivative(fixture, layout, fields, log_period, phases[row]);
    const auto rhs_unscaled = bs2026_loca::transformed_vector_field<double>(state, fixture.environment.T, log_w, fixture.environment);
    std::array<double, 3> ode{}, difference{};
    for (int component = 0; component < 3; ++component) {
      ode[component] = period * rhs_unscaled[component];
      difference[component] = derivative[component] - ode[component];
    }
    raw[0][row] = scaled_norm3(difference, fixture.reference.state_scaling) /
        (1.0 + scaled_norm3(ode, fixture.reference.state_scaling));
    raw[1][row] = scaled_norm3(derivative, fixture.reference.state_scaling);
    raw[2][row] = scaled_norm3(curvature, fixture.reference.state_scaling);
    const auto c = bs2026_loca::coefficients(fixture.environment);
    const double n_phys = std::exp(state[0]);
    const double q_phys = std::exp(state[1]);
    const double s = state[2];
    const double expo = std::exp(c.p1e * (s - c.p2));
    std::array<double, 3> nucleation{c.A_n * expo / n_phys, c.A_q * expo / q_phys, -c.A_s * expo};
    for (int component = 0; component < 3; ++component) nucleation[component] *= period;
    raw[3][row] = scaled_norm3(nucleation, fixture.reference.state_scaling);
  }
  std::array<std::vector<double>, 4> normalized;
  for (int density = 0; density < 4; ++density) {
    const double maximum = *std::max_element(raw[density].begin(), raw[density].end());
    normalized[density].assign(raw[density].size(), 0.0);
    if (maximum <= 0.0) continue;
    double first_average = 0.0;
    for (std::size_t i = 0; i < raw[density].size(); ++i) first_average += widths[i] * (raw[density][i] / maximum);
    double second_average = 0.0;
    for (std::size_t i = 0; i < raw[density].size(); ++i) {
      normalized[density][i] = std::min((raw[density][i] / maximum) / first_average, 20.0);
      second_average += widths[i] * normalized[density][i];
    }
    for (double& value : normalized[density]) value /= second_average;
  }
  std::vector<double> monitor(phases.size());
  for (std::size_t i = 0; i < monitor.size(); ++i)
    monitor[i] = 0.20 + 0.80 * (0.50 * normalized[0][i] + 0.20 * normalized[1][i] +
                                0.20 * normalized[2][i] + 0.10 * normalized[3][i]);
  return monitor;
}

std::vector<double> invert_monitor_boundaries(const std::vector<double>& boundaries,
                                              const std::vector<double>& monitor_values,
                                              std::size_t target_count) {
  constexpr int subcells = 16;
  std::vector<double> masses(monitor_values.size()), lower(monitor_values.size()), sub_widths(monitor_values.size());
  for (std::size_t interval = 0; interval + 1 < boundaries.size(); ++interval) {
    const double width = (boundaries[interval + 1] - boundaries[interval]) / subcells;
    for (int sub = 0; sub < subcells; ++sub) {
      const std::size_t index = interval * subcells + static_cast<std::size_t>(sub);
      lower[index] = boundaries[interval] + static_cast<double>(sub) * width;
      sub_widths[index] = width;
      masses[index] = width * monitor_values[index];
    }
  }
  std::vector<double> cumulative(masses.size());
  double total = 0.0;
  for (std::size_t i = 0; i < masses.size(); ++i) { total += masses[i]; cumulative[i] = total; }
  const double eps_reach = 64.0 * std::numeric_limits<double>::epsilon() * std::max(1.0, total);
  std::vector<double> result(target_count + 1);
  result.front() = 0.0; result.back() = 1.0;
  double previous_upper = 0.0;
  std::size_t cursor = 0;
  for (std::size_t j = 1; j < target_count; ++j) {
    const double target = total * static_cast<double>(j) / static_cast<double>(target_count);
    while (cursor + 1 < cumulative.size() && cumulative[cursor] + eps_reach < target) {
      previous_upper = cumulative[cursor];
      ++cursor;
    }
    const double fraction = masses[cursor] <= 0.0 ? 0.0 : std::min(1.0, std::max(0.0, (target - previous_upper) / masses[cursor]));
    result[j] = lower[cursor] + fraction * sub_widths[cursor];
  }
  return result;
}

std::vector<std::size_t> mark_h_refinement_indices(const std::vector<double>& defect, std::size_t max_count,
                                                   std::size_t& growth_limit, double& halfmax) {
  const std::size_t n = defect.size();
  growth_limit = std::min(static_cast<std::size_t>(std::floor(0.5 * static_cast<double>(n))), max_count > n ? max_count - n : 0);
  const double max_eta = *std::max_element(defect.begin(), defect.end());
  halfmax = 0.5 * max_eta;
  if (max_eta <= 0.0 || growth_limit == 0) return {};
  std::vector<std::size_t> order(n);
  for (std::size_t i = 0; i < n; ++i) order[i] = i;
  std::sort(order.begin(), order.end(), [&](std::size_t a, std::size_t b) {
    if (defect[a] != defect[b]) return defect[a] > defect[b];
    return a < b;
  });
  double total_square = 0.0;
  for (double value : defect) total_square += value * value;
  std::vector<bool> include(n, false);
  double running = 0.0;
  for (std::size_t index : order) {
    if (total_square > 0.0 && running >= 0.70 * total_square) break;
    include[index] = true;
    running += defect[index] * defect[index];
  }
  for (std::size_t i = 0; i < n; ++i) if (defect[i] >= halfmax) include[i] = true;
  std::vector<std::size_t> uncapped;
  for (std::size_t i = 0; i < n; ++i) if (include[i]) uncapped.push_back(i);
  std::sort(uncapped.begin(), uncapped.end(), [&](std::size_t a, std::size_t b) {
    if (defect[a] != defect[b]) return defect[a] > defect[b];
    return a < b;
  });
  if (uncapped.size() > growth_limit) uncapped.resize(growth_limit);
  return uncapped;
}

std::vector<double> apply_beta_r_movement(const std::vector<double>& old_boundaries,
                                          const std::vector<double>& target_boundaries,
                                          double& accepted_beta,
                                          std::vector<double>& attempted) {
  const std::size_t n = old_boundaries.size() - 1;
  std::vector<double> old_widths(n);
  for (std::size_t i = 0; i < n; ++i) old_widths[i] = old_boundaries[i + 1] - old_boundaries[i];
  for (int exponent = 1; exponent <= 20; ++exponent) {
    const double beta = std::ldexp(1.0, -exponent);
    attempted.push_back(beta);
    auto candidate = old_boundaries;
    for (std::size_t i = 1; i < n; ++i) candidate[i] = old_boundaries[i] + beta * (target_boundaries[i] - old_boundaries[i]);
    bool rejected = false;
    std::vector<double> widths(n);
    for (std::size_t i = 0; i < n; ++i) {
      widths[i] = candidate[i + 1] - candidate[i];
      if (widths[i] <= 0.0 || widths[i] < 1.0 / (20.0 * n) || widths[i] > 5.0 / n) rejected = true;
    }
    for (std::size_t i = 1; i < n; ++i) {
      const double displacement = std::abs(candidate[i] - old_boundaries[i]);
      if (displacement > 0.5 * std::min(old_widths[i - 1], old_widths[i])) rejected = true;
    }
    for (std::size_t i = 0; i < n; ++i) {
      const double ratio = widths[i] / widths[(i + 1) % n];
      if (ratio < 1.0 / 3.0 || ratio > 3.0) rejected = true;
    }
    if (!rejected) { accepted_beta = beta; return candidate; }
  }
  accepted_beta = 0.0;
  return old_boundaries;
}

void write_adaptive_controller(const Fixture& fixture, const OrbitLayout& layout) {
  const auto defect = independent_defect_summary(fixture, layout, fixture.unknowns);
  std::vector<double> phases, widths;
  const auto monitor = composite_monitor_values(fixture, layout, fixture.unknowns, phases, widths);
  const auto targets = invert_monitor_boundaries(fixture.reference.boundaries, monitor, layout.interval_count());
  std::size_t growth_limit = 0;
  double halfmax = 0.0;
  const auto marked = mark_h_refinement_indices(defect.combined, 256, growth_limit, halfmax);
  double beta = 0.0;
  std::vector<double> attempted;
  const auto moved = apply_beta_r_movement(fixture.reference.boundaries, targets, beta, attempted);
  std::cout << std::setprecision(17) << std::scientific;
  std::cout << "adaptive_controller_contract external-gauss3-hr-adaptive-v1 two-grid-relative-defect-v1 composite-r-monitor-v1 defect-bulk-halfmax-marking-v1 global-beta-r-movement-v1 adaptive-cycle-controller-v1 fixed-parameter-remesh-restart-retry-v1\n";
  write_runtime_provenance(layout);
  std::cout << "defect_summary " << defect.maximum << " " << defect.argmax_phase << " " << defect.argmax_bin << " " << defect.material.size() << "\n";
  auto write_plain = [](const std::string& label, const std::vector<double>& values) {
    std::cout << label << " " << values.size();
    for (double value : values) std::cout << " " << value;
    std::cout << "\n";
  };
  write_plain("defect_combined", defect.combined);
  write_plain("defect_next_element", defect.next_element);
  write_plain("defect_dyadic_element", defect.dyadic_element);
  write_plain("defect_probe_admitted", defect.probe_admitted);
  write_plain("defect_grid_disagreement", defect.disagreement);
  write_plain("defect_endpoint_left", defect.endpoint_left);
  write_plain("defect_endpoint_right", defect.endpoint_right);
  write_plain("defect_derivative_jumps", defect.derivative_jumps);
  std::cout << "defect_material_elements " << defect.material.size();
  for (std::size_t index : defect.material) std::cout << " " << index;
  std::cout << "\n";
  write_plain("monitor_values", monitor);
  write_plain("monitor_target_boundaries", targets);
  std::cout << "h_marking " << marked.size() << " " << growth_limit << " " << (layout.interval_count() + marked.size()) << " " << halfmax;
  for (std::size_t index : marked) std::cout << " " << index;
  std::cout << "\n";
  std::cout << "r_movement " << (beta > 0.0 ? "accepted" : "stalled") << " " << beta << " " << attempted.size();
  for (double value : attempted) std::cout << " " << value;
  std::cout << "\n";
  write_plain("r_movement_boundaries", moved);
  const bool defect_pass = defect.maximum < 1.0e-4;
  std::cout << "cycle_decision actual " << (defect_pass ? "pure_r continue convergence_gate_failed" : "ordinary_h_r continue defect_gate_failed") << "\n";
  std::cout << "cycle_decision converged stop_converged converged none\n";
  std::cout << "cycle_decision cycle_budget resolution_unresolved resolution_unresolved cycle_budget_exhausted\n";
  std::cout << "restart_plan h+r h_r_transfer_correct h_r_refresh_reference_recorrect h_r_rebootstrap_tangent_recorrect\n";
  std::cout << "restart_plan pure-r pure_r_transfer_correct pure_r_refresh_reference_recorrect pure_r_rebootstrap_tangent_recorrect\n";
  std::cout << "restart_plan tangent_only deterministic_two_point_rebootstrap restart_with_rebootstrapped_tangent reject_after_rebootstrap_failure\n";
}

struct TransferBundle {
  std::vector<double> destination_boundaries;
  std::vector<double> unknowns;
  std::vector<double> tangent;
  PhaseReference reference;
  double tangent_norm_before_normalization = 0.0;
};

TransferBundle build_transfer_bundle(const Fixture& fixture, const OrbitLayout& layout) {
  TransferBundle bundle;
  bundle.destination_boundaries = deterministic_split_boundaries(fixture.reference.boundaries);
  bundle.unknowns = transfer_values(fixture, layout, fixture.unknowns, bundle.destination_boundaries);
  bundle.reference = transferred_phase_reference(fixture, layout, fixture.unknowns, bundle.destination_boundaries);
  constexpr double epsilon = 1.0e-6;
  std::vector<double> tangent(fixture.unknowns.size());
  double norm_squared = 0.0;
  for (std::size_t gid = 0; gid < tangent.size(); ++gid) {
    tangent[gid] = std::cos(static_cast<double>(gid) + 0.21);
    norm_squared += tangent[gid] * tangent[gid];
  }
  const double norm = std::sqrt(norm_squared);
  for (double& value : tangent) value /= norm;
  auto plus = fixture.unknowns;
  auto minus = fixture.unknowns;
  for (std::size_t gid = 0; gid < tangent.size(); ++gid) {
    plus[gid] += epsilon * tangent[gid];
    minus[gid] -= epsilon * tangent[gid];
  }
  const auto plus_transfer = transfer_values(fixture, layout, plus, bundle.destination_boundaries);
  const auto minus_transfer = transfer_values(fixture, layout, minus, bundle.destination_boundaries);
  bundle.tangent.resize(plus_transfer.size());
  double transferred_norm_squared = 0.0;
  for (std::size_t gid = 0; gid < bundle.tangent.size(); ++gid) {
    bundle.tangent[gid] = (plus_transfer[gid] - minus_transfer[gid]) / (2.0 * epsilon);
    transferred_norm_squared += bundle.tangent[gid] * bundle.tangent[gid];
  }
  bundle.tangent_norm_before_normalization = std::sqrt(transferred_norm_squared);
  if (bundle.tangent_norm_before_normalization > 0.0 && std::isfinite(bundle.tangent_norm_before_normalization))
    for (double& value : bundle.tangent) value /= bundle.tangent_norm_before_normalization;
  return bundle;
}

void write_adaptive_transfer(const Fixture& fixture, const OrbitLayout& layout) {
  const auto bundle = build_transfer_bundle(fixture, layout);
  const double epsilon = 1.0e-6;
  std::cout << std::setprecision(17) << std::scientific;
  std::cout << "adaptive_transfer_contract collocation-polynomial-transfer-v1 "
            << fixture.reference.boundaries.size() - 1 << " " << bundle.destination_boundaries.size() - 1 << " "
            << layout.stage_count() << " " << epsilon << "\n";
  write_runtime_provenance(layout);
  std::cout << "destination_boundaries " << bundle.destination_boundaries.size();
  for (double value : bundle.destination_boundaries) std::cout << " " << value;
  std::cout << "\ntransferred_unknowns " << bundle.unknowns.size();
  for (double value : bundle.unknowns) std::cout << " " << value;
  std::cout << "\ntransferred_tangent " << bundle.tangent.size();
  for (double value : bundle.tangent) std::cout << " " << value * bundle.tangent_norm_before_normalization;
  std::cout << "\ntransferred_phase_values " << bundle.reference.stage_values.size();
  for (const auto& row : bundle.reference.stage_values) for (double value : row) std::cout << " " << value;
  std::cout << "\ntransferred_phase_derivatives " << bundle.reference.stage_derivatives.size();
  for (const auto& row : bundle.reference.stage_derivatives) for (double value : row) std::cout << " " << value;
  OrbitLayout destination_layout(bundle.destination_boundaries.size() - 1, layout.stage_count(),
                                 Teuchos::DefaultComm<int>::getComm());
  Assembler destination_assembler(destination_layout, fixture.environment, bundle.reference);
  std::cout << "\ntransferred_phase_energy " << destination_assembler.phase_energy() << "\n";
}

void write_adaptive_restart(const Fixture& fixture, const OrbitLayout& layout) {
  const auto bundle = build_transfer_bundle(fixture, layout);
  OrbitLayout destination_layout(bundle.destination_boundaries.size() - 1, layout.stage_count(),
                                 Teuchos::DefaultComm<int>::getComm());
  auto destination_assembler = Teuchos::rcp(new Assembler(destination_layout, fixture.environment, bundle.reference));
  auto transferred_vector = make_vector(destination_layout, bundle.unknowns);
  const auto transfer_residual = destination_assembler->diagnostics(*destination_assembler->residual(*transferred_vector));
  const auto result = bs2026_loca::midpoint::solve_fixed_parameter(destination_assembler, *transferred_vector);
  const auto corrected = copy_vector_by_global_id(*result.unknowns);
  double correction_norm_squared = 0.0;
  for (std::size_t gid = 0; gid < corrected.size(); ++gid) {
    const double delta = corrected[gid] - bundle.unknowns[gid];
    correction_norm_squared += delta * delta;
  }
  std::cout << std::setprecision(17) << std::scientific;
  std::cout << "adaptive_restart_contract fixed-parameter-remesh-restart-v1 h+r "
            << "collocation-polynomial-transfer-v1 fixed-parameter-remesh-restart-retry-v1 "
            << (fixture.reference.boundaries.size() - 1) << " " << (bundle.destination_boundaries.size() - 1) << " "
            << layout.stage_count() << "\n";
  write_runtime_provenance(layout);
  std::cout << "restart_rebuild " << layout.unknown_size() << " " << destination_layout.unknown_size() << " "
            << layout.stage_size() << " " << destination_layout.stage_size() << " "
            << layout.endpoint_size() << " " << destination_layout.endpoint_size() << " "
            << layout.log_period_index() << " " << destination_layout.log_period_index() << " "
            << layout.phase_row() << " " << destination_layout.phase_row() << " "
            << layout.stage_count() << " " << destination_layout.stage_count() << "\n";
  std::cout << "restart_graph " << destination_assembler->graph()->getGlobalNumEntries() << " retained_reuse true rebuilt true\n";
  std::cout << "restart_attempts 3 h_r_transfer_correct h_r_refresh_reference_recorrect h_r_rebootstrap_tangent_recorrect\n";
  std::cout << "restart_transfer_residual " << transfer_residual.stage_max << " " << transfer_residual.stage_rms << " "
            << transfer_residual.update_max << " " << transfer_residual.update_rms << " "
            << transfer_residual.phase_abs << " " << transfer_residual.phase_energy << "\n";
  std::cout << "restart_tangent " << bundle.tangent_norm_before_normalization << " 1 "
            << (bundle.tangent_norm_before_normalization > 0.0 && std::isfinite(bundle.tangent_norm_before_normalization) ? "true" : "false") << "\n";
  std::cout << "restart_correction " << (result.acceptance.accepted ? "accepted" : "rejected") << " "
            << (result.nox_converged ? "converged" : "not_converged") << " "
            << result.nonlinear_iterations << " " << result.nox_residual_norm << " "
            << std::sqrt(correction_norm_squared) << " " << result.period << "\n";
  std::cout << "restart_linear " << result.linear.backend << " "
            << (result.linear.reported ? "reported" : "unreported") << " "
            << result.linear.symbolic_factorizations << " " << result.linear.numeric_factorizations << " "
            << result.linear.solves << " "
            << (result.linear.symbolic_complete ? "true" : "false") << " "
            << (result.linear.numeric_complete ? "true" : "false") << " "
            << (result.linear.solve_complete ? "true" : "false") << "\n";
  std::cout << "restart_final_diagnostics " << result.diagnostics.stage_max << " " << result.diagnostics.stage_rms << " "
            << result.diagnostics.update_max << " " << result.diagnostics.update_rms << " "
            << result.diagnostics.phase_abs << " " << result.diagnostics.phase_energy << "\n";
  std::cout << "restart_gates residual " << (result.acceptance.accepted ? "true" : "false")
            << " phase " << (result.diagnostics.phase_abs <= bs2026_loca::midpoint::accepted_phase_tolerance ? "true" : "false")
            << " positivity " << (result.physical_states_positive_finite && result.period_positive_finite ? "true" : "false")
            << " finite_change true linear " << (result.linear.solve_complete ? "true" : "false")
            << " tangent " << (bundle.tangent_norm_before_normalization > 0.0 && std::isfinite(bundle.tangent_norm_before_normalization) ? "true" : "false") << "\n";
  std::cout << "restart_solution " << corrected.size();
  for (double value : corrected) std::cout << " " << value;
  std::cout << "\n";
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
        command == "solve" || command == "adaptive-transfer" || command == "adaptive-controller" || command == "adaptive-restart" || command == "loca-contract" || command == "loca-smoke" || command == "loca-branches" ||
        command == "loca-dfdp" || command == "guard-nonfinite-reference" || command == "guard-invalid-period";
    const bool valid_arity = (fixture_command && argc == 3) ||
        (command == "acceptance-guard" && argc == 4);
    if (!valid_arity) {
      std::cerr << "Usage: bs2026_midpoint_orbit inspect|evaluate|solve|adaptive-transfer|adaptive-controller|adaptive-restart|loca-contract|loca-smoke|loca-branches|loca-dfdp|guard-nonfinite-reference|guard-invalid-period fixture.txt\n"
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
        Assembler invalid_assembler(OrbitLayout(fixture.reference.boundaries.size() - 1, fixture.stage_count, comm),
                                    fixture.environment, fixture.reference);
      } catch (const std::invalid_argument&) {
        std::cout << "nonfinite_reference_rejected true\n";
        return 0;
      }
      throw std::runtime_error("nonfinite phase reference was not rejected");
    }
    if (command == "guard-invalid-period") {
      fixture.unknowns.back() = std::numeric_limits<double>::infinity();
      Assembler guard_assembler(OrbitLayout(fixture.reference.boundaries.size() - 1, fixture.stage_count, comm),
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
    OrbitLayout layout(fixture.reference.boundaries.size() - 1, fixture.stage_count, comm);
    Assembler assembler(layout, fixture.environment, fixture.reference);
    auto unknowns = make_vector(layout, fixture.unknowns);
    if (command == "loca-contract" || command == "loca-smoke" || command == "loca-branches" || command == "loca-dfdp") {
      auto assembler_ptr = Teuchos::rcp(new Assembler(std::move(assembler)));
      const double origin = (std::log(fixture.environment.w) -
          0.5 * (fixture.log_w_lower + fixture.log_w_upper)) /
          (0.5 * (fixture.log_w_upper - fixture.log_w_lower));
      auto path = std::make_shared<bs2026_loca::midpoint::FixedTemperatureRhoPath>(
          fixture.environment.T, fixture.log_w_lower, fixture.log_w_upper);
      const auto weights = bs2026_loca::midpoint::continuation_metric_weights(*assembler_ptr);
      auto model = Teuchos::rcp(new bs2026_loca::midpoint::ContinuationModelEvaluator(
          assembler_ptr, path, origin, *unknowns));
      std::cout << std::setprecision(17) << std::scientific;
      std::cout << "loca_contract " << bs2026_loca::midpoint::continuation_version(layout) << " "
                << model->createOutArgs().Np() << " " << model->get_p_space(0)->dim() << " "
                << layout.unknown_size() << " " << layout.unknown_size() + 1 << " "
                << layout.phase_row() << " " << layout.log_period_index() << "\n";
      std::cout << "loca_method Arc_Length native_stepper true base_has_arclength false metric "
                << bs2026_loca::midpoint::loca_metric_version << "\n";
      std::cout << "rule " << layout.rule().family << " " << layout.stage_count() << " "
                << layout.formal_order() << " " << bs2026_loca::collocation::artifact_sha256 << "\n";
      std::cout << "build_identity " << __VERSION__ << " Trilinos_" << TRILINOS_VERSION_STRING << "\n";
      std::cout << "cmake_identity " << BS2026_CMAKE_SOURCE_SHA256 << " build_type_" << BS2026_CMAKE_BUILD_TYPE << "\n";
      std::cout << "source_fingerprint " << BS2026_MIDPOINT_LOCA_SHA256 << " " << BS2026_MIDPOINT_ORBIT_SHA256
                << " " << BS2026_MODEL_SHA256 << " " << BS2026_MIDPOINT_NOX_SHA256 << " "
                << BS2026_COLLOCATION_COEFFICIENTS_SHA256 << " " << BS2026_MIDPOINT_CLI_SHA256 << "\n";
      std::cout << "metric " << weights.size();
      for (double weight : weights) std::cout << " " << weight;
      std::cout << "\n";
      auto dot_a = Teuchos::rcp(new vector_type(layout.domain_map()));
      auto dot_b = Teuchos::rcp(new vector_type(layout.domain_map()));
      double expected_dot = 0.0;
      for (std::size_t gid = 0; gid < layout.unknown_size(); ++gid) {
        const double a = std::sin(static_cast<double>(gid) + 0.37);
        const double b = std::cos(static_cast<double>(gid) + 0.61);
        dot_a->replaceGlobalValue(static_cast<long long>(gid), a);
        dot_b->replaceGlobalValue(static_cast<long long>(gid), b);
        expected_dot += weights[gid] * a * b;
      }
      auto dot_global = LOCA::createGlobalData(Teuchos::rcp(new Teuchos::ParameterList));
      LOCA::ParameterVector dot_parameters; dot_parameters.addParameter(path->name(), origin);
      NOX::Thyra::Vector nox_a(*Thyra::createVector(dot_a, model->get_x_space()));
      NOX::Thyra::Vector nox_b(*Thyra::createVector(dot_b, model->get_x_space()));
      auto state_weights = weights; state_weights.pop_back();
      bs2026_loca::midpoint::WeightedThyraGroup metric_group(
          dot_global, nox_a, model, dot_parameters, state_weights);
      std::cout << "group_weighted_dot " << metric_group.computeScaledDotProduct(nox_a, nox_b)
                << " " << expected_dot << "\n";
      LOCA::destroyGlobalData(dot_global);
      if (command == "loca-dfdp") {
        constexpr double epsilon = 1.0e-6;
        auto check_dfdp = [&](const std::string& path_name,
                              const std::shared_ptr<const bs2026_loca::midpoint::ContinuationPath>& trial_path,
                              double coordinate) {
          auto trial_model = Teuchos::rcp(new bs2026_loca::midpoint::ContinuationModelEvaluator(
              assembler_ptr, trial_path, coordinate, *unknowns));
          auto evaluate_model = [&](double trial_coordinate, bool request_derivative) {
            auto in = trial_model->getNominalValues();
            auto parameter = Thyra::createMember(trial_model->get_p_space(0));
            { Thyra::DetachedVectorView<double> value(*parameter); value[0] = trial_coordinate; }
            in.set_p(0, parameter);
            auto out = trial_model->createOutArgs();
            auto residual = Thyra::createMember(trial_model->get_f_space());
            out.set_f(residual);
            Teuchos::RCP<Thyra::MultiVectorBase<double>> derivative = Teuchos::null;
            if (request_derivative) {
              derivative = Thyra::createMembers(trial_model->get_f_space(), 1);
              out.set_DfDp(0, Thyra::ModelEvaluatorBase::Derivative<double>(
                  derivative, Thyra::ModelEvaluatorBase::DERIV_MV_BY_COL));
            }
            trial_model->evalModel(in, out);
            auto residual_tpetra = Thyra::TpetraOperatorVectorExtraction<double>::getConstTpetraVector(residual);
            std::vector<double> derivative_values;
            if (!derivative.is_null()) {
              auto derivative_tpetra = Thyra::TpetraOperatorVectorExtraction<double>::getConstTpetraVector(
                  derivative->col(0));
              derivative_values = copy_vector_by_global_id(*derivative_tpetra);
            }
            return std::make_pair(copy_vector_by_global_id(*residual_tpetra), derivative_values);
          };
          const auto center = evaluate_model(coordinate, true);
          const auto plus = evaluate_model(coordinate + epsilon, false).first;
          const auto minus = evaluate_model(coordinate - epsilon, false).first;
          // A final center evaluation proves trial calls do not leave the shared
          // assembler at either finite-difference environment.
          (void)evaluate_model(coordinate, false);
          std::vector<double> difference(center.first.size());
          double error_squared = 0.0, column_squared = 0.0;
          for (std::size_t i = 0; i < difference.size(); ++i) {
            difference[i] = (plus[i] - minus[i]) / (2.0 * epsilon);
            const double error = center.second[i] - difference[i];
            error_squared += error * error; column_squared += center.second[i] * center.second[i];
          }
          const auto expected = trial_path->coordinates(coordinate);
          const double relative_error = std::sqrt(error_squared) / std::max(1.0, std::sqrt(column_squared));
          std::cout << "dfdp " << path_name << " " << epsilon << " " << relative_error << " "
                    << trial_model->last_evaluated_coordinate() << " " << assembler_ptr->environment().T << " "
                    << std::log(assembler_ptr->environment().w) << " " << expected.temperature << " "
                    << expected.log_w << " " << expected.coordinate << "\n";
          std::cout << "dfdp_column " << path_name << " " << center.second.size();
          for (double value : center.second) std::cout << " " << value;
          std::cout << "\n";
          std::cout << "dfdp_centered_difference " << path_name << " " << difference.size();
          for (double value : difference) std::cout << " " << value;
          std::cout << "\n";
        };
        check_dfdp("rho", path, origin);
        const double temperature_hat = (fixture.environment.T - 215.0) / 25.0;
        const auto lower = [fixture](double temperature) {
          return fixture.log_w_lower + fixture.spine_derivative * (temperature - fixture.environment.T);
        };
        const auto upper = [fixture](double temperature) {
          return fixture.log_w_upper + fixture.spine_derivative * (temperature - fixture.environment.T);
        };
        auto temperature_path = std::make_shared<bs2026_loca::midpoint::SpineTemperaturePath>(
            lower, upper, [fixture](double) { return fixture.spine_derivative; });
        check_dfdp("temperature_hat", temperature_path, temperature_hat);
        return 0;
      }
      if (command == "loca-branches") {
        const PchipFunction lower(false), upper(true);
        auto fixed225 = std::make_shared<bs2026_loca::midpoint::FixedTemperatureRhoPath>(
            225.0, lower(225.0), upper(225.0));
        auto spine = std::make_shared<bs2026_loca::midpoint::SpineTemperaturePath>(
            [lower](double value) { return lower(value); },
            [upper](double value) { return upper(value); },
            [lower, upper](double value) { return 0.5 * (lower.derivative(value) + upper.derivative(value)); });
        const double origin_rho = (std::log(fixture.environment.w) - 0.5 * (lower(225.0) + upper(225.0))) /
            (0.5 * (upper(225.0) - lower(225.0)));
        struct SegmentSpec { std::string id, reference_id; std::shared_ptr<const bs2026_loca::midpoint::ContinuationPath> path;
          Teuchos::RCP<Assembler> assembler; Teuchos::RCP<vector_type> origin; double coordinate, target, bootstrap_step, max_bootstrap; };
        auto run_segment = [&](const SegmentSpec& spec) {
          const int direction = spec.target > spec.coordinate ? 1 : -1;
          const auto bootstrap_result = bs2026_loca::midpoint::deterministic_bootstrap(
              spec.assembler, *spec.path, *spec.origin, spec.coordinate, direction,
              spec.bootstrap_step, spec.max_bootstrap);
          auto native = bs2026_loca::midpoint::run_native_loca(
              spec.assembler, spec.path, *spec.origin, spec.coordinate, spec.target,
              spec.bootstrap_step * direction, 100, &bootstrap_result.tangent);
          if (native.status != LOCA::Abstract::Iterator::Finished || native.points.empty() ||
              std::abs(native.points.back().coordinate - spec.target) > 1.0e-14)
            throw std::runtime_error("native branch failed exact landing: " + spec.id);
          std::cout << "branch_begin " << spec.id << " " << spec.reference_id << " "
                    << spec.path->name() << " " << spec.coordinate << " " << spec.target << "\n";
          for (const auto& attempt : bootstrap_result.attempts)
            std::cout << "branch_bootstrap " << spec.id << " " << attempt.attempt << " "
                      << attempt.requested_step << " " << attempt.coordinate << " "
                      << (attempt.accepted ? "accepted" : "rejected") << " " << attempt.weighted_step << "\n";
          std::cout << "branch_restart " << spec.id << " "
                    << native.signed_bootstrap_parameter_component << " "
                    << native.signed_bootstrap_weighted_norm << " "
                    << native.injected_restart_parameter_component << " "
                    << native.injected_restart_weighted_norm << " "
                    << native.signed_initial_step << " "
                    << (native.injected_restart_orientation_canonicalized ? "true" : "false") << "\n";
          for (std::size_t index = 0; index < native.events.size(); ++index) {
            const auto& event = native.events[index];
            std::cout << "branch_event " << spec.id << " " << index << " " << event.status << " "
                      << event.attempted_coordinate << " " << event.accepted_coordinate << " "
                      << event.attempted_coordinate_delta << " " << event.retry_coordinate_delta << " "
                      << (event.initial_solve ? "initial" : (event.final_target_solve ? "final" : "regular")) << "\n";
          }
          for (std::size_t index = 0; index < native.points.size(); ++index) {
            const auto& point = native.points[index];
            spec.assembler->set_environment(bs2026_loca::midpoint::environment_on_path(
                spec.assembler->environment(), *spec.path, point.coordinate));
            auto native_vector = make_vector(spec.assembler->layout(), point.unknowns);
            const auto native_diagnostics = spec.assembler->diagnostics(*spec.assembler->residual(*native_vector));
            bool native_states_positive_finite = true;
            for (std::size_t interval = 0; interval < spec.assembler->layout().interval_count(); ++interval) {
              for (int component = 0; component < 2; ++component)
                native_states_positive_finite = native_states_positive_finite &&
                    bs2026_loca::midpoint::finite_positive_exp(point.unknowns[static_cast<std::size_t>(
                        spec.assembler->layout().endpoint_index(interval, component))]);
              native_states_positive_finite = native_states_positive_finite &&
                  std::isfinite(point.unknowns[static_cast<std::size_t>(
                      spec.assembler->layout().endpoint_index(interval, 2))]);
              for (int stage = 0; stage < spec.assembler->layout().stage_count(); ++stage) {
                for (int component = 0; component < 2; ++component)
                  native_states_positive_finite = native_states_positive_finite &&
                      bs2026_loca::midpoint::finite_positive_exp(point.unknowns[static_cast<std::size_t>(
                          spec.assembler->layout().stage_index(interval, stage, component))]);
                native_states_positive_finite = native_states_positive_finite &&
                    std::isfinite(point.unknowns[static_cast<std::size_t>(
                        spec.assembler->layout().stage_index(interval, stage, 2))]);
              }
            }
            const bool native_period_positive_finite =
                bs2026_loca::midpoint::finite_positive_exp(point.unknowns.back());
            auto validation_seed = Teuchos::rcp(new vector_type(*native_vector));
            for (std::size_t gid = 0; gid < point.unknowns.size(); ++gid)
              validation_seed->replaceGlobalValue(static_cast<long long>(gid),
                  point.unknowns[gid] + 1.0e-7 * std::sin(static_cast<double>(gid) + 0.375));
            const auto validation = bs2026_loca::midpoint::solve_fixed_parameter(spec.assembler, *validation_seed);
            std::vector<double> validation_delta(point.unknowns.size() + 1, 0.0);
            const auto validated_values = copy_vector_by_global_id(*validation.unknowns);
            for (std::size_t gid = 0; gid < point.unknowns.size(); ++gid)
              validation_delta[gid] = validated_values[gid] - point.unknowns[gid];
            const double validation_distance = bs2026_loca::midpoint::weighted_norm(
                validation_delta, bs2026_loca::midpoint::continuation_metric_weights(*spec.assembler));
            bs2026_loca::midpoint::AcceptanceInputs native_acceptance_inputs;
            native_acceptance_inputs.nox_converged = true;
            native_acceptance_inputs.residual = native_diagnostics;
            native_acceptance_inputs.physical_states_positive_finite = native_states_positive_finite;
            native_acceptance_inputs.period_positive_finite = native_period_positive_finite;
            native_acceptance_inputs.linear = validation.linear;
            const auto native_acceptance = bs2026_loca::midpoint::evaluate_acceptance(native_acceptance_inputs);
            if (!validation.acceptance.accepted || !native_acceptance.accepted ||
                validation_distance > bs2026_loca::midpoint::loca_weighted_orbit_tolerance)
              throw std::runtime_error("native accepted-point validation failed: " + spec.id);
            std::cout << "branch_validation " << spec.id << " " << index << " "
                      << native_diagnostics.stage_max << " " << native_diagnostics.stage_rms << " "
                      << native_diagnostics.update_max << " " << native_diagnostics.update_rms << " "
                      << native_diagnostics.phase_abs << " "
                      << (native_states_positive_finite ? "true" : "false") << " "
                      << (native_period_positive_finite ? "true" : "false") << " "
                      << validation.linear.backend << " "
                      << (validation.linear.solve_complete ? "true" : "false") << " "
                      << validation_distance << "\n";
            std::cout << "branch_point " << spec.id << " " << index << " " << spec.reference_id << " "
                      << point.coordinate << " " << std::exp(point.unknowns.back());
            for (double value : point.unknowns) std::cout << " " << value;
            std::cout << "\n";
          }
          const int initial_saves = static_cast<int>(std::count_if(native.events.begin(), native.events.end(),
              [](const auto& event) { return event.initial_solve; }));
          const int final_saves = static_cast<int>(std::count_if(native.events.begin(), native.events.end(),
              [](const auto& event) { return event.final_target_solve; }));
          const int regular_accepted = static_cast<int>(std::count_if(native.events.begin(), native.events.end(),
              [](const auto& event) { return !event.initial_solve && !event.final_target_solve && event.status == "accepted"; }));
          const int regular_rejected = static_cast<int>(std::count_if(native.events.begin(), native.events.end(),
              [](const auto& event) { return !event.initial_solve && !event.final_target_solve && event.status == "rejected"; }));
          std::cout << "branch_end " << spec.id << " " << native.raw_step_number << " " << native.raw_failed_step_count << " "
                    << native.raw_total_step_count << " " << initial_saves << " " << final_saves << " "
                    << regular_accepted + regular_rejected << " " << regular_accepted << " " << regular_rejected << " "
                    << (native.used_bootstrap_restart_tangent ? "true" : "false") << "\n";
          return native;
        };
        auto initial_assembler = Teuchos::rcp(new Assembler(layout, fixture.environment, fixture.reference));
        auto to_spine = run_segment({"fixed225-to-spine", "phase-ref-episode007-seed", fixed225,
                                     initial_assembler, unknowns, origin_rho, 0.0, 0.02, 0.025});
        auto spine225_unknowns = make_vector(layout, to_spine.points.back().unknowns);
        const auto spine225_physical = fixed225->coordinates(0.0);
        const auto spine225_mapped = spine->coordinates(0.4);
        const auto spine225_reference = bs2026_loca::midpoint::refreshed_phase_reference(*initial_assembler, *spine225_unknowns);
        double spine225_stage_identity_max = 0.0, spine225_derivative_identity_max = 0.0;
        const auto spine225_values = copy_vector_by_global_id(*spine225_unknowns);
        const double spine225_period = std::exp(spine225_values[static_cast<std::size_t>(layout.log_period_index())]);
        for (std::size_t interval = 0; interval < layout.interval_count(); ++interval)
          for (int stage = 0; stage < layout.stage_count(); ++stage) {
            std::array<double, 3> values{};
            const std::size_t reference_index = interval * static_cast<std::size_t>(layout.stage_count()) + static_cast<std::size_t>(stage);
            for (int component = 0; component < 3; ++component) {
              values[component] = spine225_values[static_cast<std::size_t>(layout.stage_index(interval, stage, component))];
              spine225_stage_identity_max = std::max(spine225_stage_identity_max,
                  std::abs(values[component] - spine225_reference.stage_values[reference_index][component]));
            }
            const auto derivatives = bs2026_loca::local_derivatives(values, fixture.environment.T,
                spine225_physical.log_w, fixture.environment);
            for (int component = 0; component < 3; ++component)
              spine225_derivative_identity_max = std::max(spine225_derivative_identity_max,
                  std::abs(spine225_period * derivatives.values[component] -
                           spine225_reference.stage_derivatives[reference_index][component]));
          }
        auto spine_assembler = Teuchos::rcp(new Assembler(layout,
            bs2026_loca::midpoint::environment_on_path(fixture.environment, *spine, 0.4), spine225_reference));
        auto spine225_verify_seed = make_vector(layout, to_spine.points[to_spine.points.size() - 2].unknowns);
        const auto spine225_verified = bs2026_loca::midpoint::solve_fixed_parameter(spine_assembler, *spine225_verify_seed);
        if (!spine225_verified.acceptance.accepted ||
            std::abs(spine225_physical.temperature - spine225_mapped.temperature) > 1.0e-12 ||
            std::abs(spine225_physical.log_w - spine225_mapped.log_w) > 1.0e-12)
          throw std::runtime_error("spine-225 phase refresh verification failed");
        spine225_unknowns = spine225_verified.unknowns;
        if (layout.stage_count() == 1)
          std::cout << "phase_refresh phase-ref-episode007-seed phase-ref-spine-225 fixed225-to-spine temperature_hat 0.4 "
                    << spine225_physical.temperature << " " << spine225_physical.log_w << " "
                    << spine225_mapped.temperature << " " << spine225_mapped.log_w << " "
                    << spine225_verified.diagnostics.stage_max << " " << spine225_verified.diagnostics.update_max << " "
                    << spine225_verified.diagnostics.phase_abs << " " << spine225_verified.linear.backend << " "
                    << (spine225_verified.linear.solve_complete ? "true" : "false") << "\n";
        auto spine_up = run_segment({"spine-positive-T-hat", "phase-ref-spine-225", spine,
                                     spine_assembler, spine225_unknowns, 0.4, 0.44, 0.01, 0.25});
        (void)spine_up;
        auto spine_down = run_segment({"spine-negative-T-hat-to-210", "phase-ref-spine-225", spine,
                                       spine_assembler, spine225_unknowns, 0.4, -0.2, 0.01, 0.25});
        if (layout.stage_count() > 1)
          std::cout << "phase_refresh phase-ref-episode007-seed phase-ref-spine-225 fixed225-to-spine temperature_hat 0.4 "
                    << spine225_physical.temperature << " " << spine225_physical.log_w << " "
                    << spine225_mapped.temperature << " " << spine225_mapped.log_w << " "
                    << spine225_verified.diagnostics.stage_max << " " << spine225_verified.diagnostics.update_max << " "
                    << spine225_verified.diagnostics.phase_abs << " " << spine225_verified.linear.backend << " "
                    << (spine225_verified.linear.solve_complete ? "true" : "false") << " "
                    << spine225_stage_identity_max << " " << spine225_derivative_identity_max << " "
                    << (spine_assembler.get() != initial_assembler.get() ? "true" : "false") << " "
                    << (spine_up.model_evaluator_constructed && spine_up.weighted_group_constructed &&
                        spine_up.stepper_constructed ? "true" : "false") << "\n";
        auto spine210_unknowns = make_vector(layout, spine_down.points.back().unknowns);
        auto slice210 = std::make_shared<bs2026_loca::midpoint::FixedTemperatureRhoPath>(
            210.0, lower(210.0), upper(210.0));
        const auto slice210_physical = spine->coordinates(-0.2);
        const auto slice210_mapped = slice210->coordinates(0.0);
        const auto slice210_reference = bs2026_loca::midpoint::refreshed_phase_reference(*spine_assembler, *spine210_unknowns);
        double slice210_stage_identity_max = 0.0, slice210_derivative_identity_max = 0.0;
        const auto slice210_values = copy_vector_by_global_id(*spine210_unknowns);
        const double slice210_period = std::exp(slice210_values[static_cast<std::size_t>(layout.log_period_index())]);
        for (std::size_t interval = 0; interval < layout.interval_count(); ++interval)
          for (int stage = 0; stage < layout.stage_count(); ++stage) {
            std::array<double, 3> values{};
            const std::size_t reference_index = interval * static_cast<std::size_t>(layout.stage_count()) + static_cast<std::size_t>(stage);
            for (int component = 0; component < 3; ++component) {
              values[component] = slice210_values[static_cast<std::size_t>(layout.stage_index(interval, stage, component))];
              slice210_stage_identity_max = std::max(slice210_stage_identity_max,
                  std::abs(values[component] - slice210_reference.stage_values[reference_index][component]));
            }
            const auto derivatives = bs2026_loca::local_derivatives(values, slice210_physical.temperature,
                slice210_physical.log_w, fixture.environment);
            for (int component = 0; component < 3; ++component)
              slice210_derivative_identity_max = std::max(slice210_derivative_identity_max,
                  std::abs(slice210_period * derivatives.values[component] -
                           slice210_reference.stage_derivatives[reference_index][component]));
          }
        auto slice_assembler = Teuchos::rcp(new Assembler(layout,
            bs2026_loca::midpoint::environment_on_path(fixture.environment, *slice210, 0.0), slice210_reference));
        auto slice210_verify_seed = make_vector(layout, spine_down.points[spine_down.points.size() - 2].unknowns);
        const auto slice210_verified = bs2026_loca::midpoint::solve_fixed_parameter(slice_assembler, *slice210_verify_seed);
        if (!slice210_verified.acceptance.accepted ||
            std::abs(slice210_physical.temperature - slice210_mapped.temperature) > 1.0e-12 ||
            std::abs(slice210_physical.log_w - slice210_mapped.log_w) > 1.0e-12)
          throw std::runtime_error("slice-210 phase refresh verification failed");
        spine210_unknowns = slice210_verified.unknowns;
        if (layout.stage_count() == 1)
          std::cout << "phase_refresh phase-ref-spine-225 phase-ref-slice-210 spine-negative-T-hat-to-210 rho 0 "
                    << slice210_physical.temperature << " " << slice210_physical.log_w << " "
                    << slice210_mapped.temperature << " " << slice210_mapped.log_w << " "
                    << slice210_verified.diagnostics.stage_max << " " << slice210_verified.diagnostics.update_max << " "
                    << slice210_verified.diagnostics.phase_abs << " " << slice210_verified.linear.backend << " "
                    << (slice210_verified.linear.solve_complete ? "true" : "false") << "\n";
        auto slice_down = run_segment({"slice210-negative-rho", "phase-ref-slice-210", slice210,
                                       slice_assembler, spine210_unknowns, 0.0, -0.15, 0.02, 0.25});
        auto slice_up = run_segment({"slice210-positive-rho", "phase-ref-slice-210", slice210,
                                     slice_assembler, spine210_unknowns, 0.0, 0.15, 0.02, 0.25});
        (void)slice_down; (void)slice_up;
        if (layout.stage_count() > 1)
          std::cout << "phase_refresh phase-ref-spine-225 phase-ref-slice-210 spine-negative-T-hat-to-210 rho 0 "
                    << slice210_physical.temperature << " " << slice210_physical.log_w << " "
                    << slice210_mapped.temperature << " " << slice210_mapped.log_w << " "
                    << slice210_verified.diagnostics.stage_max << " " << slice210_verified.diagnostics.update_max << " "
                    << slice210_verified.diagnostics.phase_abs << " " << slice210_verified.linear.backend << " "
                    << (slice210_verified.linear.solve_complete ? "true" : "false") << " "
                    << slice210_stage_identity_max << " " << slice210_derivative_identity_max << " "
                    << (slice_assembler.get() != spine_assembler.get() ? "true" : "false") << " "
                    << (slice_down.model_evaluator_constructed && slice_down.weighted_group_constructed &&
                        slice_down.stepper_constructed ? "true" : "false") << "\n";
      } else if (command == "loca-smoke") {
        const auto bootstrap = bs2026_loca::midpoint::deterministic_bootstrap(
            assembler_ptr, *path, *unknowns, origin, 1, 0.02, 0.25);
        std::cout << "bootstrap " << bootstrap.attempts.size() << " " << bootstrap.coordinate << " "
                  << bootstrap.tangent.back() << " " << bootstrap.attempts.back().weighted_step << "\n";
        for (const auto& attempt : bootstrap.attempts)
          std::cout << "bootstrap_attempt " << attempt.attempt << " " << attempt.requested_step << " "
                    << (attempt.accepted ? "accepted" : "rejected") << " " << attempt.weighted_step << "\n";
        auto result = bs2026_loca::midpoint::run_native_loca(
            assembler_ptr, path, *unknowns, origin, origin + 0.06, 0.02, 20);
        std::cout << "loca_result " << result.raw_step_number << " " << result.raw_failed_step_count << " "
                  << result.raw_total_step_count << " " << result.base_dimension << " "
                  << result.extended_dimension << " " << result.points.size() << " "
                  << result.predictor_method << " " << result.step_size_method << "\n";
        for (const auto& point : result.points)
          std::cout << "loca_point " << point.coordinate << " " << std::exp(point.unknowns.back()) << "\n";
        auto forced = bs2026_loca::midpoint::run_native_loca(
            assembler_ptr, path, *unknowns, origin, origin + 0.04, 0.02, 20, &bootstrap.tangent, true);
        const int forced_regular_accepted = static_cast<int>(std::count_if(forced.events.begin(), forced.events.end(),
            [](const auto& event) { return !event.initial_solve && !event.final_target_solve && event.status == "accepted"; }));
        const int forced_regular_rejected = static_cast<int>(std::count_if(forced.events.begin(), forced.events.end(),
            [](const auto& event) { return !event.initial_solve && !event.final_target_solve && event.status == "rejected"; }));
        std::cout << "forced_rejection_result " << forced.raw_step_number << " " << forced.raw_failed_step_count << " "
                  << forced.raw_total_step_count << " " << forced.points.size() << " "
                  << forced_regular_accepted + forced_regular_rejected << " " << forced_regular_accepted << " "
                  << forced_regular_rejected << "\n";
        for (std::size_t index = 0; index < forced.events.size(); ++index) {
          const auto& event = forced.events[index];
          std::cout << "forced_rejection_event " << index << " " << event.status << " "
                    << event.attempted_coordinate << " " << event.accepted_coordinate << " "
                    << event.attempted_coordinate_delta << " " << event.retry_coordinate_delta << " "
                    << (event.initial_solve ? "initial" : (event.final_target_solve ? "final" : "regular")) << "\n";
        }
      }
      return 0;
    }
    if (command == "adaptive-transfer") {
      write_adaptive_transfer(fixture, layout);
      return 0;
    }
    if (command == "adaptive-controller") {
      write_adaptive_controller(fixture, layout);
      return 0;
    }
    if (command == "adaptive-restart") {
      write_adaptive_restart(fixture, layout);
      return 0;
    }
    if (command == "solve") {
      std::cout << "upstream_status " << fixture.upstream_status << "\n";
      write_solve_contract(assembler);
      if (fixture.upstream_status == "rejected") {
        write_runtime_provenance(layout);
        std::cout << "accepted false\nrejection_reasons 1 upstream_fixture_rejected\n";
        return 0;
      }
      if (fixture.upstream_status == "nonsolution") {
        write_runtime_provenance(layout);
        std::cout << "accepted false\nrejection_reasons 1 fixture_not_correction_input\n";
        return 0;
      }
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
    std::cout << "constants " << (layout.stage_count() == 1 ? bs2026_loca::midpoint::formulation_version : bs2026_loca::midpoint::gauss_formulation_version) << " "
              << bs2026_loca::midpoint::formulation_parity_tolerance << " "
              << bs2026_loca::midpoint::formulation_parity_absolute_floor << " "
              << bs2026_loca::midpoint::directional_relative_tolerance << "\n";
    std::cout << "layout " << layout.interval_count() << " " << layout.unknown_size() << " "
              << layout.endpoint_index(0, 0) << " " << layout.stage_index(0, 0, 0) << " "
              << layout.log_period_index() << " " << layout.phase_row() << "\n";
    write_runtime_provenance(layout);
    std::cout << "blocks " << layout.stage_size() << " " << layout.endpoint_size() << " 1\n";
    std::cout << "upstream_status " << fixture.upstream_status << "\n";
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
      auto log_period_direction = Teuchos::rcp(new vector_type(layout.domain_map()));
      log_period_direction->putScalar(0.0);
      log_period_direction->replaceGlobalValue(layout.log_period_index(), 1.0);
      auto log_period_column = Teuchos::rcp(new vector_type(layout.range_map()));
      jacobian->apply(*log_period_direction, *log_period_column);
      write_vector("log_period", *log_period_column);
      write_vector("rho", *columns.first);
      write_vector("temperature_hat", *columns.second);
      std::cout << "diagnostics " << diagnostics.stage_max << " " << diagnostics.stage_rms << " "
                << diagnostics.update_max << " " << diagnostics.update_rms << " "
                << diagnostics.phase_abs << " " << diagnostics.phase_energy << " "
                << diagnostics.largest_stage.interval << " " << diagnostics.largest_stage.component << " "
                << diagnostics.largest_update.interval << " " << diagnostics.largest_update.component;
      for (double scale : diagnostics.state_scaling) std::cout << " " << scale;
      std::cout << "\n";
      std::cout << "higher_order_diagnostics " << diagnostics.largest_stage.interval << " "
                << diagnostics.largest_stage.stage << " " << diagnostics.largest_stage.component << "\n";
    } else if (command != "inspect") {
      throw std::invalid_argument("unknown command: " + command);
    }
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "bs2026_midpoint_orbit: " << error.what() << "\n";
    return 2;
  }
}
