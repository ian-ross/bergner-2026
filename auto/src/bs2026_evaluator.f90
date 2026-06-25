! Standalone evaluator for the shared Bergner & Spichtinger (2026) Fortran core.
!
! This driver deliberately does not run AUTO continuation.  It gives tests and
! future orchestration scripts a small callable path for coefficients, process
! terms, the vector field, and log-coordinate equilibrium residuals.
program bs2026_evaluator
  use bs2026_constants, only: dp, N_a_default, dz_default
  use bs2026_model, only: environment_t, coefficients_t, compute_coefficients, process_terms, &
       vector_field, equilibrium_residual
  implicit none

  character(len=32) :: mode
  integer :: nargs, status
  type(environment_t) :: env
  type(coefficients_t) :: c
  real(dp) :: n, q, s, log_w, vals(9), log_state(3), residual(3)

  nargs = command_argument_count()
  if (nargs < 1) call usage_and_stop()
  call get_command_argument(1, mode)

  select case (trim(mode))
  case ("coefficients")
     if (nargs < 5) call usage_and_stop()
     call read_environment(2, env)
     c = compute_coefficients(env)
     call print_coefficients(c)
  case ("terms")
     if (nargs < 8) call usage_and_stop()
     call read_environment_state_command(env, n, q, s)
     c = compute_coefficients(env)
     call process_terms(n, q, s, env, c, vals, status)
     if (status /= 0) call invalid_state_stop()
     call print_terms(vals)
  case ("rhs")
     if (nargs < 8) call usage_and_stop()
     call read_environment_state_command(env, n, q, s)
     c = compute_coefficients(env)
     call vector_field(n, q, s, env, c, vals(1:3), status)
     if (status /= 0) call invalid_state_stop()
     call print_vector("rhs", vals(1:3))
  case ("residual")
     if (nargs < 8) call usage_and_stop()
     ! residual p T log_w F log_n log_q s [N_a dz include_evaporation]
     call read_real_arg(2, env%p)
     call read_real_arg(3, env%T)
     call read_real_arg(4, log_w)
     call read_real_arg(5, env%F)
     env%w = exp(log_w)
     env%N_a = N_a_default
     env%dz = dz_default
     env%include_evaporation = .false.
     call read_real_arg(6, log_state(1))
     call read_real_arg(7, log_state(2))
     call read_real_arg(8, log_state(3))
     if (nargs >= 9) call read_real_arg(9, env%N_a)
     if (nargs >= 10) call read_real_arg(10, env%dz)
     if (nargs >= 11) call read_logical_arg(11, env%include_evaporation)
     call equilibrium_residual(log_state, log_w, env, residual, status)
     if (status /= 0) call invalid_state_stop()
     call print_vector("residual", residual)
  case default
     call usage_and_stop()
  end select

contains

  subroutine read_environment(first, env)
    integer, intent(in) :: first
    type(environment_t), intent(out) :: env
    integer :: nargs_local
    nargs_local = command_argument_count()
    call read_required_environment(first, env)
    if (nargs_local >= first + 4) call read_real_arg(first + 4, env%N_a)
    if (nargs_local >= first + 5) call read_real_arg(first + 5, env%dz)
    if (nargs_local >= first + 6) call read_logical_arg(first + 6, env%include_evaporation)
  end subroutine read_environment

  subroutine read_required_environment(first, env)
    integer, intent(in) :: first
    type(environment_t), intent(out) :: env
    call read_real_arg(first, env%p)
    call read_real_arg(first + 1, env%T)
    call read_real_arg(first + 2, env%w)
    call read_real_arg(first + 3, env%F)
    env%N_a = N_a_default
    env%dz = dz_default
    env%include_evaporation = .false.
  end subroutine read_required_environment

  subroutine read_environment_state_command(env, n, q, s)
    type(environment_t), intent(out) :: env
    real(dp), intent(out) :: n, q, s
    integer :: nargs_local
    nargs_local = command_argument_count()
    call read_required_environment(2, env)
    call read_real_arg(6, n)
    call read_real_arg(7, q)
    call read_real_arg(8, s)
    if (nargs_local >= 9) call read_real_arg(9, env%N_a)
    if (nargs_local >= 10) call read_real_arg(10, env%dz)
    if (nargs_local >= 11) call read_logical_arg(11, env%include_evaporation)
  end subroutine read_environment_state_command

  subroutine read_real_arg(index, value)
    integer, intent(in) :: index
    real(dp), intent(out) :: value
    character(len=128) :: arg
    integer :: ios
    call get_command_argument(index, arg)
    read(arg, *, iostat=ios) value
    if (ios /= 0) then
       write(*, '(a,i0,a)') 'error argument ', index, ' must be a real number'
       stop 2
    end if
  end subroutine read_real_arg

  subroutine read_logical_arg(index, value)
    integer, intent(in) :: index
    logical, intent(out) :: value
    character(len=128) :: arg
    integer :: parsed_int, ios
    call get_command_argument(index, arg)
    read(arg, *, iostat=ios) parsed_int
    if (ios == 0) then
       value = parsed_int /= 0
       return
    end if
    select case (trim(arg))
    case ("true", "TRUE", "True", ".true.", ".TRUE.")
       value = .true.
    case ("false", "FALSE", "False", ".false.", ".FALSE.")
       value = .false.
    case default
       write(*, '(a,i0,a)') 'error argument ', index, ' must be boolean-like'
       stop 2
    end select
  end subroutine read_logical_arg

  subroutine print_coefficients(c)
    type(coefficients_t), intent(in) :: c
    call print_scalar("rho", c%rho)
    call print_scalar("D", c%D_cool)
    call print_scalar("p_si", c%p_si)
    call print_scalar("p1e", c%p1e)
    call print_scalar("p2", c%p2)
    call print_scalar("A_n", c%A_n)
    call print_scalar("A_q", c%A_q)
    call print_scalar("A_s", c%A_s)
    call print_scalar("B_q", c%B_q)
    call print_scalar("B_s", c%B_s)
    call print_scalar("C_n", c%C_n)
    call print_scalar("C_q", c%C_q)
  end subroutine print_coefficients

  subroutine print_terms(terms)
    real(dp), intent(in) :: terms(9)
    call print_scalar("Nuc_n", terms(1))
    call print_scalar("Nuc_q", terms(2))
    call print_scalar("Nuc_s", terms(3))
    call print_scalar("Dep_q", terms(4))
    call print_scalar("Dep_s", terms(5))
    call print_scalar("Evap_n", terms(6))
    call print_scalar("Sed_n", terms(7))
    call print_scalar("Sed_q", terms(8))
    call print_scalar("Cool", terms(9))
  end subroutine print_terms

  subroutine print_vector(prefix, vector)
    character(len=*), intent(in) :: prefix
    real(dp), intent(in) :: vector(3)
    call print_scalar(trim(prefix)//"_1", vector(1))
    call print_scalar(trim(prefix)//"_2", vector(2))
    call print_scalar(trim(prefix)//"_3", vector(3))
  end subroutine print_vector

  subroutine print_scalar(name, value)
    character(len=*), intent(in) :: name
    real(dp), intent(in) :: value
    write(*, '(a,1x,es24.16e3)') trim(name), value
  end subroutine print_scalar

  subroutine invalid_state_stop()
    write(*, '(a)') 'error n and q must be strictly positive'
    stop 3
  end subroutine invalid_state_stop

  subroutine usage_and_stop()
    write(*, '(a)') 'usage:'
    write(*, '(a)') '  bs2026_evaluator coefficients p T w F [N_a dz include_evaporation]'
    write(*, '(a)') '  bs2026_evaluator terms p T w F n q s [N_a dz include_evaporation]'
    write(*, '(a)') '  bs2026_evaluator rhs p T w F n q s [N_a dz include_evaporation]'
    write(*, '(a)') '  bs2026_evaluator residual p T log_w F log_n log_q s [N_a dz include_evaporation]'
    stop 2
  end subroutine usage_and_stop

end program bs2026_evaluator
