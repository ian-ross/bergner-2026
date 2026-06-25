! Shared legible Fortran model core for Bergner & Spichtinger (2026).
!
! This file intentionally mirrors the small functions in
! src/bergner_spichtinger_2026/core.py and residuals.py rather than hiding the
! model inside AUTO callbacks.  It can be used by AUTO run files later, and by
! the standalone evaluator in this directory now.
module bs2026_model
  use bs2026_constants, only: dp, R_d, R_v, grav, c_p, epsilon, M_mol_v, &
       l0, l1, l2, l3, T_l, b0, b1, b2, b3, D_v0, T0, p0, a_K, b_K, T_K, c_K, &
       rho_b, r0, r_sol, sigma_r, N_a_default, J0, m_nuc, p1_a0, p1_a1, &
       p2_as2, p2_as1, p2_as0, p_c, T_c, a_c, b_c, a_sed, dz_default, pi_dp
  implicit none

  type :: environment_t
     real(dp) :: p = 30000.0_dp       ! pressure [Pa]
     real(dp) :: T = 225.0_dp         ! temperature [K]
     real(dp) :: w = 0.1_dp           ! vertical velocity [m s^-1]
     real(dp) :: F = 1.0_dp           ! sedimentation parameter [1]
     real(dp) :: N_a = N_a_default    ! aerosol number concentration [m^-3]
     real(dp) :: dz = dz_default      ! vertical box extent [m]
     logical :: include_evaporation = .false.
  end type environment_t

  type :: coefficients_t
     real(dp) :: rho
     real(dp) :: D_cool
     real(dp) :: p_si
     real(dp) :: p1e
     real(dp) :: p2
     real(dp) :: A_n
     real(dp) :: A_q
     real(dp) :: A_s
     real(dp) :: B_q
     real(dp) :: B_s
     real(dp) :: C_n
     real(dp) :: C_q
  end type coefficients_t

contains

  pure function rho_air(p, T) result(rho)
    ! Python core.rho_air; ideal gas law, p [Pa], T [K] -> kg m^-3.
    real(dp), intent(in) :: p, T
    real(dp) :: rho
    rho = p / (R_d * T)
  end function rho_air

  pure function latent_heat(T) result(L)
    ! Python core.L; App. A Eqs. (A24)--(A29), T [K] -> J kg^-1.
    real(dp), intent(in) :: T
    real(dp) :: L, L_mol
    L_mol = l0 + l1*T + l2*T**2 + l3*exp(-((T/T_l)**2))
    L = L_mol / M_mol_v
  end function latent_heat

  pure function saturation_pressure_ice(T) result(psi)
    ! Python core.p_si; Eq. (A30), T [K] -> Pa.
    real(dp), intent(in) :: T
    real(dp) :: psi
    psi = exp(b0 + b1/T + b2*log(T) + b3*T)
  end function saturation_pressure_ice

  pure function vapor_diffusivity(T, p) result(Dv)
    ! Python core.D_v; Eq. (47), T [K], p [Pa] -> m^2 s^-1.
    real(dp), intent(in) :: T, p
    real(dp) :: Dv
    Dv = D_v0 * (T/T0)**2 * (p0/p)
  end function vapor_diffusivity

  pure function heat_conduction_air(T) result(KT)
    ! Python core.K_T; App. A Eq. (A34) with confirmed transcription.
    real(dp), intent(in) :: T
    real(dp) :: KT
    KT = (a_K * T**b_K) / (T + T_K * 10.0_dp**(c_K/T))
  end function heat_conduction_air

  pure function growth_factor(T, p) result(Gv)
    ! Python core.G_v; Howell growth factor, Eq. (50).
    real(dp), intent(in) :: T, p
    real(dp) :: Gv, Ls
    Ls = latent_heat(T)
    Gv = 1.0_dp / ((((Ls/(R_v*T)) - 1.0_dp) * Ls * vapor_diffusivity(T, p) / &
         (T * heat_conduction_air(T))) + R_v*T/saturation_pressure_ice(T))
  end function growth_factor

  pure function cooling_coefficient(T) result(Dcool)
    ! Python core.D; Eq. (15)/(30)/(38), Cool = D w s.
    real(dp), intent(in) :: T
    real(dp) :: Dcool
    Dcool = ((latent_heat(T)/(c_p*R_v*T**2)) - (1.0_dp/(R_d*T))) * grav
  end function cooling_coefficient

  pure function p1_poly(T) result(val)
    ! Python core.p1; Eq. (A18), base-10 nucleation steepness polynomial.
    real(dp), intent(in) :: T
    real(dp) :: val
    val = p1_a0 + p1_a1*T
  end function p1_poly

  pure function p1_exp(T) result(val)
    ! Python core.p1e; Eq. (A18), natural-exponential steepness log(10)*p1(T).
    real(dp), intent(in) :: T
    real(dp) :: val
    val = log(10.0_dp) * p1_poly(T)
  end function p1_exp

  pure function p2_critical(T) result(val)
    ! Python core.p2; Eq. (A19), critical saturation fit.
    real(dp), intent(in) :: T
    real(dp) :: val
    val = p2_as2*T**2 + p2_as1*T + p2_as0
  end function p2_critical

  pure function solution_droplet_volume() result(Vsol)
    ! Python core.V_sol; Eq. (A15) -> m^3.
    real(dp) :: Vsol, c_sol
    c_sol = exp(4.5_dp * log(sigma_r)**2)
    Vsol = (4.0_dp/3.0_dp) * pi_dp * r_sol**3 * c_sol
  end function solution_droplet_volume

  pure function radius_mass_coefficient() result(cr)
    ! Python core.c_radius; Eq. (31), r = c m^(1/3).
    real(dp) :: cr
    cr = (3.0_dp/(4.0_dp*pi_dp*rho_b))**(1.0_dp/3.0_dp)
  end function radius_mass_coefficient

  pure function fall_speed_correction(p, T) result(cf)
    ! Python core.c_fall; Eq. (55).
    real(dp), intent(in) :: p, T
    real(dp) :: cf
    cf = (p/p_c)**a_c * (T/T_c)**b_c
  end function fall_speed_correction

  pure function heaviside(x) result(h)
    ! Python core.H; Eq. (12)/(54), 1 for x > 0 else 0.
    real(dp), intent(in) :: x
    real(dp) :: h
    if (x > 0.0_dp) then
       h = 1.0_dp
    else
       h = 0.0_dp
    end if
  end function heaviside

  pure function compute_coefficients(env) result(c)
    ! Python core.coefficients; temperature/pressure dependent coefficients.
    type(environment_t), intent(in) :: env
    type(coefficients_t) :: c
    real(dp) :: cf
    c%rho = rho_air(env%p, env%T)
    c%p_si = saturation_pressure_ice(env%T)
    c%D_cool = cooling_coefficient(env%T)
    c%p1e = p1_exp(env%T)
    c%p2 = p2_critical(env%T)
    c%A_n = (env%N_a / c%rho) * solution_droplet_volume() * J0
    c%A_q = m_nuc * c%A_n
    c%A_s = c%A_q * env%p / (epsilon * c%p_si)
    c%B_q = 4.0_dp*pi_dp*growth_factor(env%T, env%p)*vapor_diffusivity(env%T, env%p) * &
         radius_mass_coefficient() * r0**(-1.0_dp/9.0_dp)
    c%B_s = c%B_q * env%p / (epsilon * c%p_si)
    cf = fall_speed_correction(env%p, env%T)
    c%C_n = cf * a_sed * r0**(-1.0_dp/9.0_dp) / env%dz
    c%C_q = cf * a_sed * r0**(5.0_dp/9.0_dp) / env%dz
  end function compute_coefficients

  subroutine process_terms(n, q, s, env, c, terms, status)
    ! Python core.process_terms; Sec. II.D process rates in paper order.
    ! terms = [Nuc_n,Nuc_q,Nuc_s,Dep_q,Dep_s,Evap_n,Sed_n,Sed_q,Cool]
    real(dp), intent(in) :: n, q, s
    type(environment_t), intent(in) :: env
    type(coefficients_t), intent(in) :: c
    real(dp), intent(out) :: terms(9)
    integer, intent(out) :: status
    real(dp) :: expo

    if (n <= 0.0_dp .or. q <= 0.0_dp) then
       status = 1
       terms = 0.0_dp
       return
    end if

    expo = exp(c%p1e * (s - c%p2))
    terms(1) = c%A_n * expo
    terms(2) = c%A_q * expo
    terms(3) = -c%A_s * expo
    terms(4) = c%B_q * n**(2.0_dp/3.0_dp) * q**(1.0_dp/3.0_dp) * (s - 1.0_dp)
    terms(5) = -c%B_s * n**(2.0_dp/3.0_dp) * q**(1.0_dp/3.0_dp) * (s - 1.0_dp)
    if (env%include_evaporation) then
       terms(6) = (n/q) * terms(4) * heaviside(1.0_dp - s)
    else
       terms(6) = 0.0_dp
    end if
    terms(7) = -env%F * c%C_n * n**(1.0_dp/3.0_dp) * q**(2.0_dp/3.0_dp)
    terms(8) = -env%F * c%C_q * n**(-2.0_dp/3.0_dp) * q**(5.0_dp/3.0_dp)
    terms(9) = c%D_cool * env%w * s
    status = 0
  end subroutine process_terms

  subroutine vector_field(n, q, s, env, c, rhs, status)
    ! Python core.vector_field; Eqs. (4)--(6).
    real(dp), intent(in) :: n, q, s
    type(environment_t), intent(in) :: env
    type(coefficients_t), intent(in) :: c
    real(dp), intent(out) :: rhs(3)
    integer, intent(out) :: status
    real(dp) :: terms(9)

    call process_terms(n, q, s, env, c, terms, status)
    if (status /= 0) then
       rhs = 0.0_dp
       return
    end if
    rhs(1) = terms(1) + terms(6) + terms(7)
    rhs(2) = terms(2) + terms(4) + terms(8)
    rhs(3) = terms(9) + terms(3) + terms(5)
  end subroutine vector_field

  subroutine equilibrium_residual(log_state, log_w, env_template, residual, status)
    ! Python residuals.equilibrium_residual with row scaling omitted:
    ! [dn/dt / n, dq/dt / q, ds/dt] at physical state (exp(log n), exp(log q), s)
    ! and env%w replaced by exp(log_w).  Coefficients are independent of w.
    real(dp), intent(in) :: log_state(3), log_w
    type(environment_t), intent(in) :: env_template
    real(dp), intent(out) :: residual(3)
    integer, intent(out) :: status
    type(environment_t) :: env
    type(coefficients_t) :: c
    real(dp) :: n, q, s, rhs(3)

    n = exp(log_state(1))
    q = exp(log_state(2))
    s = log_state(3)
    env = env_template
    env%w = exp(log_w)
    c = compute_coefficients(env)
    call vector_field(n, q, s, env, c, rhs, status)
    if (status /= 0) then
       residual = 0.0_dp
       return
    end if
    residual(1) = rhs(1) / n
    residual(2) = rhs(2) / q
    residual(3) = rhs(3)
  end subroutine equilibrium_residual

end module bs2026_model
