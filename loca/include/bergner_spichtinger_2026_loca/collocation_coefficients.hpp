// Generated Gauss--Legendre collocation tables; do not edit by hand.
// Generator: episodes/008-figure5-periodic-orbit-continuation/scripts/generate_collocation_coefficients.py
// Runtime dependency: C++ standard library only.
#pragma once

#include <cstddef>

namespace bs2026_loca {
namespace collocation {

inline constexpr char artifact_schema_version[] = "1.0.0";
inline constexpr char artifact_sha256[] = "f47a6f789fa463abdfdb8d0b158a78bd228bbe85881199d601d086f49396ba6a";

template <std::size_t Stages>
struct GaussLegendreRule;

template <>
struct GaussLegendreRule<1> {
  inline static constexpr std::size_t stage_count = 1;
  inline static constexpr std::size_t formal_order = 2;
  inline static constexpr std::size_t defect_check_count = 2;
  inline static constexpr char family[] = "gauss-legendre";
  inline static constexpr double nodes[1] = {5.0000000000000000e-01};
  inline static constexpr double stage_coefficients[1][1] = {
      {5.0000000000000000e-01}
  };
  inline static constexpr double quadrature_weights[1] = {1.0000000000000000e+00};
  inline static constexpr double transfer_coefficients[1][2] = {
      {0.0000000000000000e+00, 1.0000000000000000e+00}
  };
  inline static constexpr double defect_check_nodes[2] = {2.1132486540518711e-01, 7.8867513459481287e-01};
  inline static constexpr double defect_lagrange_evaluation[2][1] = {
      {1.0000000000000000e+00},
      {1.0000000000000000e+00}
  };
  inline static constexpr double defect_transfer_evaluation[2][1] = {
      {2.1132486540518711e-01},
      {7.8867513459481287e-01}
  };
};

template <>
struct GaussLegendreRule<2> {
  inline static constexpr std::size_t stage_count = 2;
  inline static constexpr std::size_t formal_order = 4;
  inline static constexpr std::size_t defect_check_count = 3;
  inline static constexpr char family[] = "gauss-legendre";
  inline static constexpr double nodes[2] = {2.1132486540518711e-01, 7.8867513459481287e-01};
  inline static constexpr double stage_coefficients[2][2] = {
      {2.5000000000000000e-01, -3.8675134594812879e-02},
      {5.3867513459481287e-01, 2.5000000000000000e-01}
  };
  inline static constexpr double quadrature_weights[2] = {5.0000000000000000e-01, 5.0000000000000000e-01};
  inline static constexpr double transfer_coefficients[2][3] = {
      {0.0000000000000000e+00, 1.3660254037844386e+00, -8.6602540378443860e-01},
      {0.0000000000000000e+00, -3.6602540378443865e-01, 8.6602540378443860e-01}
  };
  inline static constexpr double defect_check_nodes[3] = {1.1270166537925831e-01, 5.0000000000000000e-01, 8.8729833462074170e-01};
  inline static constexpr double defect_lagrange_evaluation[3][2] = {
      {1.1708203932499368e+00, -1.7082039324993692e-01},
      {5.0000000000000000e-01, 5.0000000000000000e-01},
      {-1.7082039324993692e-01, 1.1708203932499368e+00}
  };
  inline static constexpr double defect_transfer_evaluation[3][2] = {
      {1.4295337306807301e-01, -3.0251707688814709e-02},
      {4.6650635094610965e-01, 3.3493649053890337e-02},
      {5.3025170768881469e-01, 3.5704662693192696e-01}
  };
};

template <>
struct GaussLegendreRule<3> {
  inline static constexpr std::size_t stage_count = 3;
  inline static constexpr std::size_t formal_order = 6;
  inline static constexpr std::size_t defect_check_count = 4;
  inline static constexpr char family[] = "gauss-legendre";
  inline static constexpr double nodes[3] = {1.1270166537925831e-01, 5.0000000000000000e-01, 8.8729833462074170e-01};
  inline static constexpr double stage_coefficients[3][3] = {
      {1.3888888888888890e-01, -3.5976667524938902e-02, 9.7894440153083254e-03},
      {3.0026319498086457e-01, 2.2222222222222221e-01, -2.2485417203086815e-02},
      {2.6798833376246944e-01, 4.8042111196938336e-01, 1.3888888888888890e-01}
  };
  inline static constexpr double quadrature_weights[3] = {2.7777777777777779e-01, 4.4444444444444442e-01, 2.7777777777777779e-01};
  inline static constexpr double transfer_coefficients[3][4] = {
      {0.0000000000000000e+00, 1.4788305577012362e+00, -2.3121638910345697e+00, 1.1111111111111112e+00},
      {0.0000000000000000e+00, -6.6666666666666663e-01, 3.3333333333333335e+00, -2.2222222222222223e+00},
      {0.0000000000000000e+00, 1.8783610896543051e-01, -1.0211694422987638e+00, 1.1111111111111112e+00}
  };
  inline static constexpr double defect_check_nodes[4] = {6.9431844202973714e-02, 3.3000947820757187e-01, 6.6999052179242813e-01, 9.3056815579702634e-01};
  inline static constexpr double defect_lagrange_evaluation[4][3] = {
      {1.1738242215578820e+00, -2.3592624524301534e-01, 6.2102023685133248e-02},
      {3.1577941163593432e-01, 8.0735481667158682e-01, -1.2313422830752110e-01},
      {-1.2313422830752110e-01, 8.0735481667158682e-01, 3.1577941163593432e-01},
      {6.2102023685133248e-02, -2.3592624524301534e-01, 1.1738242215578820e+00}
  };
  inline static constexpr double defect_transfer_evaluation[4][3] = {
      {9.1903403504121642e-02, -3.0962438869661282e-02, 8.4908795685133473e-03},
      {2.7615242943944829e-01, 6.3147652174725732e-02, -9.2906034066021596e-03},
      {2.8706838118437994e-01, 3.8129679226971869e-01, 1.6253483383294872e-03},
      {2.6928689820926444e-01, 4.7540688331410574e-01, 1.8587437427365613e-01}
  };
};

}  // namespace collocation
}  // namespace bs2026_loca
