'''
------------------------------------------------------------------------
Last updated: 4/8/2016

Calculates steady state of OG-USA model with S age cohorts and J
ability types.

This py-file calls the following other file(s):
            tax.py
            household.py
            firm.py
            utils.py
            OUTPUT/Saved_moments/params_given.pkl
            OUTPUT/Saved_moments/params_changed.pkl
            OUTPUT/Saved_moments/labor_data_moments.pkl
            OUTPUT/Saved_moments/SS_init_solutions.pkl
            OUTPUT/Saved_moments/SS_experiment_solutions.pkl

This py-file creates the following other file(s):
    (make sure that an OUTPUT folder exists)
            OUTPUT/Saved_moments/SS_init_solutions.pkl
            OUTPUT/Saved_moments/SS_experiment_solutions.pkl
            OUTPUT/SSinit/ss_init_vars.pkl
            OUTPUT/SS/ss_vars.pkl
------------------------------------------------------------------------
'''

# Packages
import numpy as np
import scipy.optimize as opt
import cPickle as pickle

from . import tax
from . import household
import firm
import utils
import os


'''
------------------------------------------------------------------------
Imported user given values
------------------------------------------------------------------------
'''
from .parameters import DATASET

'''
------------------------------------------------------------------------
    Define Functions
------------------------------------------------------------------------
'''

# missing args are income_tax_params, wealth_tax_params, and ellipse_params


# def create_steady_state_parameters(analytical_mtrs, etr_params, mtrx_params, mtry_params, 
#                                    b_ellipse, upsilon, J, S, T, BW,
#                                    beta, sigma, alpha, Z, delta, ltilde, nu,
#                                    g_y, tau_payroll, retire,
#                                    mean_income_data, run_params,
#                                    output_dir="./OUTPUT", **kwargs):
def create_steady_state_parameters(**sim_params):
    '''
    --------------------------------------------------------------------
    This function calls the tax function estimation routine and saves
    the resulting dictionary in pickle files corresponding to the
    baseline or reform policy.
    --------------------------------------------------------------------
    
    INPUTS:
    sim_params       = dictionary, dict containing variables for simulation
    analytical_mtrs  = boolean, =True if use analytical_mtrs, =False if 
                       use estimated MTRs
    etr_params       = [S,BW,#tax params] array, parameters for effective tax rate function
    mtrx_params      = [S,BW,#tax params] array, parameters for marginal tax rate on 
                       labor income function
    mtry_params      = [S,BW,#tax params] array, parameters for marginal tax rate on 
                       capital income function
    b_ellipse        = scalar, value of b for elliptical fit of utility function
    upsilon          = scalar, value of omega for elliptical fit of utility function
    S                = integer, number of economically active periods an individual lives
    J                = integer, number of different ability groups
    T                = integer, number of time periods until steady state is reached 
    BW               = integer, number of time periods in the budget window
    beta             = scalar, discount factor for model period
    sigma            = scalar, coefficient of relative risk aversion
    alpha            = scalar, capital share of income 
    Z                = scalar, total factor productivity parameter in firms' production
                       function
    ltilde           = scalar, measure of time each individual is endowed with each
                       period
    nu               = scalar, contraction parameter in SS and TPI iteration process
                       representing the weight on the new distribution
    g_y              = scalar, growth rate of technology for a model period
    tau_payroll      = scalar, payroll tax rate
    retire           = integer, age at which individuals eligible for retirement benefits
    mean_income_data = scalar, mean income from IRS data file used to calibrate income tax
    run_params       = ???
    output_dir       = string, directory for output files to be saved


    OTHER FUNCTIONS AND FILES CALLED BY THIS FUNCTION: None

    OBJECTS CREATED WITHIN FUNCTION:
    income_tax_params = length 3 tuple, (analytical_mtrs, etr_params,
                        mtrx_params,mtry_params)
    wealth_tax_params = [3,] vector, contains values of three parameters 
                        of wealth tax function
    ellipse_params    = [2,] vector, vector with b_ellipse and upsilon 
                        paramters of elliptical utility
    parameters        = length 3 tuple, ([15,] vector of general model 
                        params, wealth_tax_params, ellipse_params)
    iterative_params  = [2,] vector, vector with max iterations and tolerance 
                        for SS solution

    RETURNS: (income_tax_params, wealth_tax_params, ellipse_params,
            parameters, iterative_params)
    
    OUTPUT: None
    --------------------------------------------------------------------
    '''
    # Put income tax parameters in a tuple 
    # Assumption here is that tax parameters of last year of budget
    # window continue forever and so will be SS values
    income_tax_params = (sim_params['analytical_mtrs'], sim_params['etr_params'][:,-1,:],
                         sim_params['mtrx_params'][:,-1,:],sim_params['mtry_params'][:,-1,:])

    # Make a vector of all one dimensional parameters, to be used in the
    # following functions
    wealth_tax_params = [sim_params['h_wealth'], sim_params['p_wealth'], sim_params['m_wealth']]
    ellipse_params = [sim_params['b_ellipse'], sim_params['upsilon']]
    parameters = [sim_params['J'], sim_params['S'], sim_params['T'], sim_params['BW'], 
                  sim_params['beta'], sim_params['sigma'], sim_params['alpha'], 
                  sim_params['Z'], sim_params['delta'], sim_params['ltilde'], 
                  sim_params['nu'], sim_params['g_y'], sim_params['g_n_ss'], 
                  sim_params['tau_payroll'], sim_params['retire'], sim_params['mean_income_data']] + \
                  wealth_tax_params + ellipse_params
    iterative_params = [sim_params['maxiter'], sim_params['mindist_SS']]
    chi_params = (sim_params['chi_b_guess'], sim_params['chi_n_guess'])
    return (income_tax_params, wealth_tax_params, ellipse_params,
            parameters, iterative_params, chi_params)


# def Euler_equation_solver(guesses, r, w, T_H, factor, j, tax_params, params, chi_b, chi_n,
#                           tau_bq, rho, lambdas, omega, e):
def Euler_equation_solver(guesses, r, w, T_H, factor, params):
    '''
    --------------------------------------------------------------------
    Finds the euler errors for certain b and n, one ability type at a time.
    --------------------------------------------------------------------
    
    INPUTS:
    guesses = [2S,] vector, initial guesses for b and n
    r = scalar, real interest rate
    w = scalar, real wage rate
    T_H = scalar, lump sum transfer 
    factor = scalar, scaling factor converting model units to dollars
    j = integer, ability group
    params = length 21 tuple, list of parameters
    chi_b = [J,] vector, chi^b_j, the utility weight on bequests
    chi_n = [S,] vector, chi^n_s utility weight on labor supply
    tau_bq = scalar, bequest tax rate
    rho = [S,] vector, mortality rates by age
    lambdas = [J,] vector, fraction of population with each ability type
    omega = [S,] vector, stationary population weights 
    e =  [S,J] array, effective labor units by age and ability type
    tax_params = length 4 tuple, (analytical_mtrs, etr_params, mtrx_params, mtry_params)
    analytical_mtrs = boolean, =True if use analytical_mtrs, =False if 
                       use estimated MTRs
    etr_params      = [S,BW,#tax params] array, parameters for effective tax rate function
    mtrx_params     = [S,BW,#tax params] array, parameters for marginal tax rate on 
                       labor income function
    mtry_params     = [S,BW,#tax params] array, parameters for marginal tax rate on 
                       capital income function

    OTHER FUNCTIONS AND FILES CALLED BY THIS FUNCTION: 
    household.get_BQ()
    tax.replacement_rate_vals()
    household.euler_savings_func()
    household.euler_labor_leisure_func()
    tax.total_taxes()
    household.get_cons()

    OBJECTS CREATED WITHIN FUNCTION:
    b_guess = [S,] vector, initial guess at household savings
    n_guess = [S,] vector, initial guess at household labor supply
    b_s = [S,] vector, wealth enter period with
    b_splus1 = [S,] vector, household savings
    b_splus2 = [S,] vector, household savings one period ahead
    BQ = scalar, aggregate bequests to lifetime income group
    theta = scalar, replacement rate for social security benenfits
    error1 = [S,] vector, errors from FOC for savings 
    error2 = [S,] vector, errors from FOC for labor supply
    tax1 = [S,] vector, total income taxes paid
    cons = [S,] vector, household consumption

    RETURNS: 2Sx1 list of euler errors
    
    OUTPUT: None
    --------------------------------------------------------------------
    '''

    J, S, beta, sigma, ltilde, g_y,\
                  g_n_ss, tau_payroll, retire, mean_income_data,\
                  h_wealth, p_wealth, m_wealth, b_ellipse, upsilon,\
                  j, chi_b, chi_n, tau_bq, rho, lambdas, omega, e,\
                  analytical_mtrs, etr_params, mtrx_params,\
                  mtry_params = params

    b_guess = np.array(guesses[:S])
    n_guess = np.array(guesses[S:])
    b_s = np.array([0] + list(b_guess[:-1]))
    b_splus1 = b_guess
    b_splus2 = np.array(list(b_guess[1:]) + [0])

    BQ = household.get_BQ(r, b_splus1, omega, lambdas[j], rho, g_n_ss, 'SS')
    theta_params = (e, J, omega, lambdas)
    theta = tax.replacement_rate_vals(n_guess, w, factor, theta_params)

    error1 = household.euler_savings_func(w, r, e[:, j], n_guess, b_s,
                                          b_splus1, b_splus2, BQ, factor, T_H,
                                          chi_b[j], tax_params, params, theta, tau_bq[j],
                                          rho, lambdas[j])

    error2 = household.euler_labor_leisure_func(w, r, e[:, j], n_guess, b_s,
                                                b_splus1, BQ, factor, T_H,
                                                chi_n, tax_params, params, theta,
                                                tau_bq[j], lambdas[j])

    # Put in constraints for consumption and savings.
    # According to the euler equations, they can be negative.  When
    # Chi_b is large, they will be.  This prevents that from happening.
    # I'm not sure if the constraints are needed for labor.
    # But we might as well put them in for now.
    mask1 = n_guess < 0
    mask2 = n_guess > ltilde
    mask3 = b_guess <= 0
    mask4 = np.isnan(n_guess)
    mask5 = np.isnan(b_guess)
    error2[mask1] = 1e14
    error2[mask2] = 1e14
    error1[mask3] = 1e14
    error1[mask5] = 1e14
    error2[mask4] = 1e14
    tax1_params = (J, S, retire, , )

    tax1_params = (e[:, j], lambdas[j], 'SS', retire, etr_params, h_wealth, p_wealth, 
                   m_wealth, tau_payroll, theta, tau_bq[j], J, S)
    tax1 = tax.total_taxes(r, w, b_s, n_guess, BQ, factor, T_H, None, False, tax1_params)
    cons = household.get_cons(r, b_s, w, e[:, j], n_guess, BQ, lambdas[j],
                              b_splus1, params, tax1)
    mask6 = cons < 0
    error1[mask6] = 1e14


    return list(error1.flatten()) + list(error2.flatten())


def SS_solver(b_guess_init, n_guess_init, wguess, rguess, T_Hguess,
              factorguess, chi_n, chi_b, tax_params, params, iterative_params, tau_bq,
              rho, lambdas, omega, e, fsolve_flag=False):
    '''
    --------------------------------------------------------------------
    Solves for the steady state distribution of capital, labor, as well as
    w, r, T_H and the scaling factor, using a bisection method similar to TPI.
    --------------------------------------------------------------------
    
    INPUTS:
    b_guess_init = [S,J] array, initial guesses for savings
    n_guess_init = [S,J] array, initial guesses for labor supply
    wguess = scalar, initial guess for SS real wage rate 
    rguess = scalar, initial guess for SS real interest rate
    T_Hguess = scalar, initial guess for lump sum transfer
    factorguess = scalar, initial guess for scaling factor to dollars
    chi_b = [J,] vector, chi^b_j, the utility weight on bequests
    chi_n = [S,] vector, chi^n_s utility weight on labor supply
    params = lenght X tuple, list of parameters 
    iterative_params = length X tuple, list of parameters that determine the convergence
                       of the while loop 
    tau_bq = [J,] vector, bequest tax rate 
    rho = [S,] vector, mortality rates by age
    lambdas = [J,] vector, fraction of population with each ability type
    omega = [S,] vector, stationary population weights 
    e =  [S,J] array, effective labor units by age and ability type


    OTHER FUNCTIONS AND FILES CALLED BY THIS FUNCTION: 
    Euler_equation_solver()
    household.get_K()
    firm.get_L()
    firm.get_Y()
    firm.get_r()
    firm.get_w()
    household.get_BQ()
    tax.replacement_rate_vals()
    tax.get_lump_sum()
    utils.convex_combo()
    utils.pct_diff_func()




    OBJECTS CREATED WITHIN FUNCTION:
    b_guess = [S,] vector, initial guess at household savings
    n_guess = [S,] vector, initial guess at household labor supply
    b_s = [S,] vector, wealth enter period with
    b_splus1 = [S,] vector, household savings
    b_splus2 = [S,] vector, household savings one period ahead
    BQ = scalar, aggregate bequests to lifetime income group
    theta = scalar, replacement rate for social security benenfits
    error1 = [S,] vector, errors from FOC for savings 
    error2 = [S,] vector, errors from FOC for labor supply
    tax1 = [S,] vector, total income taxes paid
    cons = [S,] vector, household consumption

    RETURNS: solutions = steady state values of b, n, w, r, factor,
                    T_H ((2*S*J+4)x1 array)
    
    OUTPUT: None
    --------------------------------------------------------------------
    '''
    
    J, S, T, BW, beta, sigma, alpha, Z, delta, ltilde, nu, g_y,\
                  g_n_ss, tau_payroll, retire, mean_income_data,\
                  h_wealth, p_wealth, m_wealth, b_ellipse, upsilon = params

    analytical_mtrs, etr_params, mtrx_params, mtry_params = tax_params

    maxiter, mindist_SS = iterative_params
    # Rename the inputs
    w = wguess
    r = rguess
    T_H = T_Hguess
    factor = factorguess
    bssmat = b_guess_init
    nssmat = n_guess_init

    dist = 10
    iteration = 0
    dist_vec = np.zeros(maxiter)

    if fsolve_flag == True:
        maxiter = 1 


    while (dist > mindist_SS) and (iteration < maxiter):
        # Solve for the steady state levels of b and n, given w, r, T_H and
        # factor
        for j in xrange(J):
            # Solve the euler equations
            if j == 0:
                guesses = np.append(bssmat[:, j], nssmat[:, j])
            else:
                guesses = np.append(bssmat[:, j-1], nssmat[:, j-1])

            args_ = (r, w, T_H, factor, j, tax_params, params, chi_b, chi_n, tau_bq, rho,
                     lambdas, omega, e)
            [solutions, infodict, ier, message] = opt.fsolve(Euler_equation_solver, guesses * .9,
                                   args=args_, xtol=1e-13, full_output=True)

            print 'Max Euler errors: ', np.absolute(infodict['fvec']).max()

            bssmat[:, j] = solutions[:S]
            nssmat[:, j] = solutions[S:]
        
        K_params = (omega.reshape(S, 1), lambdas.reshape(1, J), g_n_ss, 'SS')
        K = household.get_K(bssmat, K_params)
        L_params = (e, omega.reshape(S, 1), lambdas.reshape(1, J), 'SS')
        L = firm.get_L(nssmat, L_params)
        Y_params = (alpha, Z)
        Y = firm.get_Y(K, L, Y_params)
        r_params = (alpha, delta)
        new_r = firm.get_r(Y, K, r_params)
        new_w = firm.get_w(Y, L, alpha)
        b_s = np.array(list(np.zeros(J).reshape(1, J)) + list(bssmat[:-1, :]))
        average_income_model = ((new_r * b_s + new_w * e * nssmat) *
                                omega.reshape(S, 1) *
                                lambdas.reshape(1, J)).sum()
        new_factor = mean_income_data / average_income_model
        new_BQ = household.get_BQ(new_r, bssmat, omega.reshape(S, 1),
                                  lambdas.reshape(1, J), rho.reshape(S, 1),
                                  g_n_ss, 'SS')
        
        theta_params = (e, J, omega.reshape(S, 1), lambdas)
        theta = tax.replacement_rate_vals(nssmat, new_w, new_factor, theta_params)

        T_H_params = (e, lambdas.reshape(1, J), omega.reshape(S, 1), 'SS', etr_params, theta, tau_bq,
                      tau_payroll, h_wealth, p_wealth, m_wealth, retire, T, S, J)
        new_T_H = tax.get_lump_sum(new_r, new_w, b_s, nssmat, new_BQ, factor, T_H_params)

        r = utils.convex_combo(new_r, r, nu)
        w = utils.convex_combo(new_w, w, nu)
        factor = utils.convex_combo(new_factor, factor, nu)
        T_H = utils.convex_combo(new_T_H, T_H, nu)
        if T_H != 0:
            dist = np.array([utils.pct_diff_func(new_r, r)] +
                            [utils.pct_diff_func(new_w, w)] +
                            [utils.pct_diff_func(new_T_H, T_H)] +
                            [utils.pct_diff_func(new_factor, factor)]).max()
        else:
            # If T_H is zero (if there are no taxes), a percent difference
            # will throw NaN's, so we use an absoluate difference
            dist = np.array([utils.pct_diff_func(new_r, r)] +
                            [utils.pct_diff_func(new_w, w)] +
                            [abs(new_T_H - T_H)] +
                            [utils.pct_diff_func(new_factor, factor)]).max()
        dist_vec[iteration] = dist
        # Similar to TPI: if the distance between iterations increases, then
        # decrease the value of nu to prevent cycling
        if iteration > 10:
            if dist_vec[iteration] - dist_vec[iteration - 1] > 0:
                nu /= 2.0
                print 'New value of nu:', nu
        iteration += 1
        print "Iteration: %02d" % iteration, " Distance: ", dist

    eul_errors = np.ones(J)
    b_mat = np.zeros((S, J))
    n_mat = np.zeros((S, J))
    # Given the final w, r, T_H and factor, solve for the SS b and n (if you
    # don't do a final fsolve, there will be a slight mismatch,
    # with high euler errors)
    for j in xrange(J):
        guesses = np.append(bssmat[:, j], nssmat[:, j])
        args_ = (r, w, T_H, factor, j, tax_params, params, chi_b, chi_n, tau_bq, rho,
                 lambdas, omega, e)
        [solutions1, infodict, ier, message] = opt.fsolve(Euler_equation_solver, guesses * .9,
                                   args=args_, xtol=1e-13, full_output=True)
        eul_errors[j] = np.array(infodict['fvec']).max()
        print 'Max Euler errors: ', np.absolute(infodict['fvec']).max()
        b_mat[:, j] = solutions1[:S]
        n_mat[:, j] = solutions1[S:]
    print 'SS fsolve euler error:', eul_errors.max()
    solutions = np.append(b_mat.flatten(), n_mat.flatten())
    other_vars = np.array([w, r, factor, T_H])
    solutions = np.append(solutions, other_vars)
    return solutions

# def SS_fsolve(guesses, b_guess_init, n_guess_init, chi_n, chi_b, tax_params, params, iterative_params, tau_bq,
#               rho, lambdas, omega, e):
def SS_fsolve(guesses, params):
    '''
    Solves for the steady state distribution of capital, labor, as well as
    w, r, T_H and the scaling factor, using an a root finder.
    Inputs:
        b_guess_init = guesses for b (SxJ array)
        n_guess_init = guesses for n (SxJ array)
        wguess = guess for wage rate (scalar)
        rguess = guess for rental rate (scalar)
        T_Hguess = guess for lump sum tax (scalar)
        factorguess = guess for scaling factor to dollars (scalar)
        chi_n = chi^n_s (Sx1 array)
        chi_b = chi^b_j (Jx1 array)
        params = list of parameters (list)
        iterative_params = list of parameters that determine the convergence
                           of the while loop (list)
        tau_bq = bequest tax rate (Jx1 array)
        rho = mortality rates (Sx1 array)
        lambdas = ability weights (Jx1 array)
        omega = population weights (Sx1 array)
        e = ability levels (SxJ array)
    Outputs:
        solutions = steady state values of b, n, w, r, factor,
                    T_H ((2*S*J+4)x1 array)
    '''
    
    ss_params = (b_guess.reshape(S, J), n_guess.reshape(S, J), chi_params[J:], chi_params[:J], 
             income_tax_parameters, ss_parameters, iterative_params, tau_bq, rho, lambdas, omega_SS, e)

    J, S, T, BW, beta, sigma, alpha, Z, delta, ltilde, nu, g_y,\
                  g_n_ss, tau_payroll, retire, mean_income_data,\
                  h_wealth, p_wealth, m_wealth, b_ellipse, upsilon = params

    analytical_mtrs, etr_params, mtrx_params, mtry_params = tax_params

    maxiter, mindist_SS = iterative_params
    # Rename the inputs
    w = guesses[0]
    r = guesses[1]
    T_H = guesses[2]
    factor = guesses[3]
    bssmat = b_guess_init
    nssmat = n_guess_init

    # Solve for the steady state levels of b and n, given w, r, T_H and
    # factor
    for j in xrange(J):
        # Solve the euler equations
        if j == 0:
            guesses = np.append(bssmat[:, j], nssmat[:, j])
        else:
            guesses = np.append(bssmat[:, j-1], nssmat[:, j-1])
        args_ = (r, w, T_H, factor, j, tax_params, params, chi_b, chi_n, tau_bq, rho,
                 lambdas, omega, e)
        [solutions, infodict, ier, message] = opt.fsolve(Euler_equation_solver, guesses * .9,
                                   args=args_, xtol=1e-13, full_output=True)

        print 'Max Euler errors: ', np.absolute(infodict['fvec']).max()
        
        bssmat[:, j] = solutions[:S]
        nssmat[:, j] = solutions[S:]
        # print np.array(Euler_equation_solver(np.append(bssmat[:, j],
        # nssmat[:, j]), r, w, T_H, factor, j, params, chi_b, chi_n,
        # theta, tau_bq, rho, lambdas, e)).max()

    K_params = (omega.reshape(S, 1), lambdas.reshape(1, J), g_n_ss, 'SS')
    K = household.get_K(bssmat, K_params)
    L_params = (e, omega.reshape(S, 1), lambdas.reshape(1, J), 'SS')
    L = firm.get_L(nssmat, L_params)
    Y_params = (alpha, Z)
    Y = firm.get_Y(K, L, Y_params)
    r_params = (alpha, delta)
    new_r = firm.get_r(Y, K, r_params)
    new_w = firm.get_w(Y, L, alpha)
    b_s = np.array(list(np.zeros(J).reshape(1, J)) + list(bssmat[:-1, :]))
    average_income_model = ((new_r * b_s + new_w * e * nssmat) *
                            omega.reshape(S, 1) *
                            lambdas.reshape(1, J)).sum()
    new_factor = mean_income_data / average_income_model
    new_BQ = household.get_BQ(new_r, bssmat, omega.reshape(S, 1),
                              lambdas.reshape(1, J), rho.reshape(S, 1),
                              g_n_ss, 'SS')

    theta_params = (e, J, omega.reshape(S, 1), lambdas)
    theta = tax.replacement_rate_vals(nssmat, new_w, new_factor, theta_params)

    T_H_params = (e, lambdas.reshape(1, J), omega.reshape(S, 1), 'SS', etr_params, theta, tau_bq,
                      tau_payroll, h_wealth, p_wealth, m_wealth, retire, T, S, J)
    new_T_H = tax.get_lump_sum(new_r, new_w, b_s, nssmat, new_BQ, factor, T_H_params)

    error1 = new_w - w
    error2 = new_r - r
    error3 = new_T_H - T_H
    error4 = new_factor/1000000 - factor/1000000

    print 'mean income in model and data: ', average_income_model, mean_income_data
    print 'model income with factor: ', average_income_model*factor

    print 'errors: ', error1, error2, error3, error4
    print 'T_H: ', new_T_H
    print 'factor: ', new_factor
    print 'interest rate: ', new_r

    # Check and punish violations
    if r <= 0:
        error1 += 1e9
    #if r > 1:
    #    error1 += 1e9
    if w <= 0:
        error2 += 1e9

    return [error1, error2, error3, error4]

def SS_fsolve_reform(guesses, b_guess_init, n_guess_init, factor, chi_n, chi_b, tax_params, params, iterative_params, tau_bq,
              rho, lambdas, omega, e):
    '''
    Solves for the steady state distribution of capital, labor, as well as
    w, r, and T_H and the scaling factor, using a root finder. This solves for the 
    reform SS and so takes the factor from the baseline SS as an input.
    Inputs:
        b_guess_init = guesses for b (SxJ array)
        n_guess_init = guesses for n (SxJ array)
        wguess = guess for wage rate (scalar)
        rguess = guess for rental rate (scalar)
        T_Hguess = guess for lump sum tax (scalar)
        factor = scaling factor to dollars (scalar)
        chi_n = chi^n_s (Sx1 array)
        chi_b = chi^b_j (Jx1 array)
        params = list of parameters (list)
        iterative_params = list of parameters that determine the convergence
                           of the while loop (list)
        tau_bq = bequest tax rate (Jx1 array)
        rho = mortality rates (Sx1 array)
        lambdas = ability weights (Jx1 array)
        omega = population weights (Sx1 array)
        e = ability levels (SxJ array)
    Outputs:
        solutions = steady state values of b, n, w, r, factor,
                    T_H ((2*S*J+4)x1 array)
    '''
    
    J, S, T, BW, beta, sigma, alpha, Z, delta, ltilde, nu, g_y,\
                  g_n_ss, tau_payroll, retire, mean_income_data,\
                  h_wealth, p_wealth, m_wealth, b_ellipse, upsilon = params

    analytical_mtrs, etr_params, mtrx_params, mtry_params = tax_params

    maxiter, mindist_SS = iterative_params
    # Rename the inputs
    w = guesses[0]
    r = guesses[1]
    T_H = guesses[2]
    bssmat = b_guess_init
    nssmat = n_guess_init


    print 'Reform SS factor is: ', factor

    # Solve for the steady state levels of b and n, given w, r, T_H and
    # factor
    for j in xrange(J):
        # Solve the euler equations
        if j == 0:
            guesses = np.append(bssmat[:, j], nssmat[:, j])
        else:
            guesses = np.append(bssmat[:, j-1], nssmat[:, j-1])
        args_ = (r, w, T_H, factor, j, tax_params, params, chi_b, chi_n, tau_bq, rho,
                 lambdas, omega, e)
        [solutions, infodict, ier, message] = opt.fsolve(Euler_equation_solver, guesses * .9,
                                   args=args_, xtol=1e-13, full_output=True)

        print 'Max Euler errors: ', np.absolute(infodict['fvec']).max()
        
        bssmat[:, j] = solutions[:S]
        nssmat[:, j] = solutions[S:]
        # print np.array(Euler_equation_solver(np.append(bssmat[:, j],
        # nssmat[:, j]), r, w, T_H, factor, j, params, chi_b, chi_n,
        # theta, tau_bq, rho, lambdas, e)).max()

    K_params = (omega.reshape(S, 1), lambdas.reshape(1, J), g_n_ss, 'SS')
    K = household.get_K(bssmat, K_params)
    L_params = (e, omega.reshape(S, 1), lambdas.reshape(1, J), 'SS')
    L = firm.get_L(nssmat, L_params)
    Y_params = (alpha, Z)
    Y = firm.get_Y(K, L, Y_params)
    r_params = (alpha, delta)
    new_r = firm.get_r(Y, K, r_params)
    new_w = firm.get_w(Y, L, alpha)
    b_s = np.array(list(np.zeros(J).reshape(1, J)) + list(bssmat[:-1, :]))
    average_income_model = ((new_r * b_s + new_w * e * nssmat) *
                            omega.reshape(S, 1) *
                            lambdas.reshape(1, J)).sum()
    new_factor = mean_income_data / average_income_model
    new_BQ = household.get_BQ(new_r, bssmat, omega.reshape(S, 1),
                              lambdas.reshape(1, J), rho.reshape(S, 1),
                              g_n_ss, 'SS')
    theta_params = (e, J, omega.reshape(S, 1), lambdas)
    theta = tax.replacement_rate_vals(nssmat, new_w, new_factor, theta_params)

    T_H_params = (e, lambdas.reshape(1, J), omega.reshape(S, 1), 'SS', etr_params, theta, tau_bq,
                      tau_payroll, h_wealth, p_wealth, m_wealth, retire, T, S, J)
    new_T_H = tax.get_lump_sum(new_r, new_w, b_s, nssmat, new_BQ, factor, T_H_params)

    error1 = new_w - w
    error2 = new_r - r
    error3 = new_T_H - T_H
    print 'errors: ', error1, error2, error3
    print 'T_H: ', new_T_H


    # Check and punish violations
    if r <= 0:
        error1 += 1e9
    #if r > 1:
    #    error1 += 1e9
    if w <= 0:
        error2 += 1e9

    return [error1, error2, error3]





def function_to_minimize(chi_params_scalars, chi_params_init, income_tax_parameters, ss_parameters, 
                         iterative_params, omega_SS, rho_vec, lambdas, tau_bq, e, output_dir):
    '''
    Inputs:
        chi_params_scalars = guesses for multipliers for chi parameters
                             ((S+J)x1 array)
        chi_params_init = chi parameters that will be multiplied
                          ((S+J)x1 array)
        params = list of parameters (list)
        omega_SS = steady state population weights (Sx1 array)
        rho_vec = mortality rates (Sx1 array)
        lambdas = ability weights (Jx1 array)
        tau_bq = bequest tax rates (Jx1 array)
        e = ability levels (Jx1 array)
    Output:
        The sum of absolute percent deviations between the actual and
        simulated wealth moments
    '''
    J, S, T, BW, beta, sigma, alpha, Z, delta, ltilde, nu, g_y,\
                  g_n_ss, tau_payroll, retire, mean_income_data,\
                  h_wealth, p_wealth, m_wealth, b_ellipse, upsilon = ss_parameters

    analytical_mtrs, etr_params, mtrx_params, mtry_params = income_tax_parameters

    chi_params_init *= chi_params_scalars
    # print 'Print Chi_b: ', chi_params_init[:J]
    # print 'Scaling vals:', chi_params_scalars[:J]
    ss_init_path = os.path.join(output_dir,
                                "Saved_moments/SS_init_solutions.pkl")
    solutions_dict = pickle.load(open(ss_init_path, "rb"))
    solutions = solutions_dict['solutions']

    b_guess = solutions[:(S * J)]
    n_guess = solutions[S * J:2 * S * J]
    wguess, rguess, factorguess, T_Hguess = solutions[(2 * S * J):]
    guesses = [wguess, rguess, T_Hguess, factorguess]
    args_ = (b_guess.reshape(S, J), n_guess.reshape(S, J), chi_params_init[J:], chi_params_init[:J], 
                 income_tax_parameters, ss_parameters, iterative_params, tau_bq, rho, lambdas, omega_SS, e)
    [solutions, infodict, ier, message] = opt.fsolve(SS_fsolve, guesses, args=args_, xtol=mindist_SS, full_output=True)
    [wguess, rguess, T_Hguess, factorguess] = solutions
    fsolve_flag = True
    solutions = SS_solver(b_guess.reshape(S, J), n_guess.reshape(S, J), wguess, rguess, T_Hguess, factorguess, chi_params_init[
                              J:], chi_params_init[:J], income_tax_parameters, ss_parameters, iterative_params, tau_bq, rho, lambdas, omega_SS, e, fsolve_flag)


    b_new = solutions[:(S * J)]
    n_new = solutions[(S * J):(2 * S * J)]
    w_new, r_new, factor_new, T_H_new = solutions[(2 * S * J):]
    # Wealth Calibration Euler
    error5 = list(utils.check_wealth_calibration(b_new.reshape(S, J)[:-1, :],
                                                 factor_new, ss_parameters, output_dir))
    # labor calibration euler
    labor_path = os.path.join(
        output_dir, "Saved_moments/labor_data_moments.pkl")
    lab_data_dict = pickle.load(open(labor_path, "rb"))
    labor_sim = (n_new.reshape(S, J) * lambdas.reshape(1, J)).sum(axis=1)
    if DATASET == 'SMALL':
        lab_dist_data = lab_data_dict['labor_dist_data'][:S]
    else:
        lab_dist_data = lab_data_dict['labor_dist_data']

    error6 = list(utils.pct_diff_func(labor_sim, lab_dist_data))
    # combine eulers
    output = np.array(error5 + error6)
    # Constraints
    eul_error = np.ones(J)
    for j in xrange(J):
        eul_error[j] = np.abs(Euler_equation_solver(np.append(b_new.reshape(S, J)[:, j], n_new.reshape(S, J)[:, j]), r_new, w_new,
                                                    T_H_new, factor_new, j, income_tax_parameters, ss_parameters, chi_params_init[:J], chi_params_init[J:], tau_bq, rho, lambdas, omega_SS, e)).max()
    fsolve_no_converg = eul_error.max()
    if np.isnan(fsolve_no_converg):
        fsolve_no_converg = 1e6
    if fsolve_no_converg > 1e-4:
        # If the fsovle didn't converge (was NaN or above the tolerance), then tell the minimizer that this is a bad place to be
        # and don't save the solutions as initial guesses (since they might be
        # gibberish)
        output += 1e14
    else:
        var_names = ['solutions']
        dictionary = {}
        for key in var_names:
            dictionary[key] = locals()[key]
        ss_init_path = os.path.join(
            output_dir, "Saved_moments/SS_init_solutions.pkl")
        pickle.dump(dictionary, open(ss_init_path, "wb"))
    if (chi_params_init <= 0.0).any():
        # In case the minimizer doesn't respect the bounds given
        output += 1e14
    # Use generalized method of moments to fit the chi's
    weighting_mat = np.eye(2 * J + S)
    scaling_val = 100.0
    value = np.dot(scaling_val * np.dot(output.reshape(1, 2 * J + S),
                                        weighting_mat), scaling_val * output.reshape(2 * J + S, 1))
    print 'Value of criterion function: ', value.sum()

    
    # pickle output in case not converge
    global Nfeval, value_all, chi_params_all
    value_all[Nfeval] = value.sum()
    chi_params_all[:,Nfeval] = chi_params_init
    dict_GMM = dict([('values', value_all), ('chi_params', chi_params_all)])
    ss_init_path = os.path.join(output_dir, "Saved_moments/SS_init_all.pkl")
    pickle.dump(dict_GMM, open(ss_init_path, "wb"))
    Nfeval += 1

    return value.sum()


def callbackF(chi,chi_params, income_tax_parameters, ss_parameters, iterative_params, omega_SS, rho, lambdas, tau_bq, e, output_dir):
    '''
    ------------------------------------------------------------------------
      Callback function for minimizer - to save array and function eval at each iteration
    ------------------------------------------------------------------------
    '''
    global Nfeval, value_all, chi_params_all
    #print '{0:4d}   {1: 3.6f}   {2: 3.6f}   {3: 3.6f}   {4: 3.6f}'.format(Nfeval, Xi[0], Xi[1], Xi[2], rosen(Xi))
    # pickle output in case not converge
    value_all[Nfeval] = function_to_minimize(chi,chi_params, income_tax_parameters, ss_parameters, iterative_params, omega_SS, rho, lambdas, tau_bq, e, output_dir)
    chi_params_all[:,Nfeval] = chi
    dict_GMM = dict([('values', value_all), ('chi_params', chi_params_all)])
    ss_init_path = os.path.join(output_dir, "Saved_moments/SS_init_all.pkl")
    pickle.dump(dict_GMM, open(ss_init_path, "wb"))

    Nfeval += 1


def run_steady_state(income_tax_parameters, ss_parameters, iterative_params, chi_params, baseline=True, calibrate_model=False, output_dir="./OUTPUT", baseline_dir="./OUTPUT"):
    '''
    --------------------------------------------------------------------
    Solve for SS of OG-USA.
    --------------------------------------------------------------------
    
    INPUTS:
    income_tax_parameters = length 4 tuple, (analytical_mtrs, etr_params, mtrx_params, mtry_params)
    ss_parameters = length 21 tuple, (J, S, T, BW, beta, sigma, alpha, Z, delta, ltilde, nu, g_y,\
                  g_n_ss, tau_payroll, retire, mean_income_data,\
                  h_wealth, p_wealth, m_wealth, b_ellipse, upsilon)
    iterative_params  = [2,] vector, vector with max iterations and tolerance 
                        for SS solution
    baseline = boolean, =True if run is for baseline tax policy
    calibrate_model = boolean, =True if run calibration of chi parameters
    output_dir = string, path to save output from current model run
    baseline_dir = string, path where baseline results located


    OTHER FUNCTIONS AND FILES CALLED BY THIS FUNCTION:
    SS_fsolve()

    OBJECTS CREATED WITHIN FUNCTION:
    chi_params = [J+S,] vector, chi_b and chi_n stacked together
    b_guess = [S,J] array, initial guess at savings
    n_guess = [S,J] array, initial guess at labor supply
    wguess = scalar, initial guess at SS real wage rate
    rguess = scalar, initial guess at SS real interest rate
    T_Hguess = scalar, initial guess at SS lump sum transfers
    factorguess = scalar, initial guess at SS factor adjustment (to scale model units to dollars)

    output 
    

    RETURNS: output
    
    OUTPUT: None
    --------------------------------------------------------------------
    '''

    J, S, T, BW, beta, sigma, alpha, Z, delta, ltilde, nu, g_y,\
                  g_n_ss, tau_payroll, retire, mean_income_data,\
                  h_wealth, p_wealth, m_wealth, b_ellipse, upsilon = ss_parameters

    analytical_mtrs, etr_params, mtrx_params, mtry_params = income_tax_parameters

    chi_b_guess, chi_n_guess = chi_b_params

    # Generate initial guesses for chi^b_j and chi^n_s
    chi_params = np.zeros(S + J)
    chi_params[:J] = chi_b_guess
    chi_params[J:] = chi_n_guess
    # First run SS simulation with guesses at initial values for b, n, w, r, etc
    # For inital guesses of b and n, we choose very small b, and medium n
    b_guess = np.ones((S, J)).flatten() * 0.05
    n_guess = np.ones((S, J)).flatten() * .4 * ltilde
    # For initial guesses of w, r, T_H, and factor, we use values that are close
    # to some steady state values.

    if baseline:
        wguess = 1.2
        rguess = .06
        T_Hguess = 0.12 
        factorguess = 70000
        ss_params = (b_guess.reshape(S, J), n_guess.reshape(S, J), chi_params[J:], chi_params[:J], 
             income_tax_parameters, ss_parameters, iterative_params, tau_bq, rho, lambdas, omega_SS, e)
        guesses = [wguess, rguess, T_Hguess, factorguess]
        [solutions, infodict, ier, message] = opt.fsolve(SS_fsolve, guesses, args=ss_params, xtol=mindist_SS, full_output=True)
        [wguess, rguess, T_Hguess, factorguess] = solutions
        fsolve_flag = True
        solutions = SS_solver(b_guess.reshape(S, J), n_guess.reshape(S, J), wguess, rguess, T_Hguess, factorguess, chi_params[
                          J:], chi_params[:J], income_tax_parameters, ss_parameters, iterative_params, tau_bq, rho, lambdas, omega_SS, e, fsolve_flag)
    else:
        baseline_ss_dir = os.path.join(
            baseline_dir, "Saved_moments/SS_baseline_solutions.pkl")
        ss_solutions = pickle.load(open(baseline_ss_dir, "rb"))
        [wguess, rguess, factor, T_Hguess] = ss_solutions['solutions'][2 * S * J:]
        args_ = (b_guess.reshape(S, J), n_guess.reshape(S, J), factor, chi_params[J:], chi_params[:J], 
             income_tax_parameters, ss_parameters, iterative_params, tau_bq, rho, lambdas, omega_SS, e)
        guesses = [wguess, rguess, T_Hguess]
        [solutions, infodict, ier, message] = opt.fsolve(SS_fsolve_reform, guesses, args=args_, xtol=mindist_SS, full_output=True)
        [wguess, rguess, T_Hguess] = solutions
        fsolve_flag = True
        solutions = SS_solver(b_guess.reshape(S, J), n_guess.reshape(S, J), wguess, rguess, T_Hguess, factor, chi_params[
                          J:], chi_params[:J], income_tax_parameters, ss_parameters, iterative_params, tau_bq, rho, lambdas, omega_SS, e, fsolve_flag)
    

    if calibrate_model:
        global Nfeval, value_all, chi_params_all
        Nfeval = 1
        value_all = np.zeros((10000))
        chi_params_all = np.zeros((S+J,10000))
        outputs = {'solutions': solutions, 'chi_params': chi_params}
        ss_init_path = os.path.join(
            output_dir, "Saved_moments/SS_init_solutions.pkl")
        pickle.dump(outputs, open(ss_init_path, "wb"))
        function_to_minimize_X = lambda x: function_to_minimize(
            x, chi_params, income_tax_parameters, ss_parameters, iterative_params, omega_SS, rho, lambdas, tau_bq, e, output_dir)
        bnds = tuple([(1e-6, None)] * (S + J))
        # In order to scale all the parameters to estimate in the minimizer, we have the minimizer fit a vector of ones that
        # will be multiplied by the chi initial guesses inside the function.  Otherwise, if chi^b_j=1e5 for some j, and the
        # minimizer peturbs that value by 1e-8, the % difference will be extremely small, outside of the tolerance of the
        # minimizer, and it will not change that parameter.
        chi_params_scalars = np.ones(S + J)
        #chi_params_scalars = opt.minimize(function_to_minimize_X, chi_params_scalars,
        #                                  method='TNC', tol=MINIMIZER_TOL, bounds=bnds, callback=callbackF(chi_params_scalars), options=MINIMIZER_OPTIONS).x
        # chi_params_scalars = opt.minimize(function_to_minimize, chi_params_scalars, 
        #                                   args=(chi_params, income_tax_parameters, ss_parameters, iterative_params, 
        #                                     omega_SS, rho, lambdas, tau_bq, e, output_dir),
        #                                   method='TNC', tol=MINIMIZER_TOL, bounds=bnds, 
        #                                   callback=callbackF(chi_params_scalars,chi_params, income_tax_parameters, 
        #                                     ss_parameters, iterative_params, omega_SS, rho, lambdas, tau_bq, e, output_dir), 
        #                                   options=MINIMIZER_OPTIONS).x
        chi_params_scalars = opt.minimize(function_to_minimize, chi_params_scalars, 
                                          args=(chi_params, income_tax_parameters, ss_parameters, iterative_params, 
                                            omega_SS, rho, lambdas, tau_bq, e, output_dir),
                                          method='TNC', tol=MINIMIZER_TOL, bounds=bnds, 
                                          options=MINIMIZER_OPTIONS).x
        chi_params *= chi_params_scalars
        print 'The final scaling params', chi_params_scalars
        print 'The final bequest parameter values:', chi_params

        solutions_dict = pickle.load(open(ss_init_path, "rb"))
        solutions = solutions_dict['solutions']
        b_guess = solutions[:S * J]
        n_guess = solutions[S * J:2 * S * J]
        wguess, rguess, factorguess, T_Hguess = solutions[2 * S * J:]
        guesses = [wguess, rguess, T_Hguess, factorguess]
        args_ = (b_guess.reshape(S, J), n_guess.reshape(S, J), chi_params[J:], chi_params[:J], 
             income_tax_parameters, ss_parameters, iterative_params, tau_bq, rho, lambdas, omega_SS, e)
        [solutions, infodict, ier, message] = opt.fsolve(SS_fsolve, guesses, args=args_, xtol=mindist_SS, full_output=True)
        [wguess, rguess, T_Hguess, factorguess] = solutions
        fsolve_flag = True
        solutions = SS_solver(b_guess.reshape(S, J), n_guess.reshape(S, J), wguess, rguess, T_Hguess, factorguess, chi_params[
                          J:], chi_params[:J], income_tax_parameters, ss_parameters, iterative_params, tau_bq, rho, lambdas, omega_SS, e, fsolve_flag)


    '''
    ------------------------------------------------------------------------
        Generate the SS values of variables, including euler errors
    ------------------------------------------------------------------------
    '''

    if baseline:
        outputs = {'solutions': solutions, 'chi_params': chi_params}
        ss_init_dir = os.path.join(
            output_dir, "Saved_moments/SS_baseline_solutions.pkl")
        pickle.dump(outputs, open(ss_init_dir, "wb"))
    else:
        outputs = {'solutions': solutions, 'chi_params': chi_params}
        ss_exp_dir = os.path.join(
            output_dir, "Saved_moments/SS_reform_solutions.pkl")
        pickle.dump(outputs, open(ss_exp_dir, "wb"))

    bssmat = solutions[0:(S - 1) * J].reshape(S - 1, J)
    bq = solutions[(S - 1) * J:S * J] # technically, this is just the intentional bequests - wealth of those with max age
    bssmat_s = np.array(list(np.zeros(J).reshape(1, J)) + list(bssmat))
    bssmat_splus1 = np.array(list(bssmat) + list(bq.reshape(1, J)))
    nssmat = solutions[S * J:2 * S * J].reshape(S, J)
    wss, rss, factor_ss, T_Hss = solutions[2 * S * J:]

    Kss = household.get_K(bssmat_splus1, omega_SS.reshape(
        S, 1), lambdas, g_n_ss, 'SS')
  
    Lss_params = (e, omega_SS.reshape(S, 1), lambdas, 'SS')
    Lss = firm.get_L(nssmat)
    Yss_params = (alpha, Z)
    Yss = firm.get_Y(Kss, Lss, Yss_params)
    Iss_params = (delta, g_y, g_n_ss)
    Iss = firm.get_I(Kss, Kss, Iss_params)

    theta = np.zeros(J) # zero out payroll taxes since included in tax functions
    # theta_params = (e, J, omega_SS.reshape(S, 1), lambdas)
    # tax.replacement_rate_vals(nssmat, wss, factor_ss, theta_params)
    BQss = household.get_BQ(rss, bssmat_splus1, omega_SS.reshape(
        S, 1), lambdas, rho.reshape(S, 1), g_n_ss, 'SS')
    b_s = np.array(list(np.zeros(J).reshape((1, J))) + list(bssmat))
    
    etr_params_3D = np.tile(np.reshape(etr_params,(S,1,etr_params.shape[1])),(1,J,1))
    mtrx_params_3D = np.tile(np.reshape(mtrx_params,(S,1,mtrx_params.shape[1])),(1,J,1))
    etr_params_extended = np.append(etr_params,np.reshape(etr_params[-1,:],(1,etr_params.shape[1])),axis=0)[1:,:]
    etr_params_extended_3D = np.tile(np.reshape(etr_params_extended,(S,1,etr_params_extended.shape[1])),(1,J,1))
    mtry_params_extended = np.append(mtry_params,np.reshape(mtry_params[-1,:],(1,mtry_params.shape[1])),axis=0)[1:,:]
    mtry_params_extended_3D = np.tile(np.reshape(mtry_params_extended,(S,1,mtry_params_extended.shape[1])),(1,J,1))
    e_extended = np.array(list(e) + list(np.zeros(J).reshape(1, J))) 
    nss_extended = np.array(list(nssmat) + list(np.zeros(J).reshape(1, J))) 
    mtry_params = (e_extended[1:,:],etr_params_extended_3D, mtry_params_extended_3D,analytical_mtrs)
    mtry_ss = tax.MTR_capital(rss, wss, bssmat_splus1, nss_extended[1:,:], factor_ss, mtry_params)
    mtrx_params = (e, etr_params_3D, mtrx_params_3D, analytical_mtrs)
    mtrx_ss = tax.MTR_labor(rss, wss, bssmat_s, nssmat, factor_ss, mtrx_params)

    # np.savetxt("mtr_ss_capital.csv", mtry_ss, delimiter=",")
    # np.savetxt("mtr_ss_labor.csv", mtrx_ss, delimiter=",")

    taxss_params = (e, lambdas, 'SS', retire, np.tile(np.reshape(etr_params,(S,1,etr_params.shape[1])),(1,J,1)), 
                    h_wealth, p_wealth, m_wealth, tau_payroll, theta, tau_bq, J, S)
    taxss = tax.total_taxes(rss, wss, b_s, nssmat, BQss, factor_ss, T_Hss, None, False, taxss_params)
    cssmat = household.get_cons(rss, b_s, wss, e, nssmat, BQss.reshape(
        1, J), lambdas.reshape(1, J), bssmat_splus1, ss_parameters, taxss)

    Css = household.get_C(cssmat, omega_SS.reshape(S, 1), lambdas, 'SS')

    resource_constraint = Yss - (Css + Iss)

    print 'Resource Constraint Difference:', resource_constraint

    constraint_params = ltilde
    household.constraint_checker_SS(bssmat, nssmat, cssmat, constraint_params)

    b_s = np.array(list(np.zeros(J).reshape((1, J))) + list(bssmat))
    b_splus1 = bssmat_splus1
    b_splus2 = np.array(list(bssmat_splus1[1:]) + list(np.zeros(J).reshape((1, J))))

    chi_b = np.tile(chi_params[:J].reshape(1, J), (S, 1))
    chi_n = np.array(chi_params[J:])
    euler_savings = np.zeros((S, J))
    euler_labor_leisure = np.zeros((S, J))
    for j in xrange(J):
        euler_savings[:, j] = household.euler_savings_func(wss, rss, e[:, j], nssmat[:, j], b_s[:, j], b_splus1[:, j], 
                                 b_splus2[:, j], BQss[j], factor_ss, T_Hss, chi_b[:, j], income_tax_parameters, ss_parameters, 
                                 theta[j], tau_bq[j], rho, lambdas[j])
        euler_labor_leisure[:, j] = household.euler_labor_leisure_func(wss, rss, e[:, j], nssmat[:, j], b_s[:, j], 
                                     b_splus1[:, j], BQss[j], factor_ss, T_Hss, chi_n, income_tax_parameters, 
                                     ss_parameters, theta[j], tau_bq[j], lambdas[j])
    '''
    ------------------------------------------------------------------------
        Save the values in various ways, depending on the stage of
            the simulation, to be used in TPI or graphing functions
    ------------------------------------------------------------------------
    '''

    # Pickle variables
    output = {'Kss': Kss, 'bssmat': bssmat, 'Lss': Lss, 'Css':Css, 'nssmat': nssmat, 'Yss': Yss,
              'wss': wss, 'rss': rss, 'theta': theta, 'BQss': BQss, 'factor_ss': factor_ss,
              'bssmat_s': bssmat_s, 'cssmat': cssmat, 'bssmat_splus1': bssmat_splus1,
              'T_Hss': T_Hss, 'euler_savings': euler_savings,
              'euler_labor_leisure': euler_labor_leisure, 'chi_n': chi_n,
              'chi_b': chi_b}

    if baseline:
        utils.mkdirs(os.path.join(baseline_dir, "SSinit"))
        ss_init_dir = os.path.join(baseline_dir, "SSinit/ss_init_vars.pkl")
        pickle.dump(output, open(ss_init_dir, "wb"))
    else:
        utils.mkdirs(os.path.join(output_dir, "SSinit"))
        ss_init_dir = os.path.join(output_dir, "SSinit/ss_init_vars.pkl")
        pickle.dump(output, open(ss_init_dir, "wb"))
    
    bssmat_init = bssmat_splus1
    nssmat_init = nssmat

    # Pickle variables for TPI initial values
    output2 = {'bssmat_init': bssmat_init, 'nssmat_init': nssmat_init}
    ss_init_tpi = os.path.join(output_dir, "SSinit/ss_init_tpi_vars.pkl")
    pickle.dump(output2, open(ss_init_tpi, "wb"))

    return output
