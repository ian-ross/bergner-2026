! AUTO-07p equilibrium problem template for Episode 3 Figure 1 continuation.
!
! Generated per-temperature problem files substitute the @...@ tokens below.
! The physics is not duplicated here: AUTO calls the shared repository-level
! bs2026_model equilibrium_residual routine, which mirrors the Python model core.
include 'bs2026_constants.f90'
include 'bs2026_model.f90'

subroutine FUNC(NDIM, U, ICP, PAR, IJAC, F, DFDU, DFDP)
  use bs2026_constants, only: dp
  use bs2026_model, only: environment_t, equilibrium_residual
  implicit none
  integer, intent(in) :: NDIM, IJAC, ICP(*)
  double precision, intent(in) :: U(NDIM), PAR(*)
  double precision, intent(out) :: F(NDIM)
  double precision, intent(inout) :: DFDU(*), DFDP(*)
  type(environment_t) :: env
  real(dp) :: log_state(3), residual(3)
  integer :: status

  env%p = PAR(2)
  env%T = PAR(3)
  env%F = PAR(4)
  env%N_a = PAR(5)
  env%dz = PAR(6)
  env%include_evaporation = .false.
  log_state = U(1:3)
  call equilibrium_residual(log_state, PAR(1), env, residual, status)
  if (status /= 0) then
     F(1:NDIM) = 1.0d30
  else
     F(1:NDIM) = residual(1:NDIM)
  end if
end subroutine FUNC

subroutine STPNT(NDIM, U, PAR, T)
  implicit none
  integer, intent(in) :: NDIM
  double precision, intent(out) :: U(NDIM), PAR(*)
  double precision, intent(in) :: T

  U(1) = @LOG_N@
  U(2) = @LOG_Q@
  U(3) = @S@
  PAR(1) = @LOG_W_MIN@
  PAR(2) = @PRESSURE_PA@
  PAR(3) = @TEMPERATURE_K@
  PAR(4) = @SEDIMENTATION_F@
  PAR(5) = @AEROSOL_N_A@
  PAR(6) = @DZ_M@
  PAR(7) = exp(PAR(1))
  PAR(8) = exp(U(1))
  PAR(9) = exp(U(2))
end subroutine STPNT

subroutine PVLS(NDIM, U, PAR)
  implicit none
  integer, intent(in) :: NDIM
  double precision, intent(in) :: U(NDIM)
  double precision, intent(inout) :: PAR(*)
  PAR(7) = exp(PAR(1))
  PAR(8) = exp(U(1))
  PAR(9) = exp(U(2))
end subroutine PVLS

subroutine BCND
end subroutine BCND

subroutine ICND
end subroutine ICND

subroutine FOPT
end subroutine FOPT
