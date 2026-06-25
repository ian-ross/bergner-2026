! Shared AUTO-07p model constants for Bergner & Spichtinger (2026).
!
! This module mirrors src/bergner_spichtinger_2026/constants.py.  Names use
! ASCII spellings for portability in AUTO/gfortran sources while comments keep
! the paper equation references used by the Python implementation.
module bs2026_constants
  implicit none

  integer, parameter :: dp = selected_real_kind(15, 307)

  ! Appendix A, Eq. (A23); dry air and water-vapor gas constants.
  real(dp), parameter :: R_d = 287.058_dp          ! J kg^-1 K^-1
  real(dp), parameter :: R_v = 461.553_dp          ! J kg^-1 K^-1
  real(dp), parameter :: grav = 9.81_dp            ! m s^-2, App. A text below Eq. (A23)
  real(dp), parameter :: c_p = 1004.0_dp           ! J kg^-1 K^-1, used in Eq. (15)/(30)/(38)

  ! Sec. III.B / Eq. (45), (53); molar-mass ratio and vapor molar mass.
  real(dp), parameter :: epsilon = 0.622_dp
  real(dp), parameter :: M_mol_v = 18.01528e-3_dp  ! kg mol^-1, Eq. (A29)

  ! Appendix A, Eq. (A24)--(A28): latent heat of sublimation coefficients.
  real(dp), parameter :: l0 = 46782.5_dp
  real(dp), parameter :: l1 = 35.8925_dp
  real(dp), parameter :: l2 = -0.07414_dp
  real(dp), parameter :: l3 = 541.5_dp
  real(dp), parameter :: T_l = 123.75_dp

  ! Appendix A, Eq. (A30)--(A33): saturation vapor pressure over hexagonal ice.
  real(dp), parameter :: b0 = 9.550426_dp
  real(dp), parameter :: b1 = -5723.265_dp
  real(dp), parameter :: b2 = 3.53068_dp
  real(dp), parameter :: b3 = -0.00728332_dp

  ! Appendix A, Eq. (47)--(49): vapor diffusivity.
  real(dp), parameter :: D_v0 = 2.1422e-5_dp
  real(dp), parameter :: T0 = 273.15_dp
  real(dp), parameter :: p0 = 101325.0_dp

  ! Appendix A, Eq. (A34)--(A36): heat conduction of air.
  ! Same transcription as Python core.K_T: a_K T^b_K / (T + T_K 10^(c_K/T)).
  real(dp), parameter :: a_K = 0.002646_dp
  real(dp), parameter :: b_K = 1.5_dp
  real(dp), parameter :: T_K = 245.0_dp
  real(dp), parameter :: c_K = -12.0_dp

  ! Sec. III.C / Eq. (31): bulk density and ice distribution moment ratio.
  real(dp), parameter :: rho_b = 810.0_dp
  real(dp), parameter :: r0 = 3.0_dp

  ! Appendix A, Eq. (A15)--(A17): solution-droplet nucleation parameters.
  real(dp), parameter :: r_sol = 75.0e-9_dp
  real(dp), parameter :: sigma_r = 1.5_dp
  real(dp), parameter :: N_a_typical = 3.0e8_dp
  real(dp), parameter :: N_a_figure1_high = 1.0e10_dp
  real(dp), parameter :: N_a_default = N_a_typical
  real(dp), parameter :: J0 = 1.0e16_dp
  real(dp), parameter :: m_nuc = 1.0e-16_dp

  ! Appendix A, Eq. (A18)--(A22): homogeneous freezing fit.
  real(dp), parameter :: p1_a0 = -50.4085_dp
  real(dp), parameter :: p1_a1 = 0.9368_dp
  real(dp), parameter :: p2_as2 = -1.36989e-5_dp
  real(dp), parameter :: p2_as1 = 0.00228_dp
  real(dp), parameter :: p2_as0 = 1.67469_dp

  ! Sec. III.E.4, Eq. (55)--(59), (66)--(70): sedimentation.
  real(dp), parameter :: p_c = 30000.0_dp
  real(dp), parameter :: T_c = 233.0_dp
  real(dp), parameter :: a_c = -0.178_dp
  real(dp), parameter :: b_c = -0.394_dp
  real(dp), parameter :: a_sed = 6.0e5_dp
  real(dp), parameter :: dz_default = 100.0_dp

  real(dp), parameter :: pi_dp = acos(-1.0_dp)
end module bs2026_constants
