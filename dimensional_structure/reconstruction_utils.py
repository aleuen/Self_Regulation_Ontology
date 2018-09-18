import numpy as np
import pandas as pd
from sklearn.linear_model import RANSACRegressor
from selfregulation.utils.r_to_py_utils import psychFA

# utils for deriving and evaluating ontological factors for out-of-model tasks
def linear_ontology_reconstruction(results, var, pseudo_pop_size=60,
                              n_reps=100, clf=None, robust=False, verbose=True):
    def get_coefs(clf):
        try:
            return clf.coef_
        except AttributeError:
            return clf.estimator_.coef_
    if verbose: 
        print('Starting Linear reconstruction, var', var)
        print('*'*79)
    data = results.data
    c = results.EFA.results['num_factors']
    full_scores = results.EFA.get_scores(c)
    loadings = results.EFA.get_loading(c)
    # refit an EFA model without variable    
    subset = data.drop(var, axis=1)
    fa, out = psychFA(subset, c)
    scores = pd.DataFrame(out['scores'], 
                          columns=full_scores.columns,
                          index=full_scores.index)
    
    orig_estimate = loadings.loc[var]
    if clf is None:
        clf = LinearRegression(fit_intercept=False)
    if robust:
        clf = RANSACRegressor(base_estimator=clf)
    if verbose: print('Starting full reconstruction')
    clf.fit(scores, data.loc[:, var])
    full_reconstruction = pd.Series(get_coefs(clf), index=orig_estimate.index)
    estimated_loadings = []
    if verbose: print('Starting partial reconstruction, pop size:', pseudo_pop_size)
    for rep in range(n_reps):
        if verbose and rep%100==0: 
            print('Rep', rep)
        random_subset = np.random.choice(scores.index,
                                         pseudo_pop_size, 
                                         replace=False)
        X = scores.loc[random_subset]
        y = data.loc[random_subset, var]
        clf.fit(X,y)
        estimated_loadings.append(get_coefs(clf))
    estimated_loadings = pd.DataFrame(estimated_loadings, columns=orig_estimate.index).T
    # calculate average distance from coefficient estimat eacross runs
    return orig_estimate, estimated_loadings, full_reconstruction

def k_nearest_ontology_reconstruction(results, drop_regex, reconstruct_vars=None,
                                      pseudo_pop_size=60, n_reps=100, k_list=None, verbose=True):
    def get_k_blend(distances, ref_loadings, k, weighted=True):
        """ Take a set of distances and reference loadings and return a reconstructed loading
        Args:
            distances: pandas Series of distances from the to-be-reconstructed variable in descending order
            ref_loading: the lookup loading matrix to index with the closest variables taken from distances
            k_list: list of k_values to use

        """
        closest = distances[1:k+1]
        closest /= closest.sum() # normalize
        if weighted:
            reconstruction = loadings.loc[closest.index].multiply(closest,axis=0).sum(0)
            reconstruction['weighted'] = True
        else:
            reconstruction = loadings.loc[closest.index].mean(0)
            reconstruction['weighted'] = False
        return reconstruction
    if k_list is None:
        k_list = [3]
    data = results.data
    c = results.EFA.results['num_factors']
    orig_loadings = results.EFA.get_loading(c)
    # refit an EFA model without variable    
    drop_vars = list(data.filter(regex=drop_regex).columns)
    subset = data.drop(drop_vars, axis=1)
    fa, out = psychFA(subset, c)
    loadings = pd.DataFrame(out['loadings'], index=subset.columns, columns=orig_loadings.columns)
    if reconstruct_vars is None:
        reconstruct_vars = drop_vars
    if verbose: 
        print('Starting K Nearest reconstruction, measures:', reconstruct_vars)
        print('*'*79)
    orig_estimates = orig_loadings.loc[reconstruct_vars].T
    orig_estimates.loc['var',:] = reconstruct_vars

    # full reconstruction
    if verbose: print('Starting full reconstruction')
    full_reconstruction = []
    for var in drop_vars:
        distances = data.corr().loc[var].sort_values(ascending=False).drop(drop_vars)
        for k in k_list:
            for weighted in [True, False]:
                reconstruction = get_k_blend(distances, loadings, k, weighted)
                reconstruction['k'] = k
                reconstruction['var'] = var
                full_reconstruction.append(reconstruction)
    full_reconstruction = pd.concat(full_reconstruction, axis=1)

    if verbose: print('Starting partial reconstruction, pop size:', pseudo_pop_size)
    estimated_loadings = []
    for rep in range(n_reps):
        if verbose and rep%100==0: 
            print('Rep', rep)
        random_subset = np.random.choice(data.index,
                                         pseudo_pop_size, 
                                         replace=False)
        for var in drop_vars:
            distances = data.loc[random_subset].corr().loc[var].sort_values(ascending=False).drop(drop_vars)
            for k in k_list:
                for weighted in [True, False]:
                    reconstruction = get_k_blend(distances, loadings, k, weighted)
                    reconstruction['sample'] = rep
                    reconstruction['k'] = k
                    reconstruction['var'] = var
                    estimated_loadings.append(reconstruction)
    estimated_loadings = pd.concat(estimated_loadings, axis=1)
    return orig_estimates, estimated_loadings, full_reconstruction


def organize_reconstruction(reconstruction_results):
    # organize the output from the simulations
    reconstruction_df = pd.DataFrame()
    for pop_size, out in reconstruction_results.items():
        for k, v in out.items():
            c = len(v[0])
            combined = pd.concat([v[0], v[2], v[1]], axis=1, sort=False).T
            combined.reset_index(drop=True, inplace=True)
            labels = ['true']
            if len(v[0].shape) == 2:
                labels += ['true']*(v[0].shape[1]-1)
            labels += ['full_reconstruct']
            if len(v[2].shape) == 2:
                labels += ['full_reconstruct']*(v[2].shape[1]-1)
            labels += ['partial_reconstruct']*v[1].shape[1]
            combined.loc[:, 'label'] = labels
            combined.loc[:, 'pop_size'] = pop_size
            reconstruction_df = pd.concat([reconstruction_df, combined])
    return reconstruction_df

def get_reconstruction_results(results, measure_list, pop_sizes=None, fun=None, **kwargs):
    if fun is None:
        fun = linear_ontology_reconstruction
    if pop_sizes is None:
        pop_sizes = [100, 200]
    reconstruction_results = {}
    # convert list of measures to a regex lookup
    for pop_size in pop_sizes:     
        out = {}
        for measure in measure_list:
            out[measure] = fun(results, drop_regex=measure, reconstruct_vars=None,
                               pseudo_pop_size=pop_size, **kwargs)
        reconstruction_results[pop_size] = out
    return organize_reconstruction(reconstruction_results)
    
