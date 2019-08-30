import numpy as np
import pytest
from ogusa import demographics


def test_get_pop_objs():
    """
    Test of the that omega_SS and the last period of omega_path_S are
    close to each other.
    """
    E = 20
    S = 80
    T = int(round(4.0 * S))
    start_year = 2018

    (omega, g_n_ss, omega_SS, surv_rate, rho, g_n_vector, imm_rates,
        omega_S_preTP) = demographics.get_pop_objs(E, S, T, 1, 100,
                                                   start_year, False)

    assert (np.allclose(omega_SS, omega[-1, :]))


def test_pop_smooth():
    """
    Test that population growth rates evolve smoothly.
    """
    E = 20
    S = 80
    T = int(round(4.0 * S))
    start_year = 2018

    (omega, g_n_ss, omega_SS, surv_rate, rho, g_n_vector, imm_rates,
        omega_S_preTP) = demographics.get_pop_objs(E, S, T, 1, 100,
                                                   start_year, False)

    assert (np.any(np.absolute(omega[:-1, :] - omega[1:, :]) < 0.0001))
    assert (np.any(np.absolute(g_n_vector[:-1] - g_n_vector[1:]) < 0.0001))


def test_imm_smooth():
    """
    Test that population growth rates evolve smoothly.
    """
    E = 20
    S = 80
    T = int(round(4.0 * S))
    start_year = 2018

    (omega, g_n_ss, omega_SS, surv_rate, rho, g_n_vector, imm_rates,
        omega_S_preTP) = demographics.get_pop_objs(E, S, T, 1, 100,
                                                   start_year, False)

    assert (np.any(np.absolute(imm_rates[:-1, :] - imm_rates[1:, :]) <
                   0.0001))


def test_get_fert():
    '''
    Test of function to get fertility rates from data
    '''
    fert_rates = demographics.get_fert(100, 0, 100, graph=False)
    assert (fert_rates.shape[0] == 100)


def test_get_mort():
    '''
    Test of function to get mortality rates from data
    '''
    mort_rates, infmort_rate = demographics.get_mort(
        100, 0, 100, graph=False)
    assert (mort_rates.shape[0] == 100)


def test_infant_mort():
    '''
    Test of function to get mortality rates from data
    '''
    mort_rates, infmort_rate = demographics.get_mort(
        100, 0, 100, graph=False)
    # check that infant mortality equals rate hardcoded into
    # demographics.py
    assert (infmort_rate ==  0.00587)
