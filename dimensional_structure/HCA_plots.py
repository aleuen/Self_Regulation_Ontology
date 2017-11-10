# imports
import argparse
from utils import abs_pdist, save_figure, set_seed, plot_loadings
from itertools import combinations
from math import ceil
import matplotlib.pyplot as plt
from matplotlib import patches
import numpy as np
from os import makedirs, path
import pandas as pd
import seaborn as sns
from scipy.cluster.hierarchy import dendrogram
from scipy.spatial.distance import pdist, squareform
from selfregulation.utils.plot_utils import dendroheatmap
from sklearn.manifold import MDS
from sklearn.metrics import adjusted_mutual_info_score, adjusted_rand_score
from sklearn.preprocessing import MinMaxScaler, scale

import subprocess

# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('-rerun', action='store_true')
parser.add_argument('-no_plot', action='store_true')
args = parser.parse_args()

rerun = args.rerun
plot_on = not args.no_plot


def plot_clusterings(HCA, plot_dir=None, verbose=False):    
    # get all clustering solutions
    clusterings = [(k ,v) for k,v in 
                    HCA.results.items() if 'clustering' in k]
    
    # plot dendrogram heatmaps
    for name, clustering in clusterings:
        title = name.split('-')[1] + '_metric-' + HCA.dist_metric
        filename = None
        if plot_dir is not None:
            filename = path.join(plot_dir, '%s.png' % name)
        fig = dendroheatmap(clustering['linkage'], clustering['distance_df'], 
                            clustering['labels'],
                            figsize=(50,50), title=title,
                            filename = filename)
    
    
    
def plot_clustering_similarity(HCA, plot_dir=None, verbose=False):   
    # get all clustering solutions
    clusterings = [(k ,v) for k,v in 
                    HCA.results.items() if 'clustering' in k]
    # plot cluster agreement across embedding spaces
    names = [k.split('-')[-1] for k,v in 
                    HCA.results.items() if 'clustering' in k]
    cluster_similarity = np.zeros((len(clusterings), len(clusterings)))
    cluster_similarity = pd.DataFrame(cluster_similarity, 
                                     index=names,
                                     columns=names)
    
    distance_similarity = np.zeros((len(clusterings), len(clusterings)))
    distance_similarity = pd.DataFrame(distance_similarity, 
                                     index=names,
                                     columns=names)
    for clustering1, clustering2 in combinations(clusterings, 2):
        name1 = clustering1[0].split('-')[-1]
        name2 = clustering2[0].split('-')[-1]
        # record similarity of distance_df
        dist_corr = np.corrcoef(squareform(clustering1[1]['distance_df']),
                                squareform(clustering2[1]['distance_df']))[1,0]
        distance_similarity.loc[name1, name2] = dist_corr
        distance_similarity.loc[name2, name1] = dist_corr
        # record similarity of clustering of dendrogram
        clusters1 = clustering1[1]['labels']
        clusters2 = clustering2[1]['labels']
        rand_score = adjusted_rand_score(clusters1, clusters2)
        MI_score = adjusted_mutual_info_score(clusters1, clusters2)
        cluster_similarity.loc[name1, name2] = rand_score
        cluster_similarity.loc[name2, name1] = MI_score
    
    with sns.plotting_context(context='notebook', font_scale=1.4):
        clust_fig = plt.figure(figsize = (12,12))
        sns.heatmap(cluster_similarity, square=True)
        plt.title('Cluster Similarity: TRIL: Adjusted MI, TRIU: Adjusted Rand',
                  y=1.02)
        
        dist_fig = plt.figure(figsize = (12,12))
        sns.heatmap(distance_similarity, square=True)
        plt.title('Distance Similarity, metric: %s' % HCA.dist_metric,
                  y=1.02)
        
    if plot_dir is not None:
        save_figure(clust_fig, path.join(plot_dir, 
                                   'cluster_similarity_across_measures.png'),
                    {'bbox_inches': 'tight'})
        save_figure(dist_fig, path.join(plot_dir, 
                                   'distance_similarity_across_measures.png'),
                    {'bbox_inches': 'tight'})
    
    if verbose:
        # assess relationship between two measurements
        rand_scores = cluster_similarity.values[np.triu_indices_from(cluster_similarity, k=1)]
        MI_scores = cluster_similarity.T.values[np.triu_indices_from(cluster_similarity, k=1)]
        score_consistency = np.corrcoef(rand_scores, MI_scores)[0,1]
        print('Correlation between measures of cluster consistency: %.2f' \
              % score_consistency)
        
    
    
def plot_dendrograms(HCA, label_top_percent=.2, 
                     centrality_thresh=.1, plot_dir=None):
    # get all clustering solutions
    clusterings = [(k ,v) for k,v in 
                    HCA.results.items() if 'clustering' in k]

        
    for name, clustering in clusterings:
        title = name.split('-')[1] + '_metric-' + HCA.dist_metric
        # extract cluster vars
        link = clustering['linkage']
        distance_df = clustering['distance_df']
        # check if graphs exist
        if 'graphs' in clustering.keys() and len(distance_df)>120:
            graph_vars = HCA.get_graph_vars(clustering['graphs'])
            # extract variables that are in the top_n most central for each cluster
            label_vars = []
            for i in graph_vars:
                top_n = ceil(len(i)*label_top_percent)
                top_n = i[-(top_n+1):-1]
                label_vars += [v[0] for v in top_n if v[1]>centrality_thresh]
            labels = [i if i in label_vars else '' for i in distance_df.columns]
        else:
            labels = distance_df.columns
        # get cluster sizes
        cluster_labels = HCA.get_cluster_labels(inp=name.split('-')[1])
        cluster_sizes = [len(i) for i in cluster_labels]
        # plot dendrogram
        color_palette = [[.4,.4, .4], [.8,.8,.8]]
        with sns.axes_style('white'):
            fig = plt.figure(figsize=(34,14))
            ax1 = fig.add_axes([0,.4,1,.55]) 
            dendrogram(link, labels=labels, color_threshold=-1,
                       above_threshold_color='black', ax=ax1)
            # change axis properties
            ax1.tick_params(axis='x', which='major', labelsize=14)
            # add background color to distinguish clusters
            ax2 = fig.add_axes([0,0,1,1]) 
            ax2.patch.set_alpha(0)
            xlim = ax2.get_xlim(); step = xlim[1]/len(distance_df)
            ymin, ymax = ax1.get_ylim()
            begin = 0
            for i, size in enumerate(cluster_sizes):
                patch = patches.Rectangle((begin, .4), size*step, ymax,
                                          color=color_palette[i%2],
                                          alpha=.3)
                ax2.add_patch(patch)
                begin+=size*step
            # add title
            plt.title(title, fontsize=40, y=1.05)
            # invert axes
            ax2.get_xaxis().set_visible(False)
            for ax in [ax1, ax2]:
                ax.get_yaxis().set_visible(False)
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['bottom'].set_visible(False)
                ax.spines['left'].set_visible(False)
                ax.invert_xaxis()
        if plot_dir is not None:
            save_figure(fig, path.join(plot_dir, 
                                             '%s_dendrogram.png' % name),
                        {'bbox_inches': 'tight'})
        
def plot_graphs(HCA_graphs, plot_dir=None):
    if plot_dir is not None:
        makedirs(path.join(plot_dir, 'graphs'))
    plot_options = {'inline': False,  'target': None}
    for i, GA in enumerate(HCA_graphs):
        if plot_dir is not None:
            plot_options['target'] = path.join(plot_dir, 
                                                'graphs', 
                                                'graph%s.png' % i)
        GA.set_visual_style()
        GA.display(plot_options)
    
    
    
@set_seed(seed=15)
def MDS_visualization(results, c, plot_dir=None, 
                      dist_metric='abs_correlation', **plot_kws):
    """ visualize EFA loadings and compares to raw space """
    def scale_plot(input_data, data_colors=None, cluster_colors=None,
                   cluster_sizes=None, dissimilarity='euclidean', filey=None):
        """ Plot MDS of data and clusters """
        if data_colors is None:
            data_colors = 'r'
        if cluster_colors is None:
            cluster_colors='b'
        if cluster_sizes is None:
            cluster_sizes = 2200
            
        # scale
        mds = MDS(dissimilarity=dissimilarity)
        mds_out = mds.fit_transform(input_data)
        
        with sns.axes_style('white'):
            f=plt.figure(figsize=(14,14))
            plt.scatter(mds_out[n_clusters:,0], mds_out[n_clusters:,1], 
                        s=75, color=data_colors)
            plt.scatter(mds_out[:n_clusters,0], mds_out[:n_clusters,1], 
                        marker='*', s=cluster_sizes, color=cluster_colors,
                        edgecolor='black', linewidth=2)
            # plot cluster number
            offset = .011
            font_dict = {'fontsize': 17, 'color':'white'}
            for i,(x,y) in enumerate(mds_out[:n_clusters]):
                if i<9:
                    plt.text(x-offset,y-offset,i+1, font_dict)
                else:
                    plt.text(x-offset*2,y-offset,i+1, font_dict)
            plt.title(path.basename(filey)[:-4], fontsize=20)
        if filey is not None:
            save_figure(f, filey)
            
    # set up variables
    data = results.data
    HCA = results.HCA
    EFA = results.EFA
    
    cluster_loadings = HCA.get_cluster_loading(EFA, 'data', c)
    cluster_loadings_mat = np.vstack([i[1] for i in cluster_loadings])
    EFA_loading = abs(EFA.get_loading(c))
    EFA_loading_mat = EFA_loading.values
    EFA_space = np.vstack([cluster_loadings_mat, EFA_loading_mat])
    
    # set up colors
    n_clusters = cluster_loadings_mat.shape[0]
    color_palette = sns.color_palette(palette='hls', n_colors=n_clusters)
    colors = []
    for var in EFA_loading.index:
        # find which cluster this variable is in
        index = [i for i,cluster in enumerate(cluster_loadings) \
                 if var in cluster[0]][0]
        colors.append(color_palette[index])
    # set up cluster sizes proportional to number of members
    n_members = np.reshape([len(i) for i,j in cluster_loadings], [-1,1])
    scaler = MinMaxScaler()
    relative_members = scaler.fit_transform(n_members).flatten()
    sizes = 1500+2000*relative_members
    
    if dist_metric == 'abs_correlation':
        EFA_space_distances = squareform(abs_pdist(EFA_space))
    else: 
        EFA_space_distances = squareform(pdist(EFA_space, dist_metric))
    
    # repeat the same thing as above but with raw distances
    scaled_data = pd.DataFrame(scale(data).T,
                               index=data.columns,
                               columns=data.index)
    clusters_raw = []
    for labels, EFA_vec in cluster_loadings:
        subset = scaled_data.loc[labels,:]
        cluster_vec = subset.mean(0)
        clusters_raw.append(cluster_vec)
    raw_space = np.vstack([clusters_raw, scaled_data])
    # turn raw space into distances
    if dist_metric == 'abs_correlation':
        raw_space_distances = squareform(abs_pdist(raw_space))
    else:
        raw_space_distances = squareform(pdist(raw_space, dist_metric))
    
    # plot distances
    distances = {'EFA%s' % c: EFA_space_distances,
                 'subj': raw_space_distances}
    filey=None
    for label, space in distances.items():
        if plot_dir is not None:
            filey = path.join(plot_dir, 
                              'MDS_%s_metric-%s.png' % (label, dist_metric))
        scale_plot(space, data_colors=colors,
                   cluster_colors=color_palette,
                   cluster_sizes=sizes,
                   dissimilarity='precomputed',
                   filey=filey)

def visualize_importance(importance, ax, xticklabels=True, 
                           yticklabels=True, pad=0, ymax=None, legend=True):
    """Plot task loadings on one axis"""
    importance_vars = importance[0]
    importance_vals = [abs(i)+pad for i in importance[1].T]
    plot_loadings(ax, importance_vals, kind='line', offset=.5,
                  plot_kws={'alpha': 1})
    # set up x ticks
    xtick_locs = np.arange(0.0, 2*np.pi, 2*np.pi/len(importance_vars))
    ax.set_xticks(xtick_locs)
    ax.set_xticks(xtick_locs+np.pi/len(importance_vars), minor=True)
    if xticklabels:
        if type(importance_vars[0]) == str:
            ax.set_xticklabels(importance_vars, 
                               y=.08, minor=True)
        else:
            ax.set_xticklabels(['Fac %s' % str(i+1) for i in importance_vars], 
                               y=.08, minor=True)
    # set up yticks
    if ymax:
        ax.set_ylim(top=ymax)
    ytick_locs = ax.yaxis.get_ticklocs()
    new_yticks = np.linspace(0, ytick_locs[-1], 7)
    ax.set_yticks(new_yticks)
    if yticklabels:
        labels = np.round(new_yticks,2)
        replace_dict = {i:'' for i in labels[::2]}
        labels = [replace_dict.get(i, i) for i in labels]
        ax.set_yticklabels(labels)
    if legend:
        ax.legend(loc='upper center', bbox_to_anchor=(.5,-.15))
        
def plot_cluster_factors(results, c,  plot_dir=None):
    """
    Args:
        EFA: EFA_Analysis object
        c: number of components for EFA
        task_sublists: a dictionary whose values are sets of tasks, and 
                        whose keywords are labels for those lists
    """
    # set up variables
    HCA = results.HCA
    EFA = results.EFA
    
    cluster_loadings = HCA.get_cluster_loading(EFA, 'data', c)
    max_loading = max([max(abs(i[1])) for i in cluster_loadings])
    # plot
    ncols = min(6, len(cluster_loadings))
    nrows = ceil(len(cluster_loadings)/ncols)
    f, axes = plt.subplots(nrows, ncols, 
                               figsize=(ncols*10,nrows*(8+nrows)),
                               subplot_kw={'projection': 'polar'})
    axes = f.get_axes()
    for i, (measures, loading) in enumerate(cluster_loadings):
        if i%(ncols*2)==0 or i%(ncols*2)==5:
            plot_loadings(axes[i], loading, kind='line', offset=.5,
                  plot_kws={'alpha': .8})
        else:
            plot_loadings(axes[i], loading, kind='line', offset=.5,
                  plot_kws={'alpha': .8})
        axes[i].set_title('Cluster %s' % i, y=1.14, fontsize=25)
        if i%(ncols*2)==0 or i%(ncols*2)==5:
            # set tick labels
            xtick_locs = np.arange(0.0, 2*np.pi, 2*np.pi/len(loading))
            axes[i].set_xticks(xtick_locs)
            axes[i].set_xticks(xtick_locs+np.pi/len(loading), minor=True)
            axes[i].set_xticklabels(loading.index,  y=.08, minor=True)
            # set ylim
            axes[i].set_ylim(top=max_loading)
    for j in range(i+1, len(axes)):
        axes[j].set_visible(False)
    plt.subplots_adjust(hspace=.5, wspace=.5)
    
    filename = 'clustering_polar_factors_EFA%s.png' % c
    if plot_dir is not None:
        save_figure(f, path.join(plot_dir, filename),
                    {'bbox_inches': 'tight'})
        
            
def plot_HCA(results, plot_dir=None,verbose=False):
    HCA = results.HCA
    c = results.EFA.get_metric_cs()['c_metric-BIC']
    # plots, woo
    if verbose: print("Plotting dendrogram heatmaps")
    plot_clusterings(HCA, plot_dir=plot_dir, verbose=verbose)
    if verbose: print("Plotting dendrograms")
    plot_dendrograms(HCA, plot_dir=plot_dir)
    if verbose: print("Plotting clustering similarity")
    plot_clustering_similarity(HCA, plot_dir=plot_dir, verbose=verbose)
    if verbose: print("Plotting cluster polar plots")
    plot_cluster_factors(results, c, plot_dir=plot_dir)
    if verbose: print("Plotting MDS space")
    for metric in ['abs_correlation']:
        MDS_visualization(results, c, plot_dir=plot_dir,
                          dist_metric=metric)


"""      
    # plot distance correlation for factor solutions in the same order as the
    # clustered solution
    clustered_df = results['HCA']['clustering_metric-distcorr_input-data']['clustered_df']
    cluster_order = clustered_df.index
    
    fig = plt.figure(figsize=(12,12))
    sns.heatmap(clustered_df, square=True, xticklabels=False,
                yticklabels=False, cbar=False)
    plt.title('Data', fontsize=20, y=1.02)
    fig.savefig(path.join(plot_file,  'heatmap_metric-distcorr.png'), 
                bbox_inches='tight')
    factor_distances = {}
    for c, loadings in results['EFA']['factor_tree'].items():
        if c>2:
            loadings = loadings.copy().loc[cluster_order, :]
            distances = squareform(pdist(loadings, metric=distcorr))
            distances = pd.DataFrame(distances, 
                                     index=loadings.index, 
                                     columns=loadings.index)
            factor_distances[c] = squareform(distances)
            # plot
            fig = plt.figure(figsize=(12,12))
            sns.heatmap(distances, square=True, xticklabels=False,
                yticklabels=False, cbar=False)
            plt.title('EFA %s' % c, fontsize=20, y=1.02)
            fig.savefig(path.join(plot_file,
                                  'heatmap_metric-distcorr_c-%02d.png' % c), 
                        bbox_inches='tight')
    factor_distances = pd.DataFrame(factor_distances)
    factor_distances.loc[:, 'raw'] = squareform(clustered_df)
    # create gif from files
    cmd = 'convert -delay 80 -loop 1 %s %s' % (path.join(plot_file, 'heatmap*'),
                                                path.join(plot_file, 'EFA_heatmaps.gif'))
    subprocess.call(cmd, shell=True)
    # delete still files
    for filey in glob(path.join(plot_file, 'heatmap*')):
        remove(filey)
    
    # repeat factor analysis above using PCA
    scaled_data = scale(data.loc[:, cluster_order]).T
    pca_distances = {}
    for c in results['EFA']['factor_tree'].keys():
        if c>2:
            pca = PCA(c)
            pca_out = pca.fit_transform(scaled_data)
            distances = pdist(pca_out, metric=distcorr)
            pca_distances[c] = distances
    pca_distances = pd.DataFrame(pca_distances)
    pca_distances.loc[:, 'raw'] = squareform(clustered_df)
    
    # plot correlations between distance matrices
    with sns.plotting_context('notebook', font_scale=1.8):
        f = plt.figure(figsize=(12,8))
        pca_distances.corr()['raw'][:-1].plot(label = 'PCA')
        factor_distances.corr()['raw'][:-1].plot(label = 'EFA')
        plt.xlabel('Components in Decomposition')
        plt.ylabel('Correlation with Raw Values')
        plt.title('Distance Matrix Correlations')
        plt.legend()
        f.savefig(path.join(plot_file, 
                            'distance_correlations_across_components_metric-distcorr.png'))
    
"""    
    
    
    













