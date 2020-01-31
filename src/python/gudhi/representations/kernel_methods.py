# This file is part of the Gudhi Library - https://gudhi.inria.fr/ - which is released under MIT.
# See file LICENSE or go to https://gudhi.inria.fr/licensing/ for full license details.
# Author(s):       Mathieu Carrière
#
# Copyright (C) 2018-2019 Inria
#
# Modification(s):
#   - YYYY/MM Author: Description of the modification

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import pairwise_distances, pairwise_kernels
from .metrics import SlicedWassersteinDistance, PersistenceFisherDistance, sklearn_wrapper, pairwise_persistence_diagram_distances, sliced_wasserstein_distance, persistence_fisher_distance
from .preprocessing import Padding

#############################################
# Kernel methods ############################
#############################################

def persistence_weighted_gaussian_kernel(D1, D2, weight=lambda x: 1, kernel_approx=None, bandwidth=1.):
    """
    This is a function for computing the persistence weighted Gaussian kernel value from two persistence diagrams. The persistence weighted Gaussian kernel is computed by convolving the persistence diagram points with weighted Gaussian kernels. See http://proceedings.mlr.press/v48/kusano16.html for more details.
    :param D1: (n x 2) numpy.array encoding the (finite points of the) first diagram. Must not contain essential points (i.e. with infinite coordinate).
    :param D2: (m x 2) numpy.array encoding the second diagram.
    :param bandwidth: bandwidth of the Gaussian kernel with which persistence diagrams will be convolved
    :param weight: weight function for the persistence diagram points. This function must be defined on 2D points, ie lists or numpy arrays of the form [p_x,p_y].
    :param kernel_approx: kernel approximation class used to speed up computation. Common kernel approximations classes can be found in the scikit-learn library (such as RBFSampler for instance).
    :returns: the persistence weighted Gaussian kernel value between persistence diagrams.
    :rtype: float 
    """
    ws1 = np.array([weight(D1[j,:]) for j in range(len(D1))])
    ws2 = np.array([weight(D2[j,:]) for j in range(len(D2))])
    if kernel_approx is not None:
        approx1 = np.sum(np.multiply(ws1[:,np.newaxis], kernel_approx.transform(D1)), axis=0)
        approx2 = np.sum(np.multiply(ws2[:,np.newaxis], kernel_approx.transform(D2)), axis=0)
        return (1./(np.sqrt(2*np.pi)*bandwidth)) * np.matmul(approx1, approx2.T)
    else:
        W = np.matmul(ws1[:,np.newaxis], ws2[np.newaxis,:])
        E = (1./(np.sqrt(2*np.pi)*bandwidth)) * np.exp(-np.square(pairwise_distances(D1,D2))/(2*bandwidth*bandwidth))
        return np.sum(np.multiply(W, E))

def persistence_scale_space_kernel(D1, D2, kernel_approx=None, bandwidth=1.):
    """
    This is a function for computing the persistence scale space kernel value from two persistence diagrams. The persistence scale space kernel is computed by adding the symmetric to the diagonal of each point in each persistence diagram, with negative weight, and then convolving the points with a Gaussian kernel. See https://www.cv-foundation.org/openaccess/content_cvpr_2015/papers/Reininghaus_A_Stable_Multi-Scale_2015_CVPR_paper.pdf for more details.
    :param D1: (n x 2) numpy.array encoding the (finite points of the) first diagram. Must not contain essential points (i.e. with infinite coordinate).
    :param D2: (m x 2) numpy.array encoding the second diagram.
    :param bandwidth: bandwidth of the Gaussian kernel with which persistence diagrams will be convolved
    :param kernel_approx: kernel approximation class used to speed up computation. Common kernel approximations classes can be found in the scikit-learn library (such as RBFSampler for instance).
    :returns: the persistence scale space kernel value between persistence diagrams.
    :rtype: float 
    """
    DD1 = np.concatenate([D1, D1[:,[1,0]]], axis=0)
    DD2 = np.concatenate([D2, D2[:,[1,0]]], axis=0)
    weight_pss = lambda x: 1 if x[1] >= x[0] else -1
    return 0.5 * persistence_weighted_gaussian_kernel(DD1, DD2, weight=weight_pss, kernel_approx=kernel_approx, bandwidth=bandwidth)

def pairwise_persistence_diagram_kernels(X, Y=None, metric="sliced_wasserstein", **kwargs):
    """
    This function computes the kernel matrix between two lists of persistence diagrams given as numpy arrays of shape (nx2).
    :param X: first list of persistence diagrams. 
    :param Y: second list of persistence diagrams (optional). If None, pairwise kernel values are computed from the first list only.
    :param metric: kernel to use. It can be either a string ("sliced_wasserstein", "persistence_scale_space", "persistence_weighted_gaussian", "persistence_fisher") or a function taking two numpy arrays of shape (nx2) and (mx2) as inputs.
    :returns: kernel matrix, i.e., numpy array of shape (num diagrams 1 x num diagrams 2)
    :rtype: float
    """
    if Y is None:
        YY = None
        pX = Padding(use=True).fit_transform(X)
        diag_len = len(pX[0])
        XX = np.reshape(np.vstack(pX), [-1, diag_len*3])
    else:
        nX, nY = len(X), len(Y)
        pD = Padding(use=True).fit_transform(X + Y)
        diag_len = len(pD[0])
        XX = np.reshape(np.vstack(pD[:nX]), [-1, diag_len*3])
        YY = np.reshape(np.vstack(pD[nX:]), [-1, diag_len*3])

    if metric == "sliced_wasserstein":
        return np.exp(-pairwise_persistence_diagram_distances(X, Y, metric="sliced_wasserstein", num_directions=kwargs["num_directions"]) / kwargs["bandwidth"])
    elif metric == "persistence_fisher":
        return np.exp(-pairwise_persistence_diagram_distances(X, Y, metric="persistence_fisher", kernel_approx=kwargs["kernel_approx"], bandwidth=kwargs["bandwidth"]) / kwargs["bandwidth_fisher"])
    elif metric == "persistence_scale_space":
        return pairwise_kernels(XX, YY, metric=sklearn_wrapper(persistence_scale_space_kernel, **kwargs))
    elif metric == "persistence_weighted_gaussian":
        return pairwise_kernels(XX, YY, metric=sklearn_wrapper(persistence_weighted_gaussian_kernel, **kwargs))
    else:
        return pairwise_kernels(XX, YY, metric=sklearn_wrapper(metric, **kwargs))

class SlicedWassersteinKernel(BaseEstimator, TransformerMixin):
    """
    This is a class for computing the sliced Wasserstein kernel matrix from a list of persistence diagrams. The sliced Wasserstein kernel is computed by exponentiating the corresponding sliced Wasserstein distance with a Gaussian kernel. See http://proceedings.mlr.press/v70/carriere17a.html for more details. 
    """
    def __init__(self, num_directions=10, bandwidth=1.0):
        """
        Constructor for the SlicedWassersteinKernel class.

        Parameters:
            bandwidth (double): bandwidth of the Gaussian kernel applied to the sliced Wasserstein distance (default 1.).
            num_directions (int): number of lines evenly sampled from [-pi/2,pi/2] in order to approximate and speed up the kernel computation (default 10).
        """
        self.bandwidth = bandwidth
        self.num_directions = num_directions

    def fit(self, X, y=None):
        """
        Fit the SlicedWassersteinKernel class on a list of persistence diagrams: an instance of the SlicedWassersteinDistance class is fitted on the diagrams and then stored. 

        Parameters:
            X (list of n x 2 numpy arrays): input persistence diagrams.
            y (n x 1 array): persistence diagram labels (unused).
        """
        self.diagrams_ = X
        return self

    def transform(self, X):
        """
        Compute all sliced Wasserstein kernel values between the persistence diagrams that were stored after calling the fit() method, and a given list of (possibly different) persistence diagrams.

        Parameters:
            X (list of n x 2 numpy arrays): input persistence diagrams.

        Returns:
            numpy array of shape (number of diagrams in **diagrams**) x (number of diagrams in X): matrix of pairwise sliced Wasserstein kernel values.
        """
        return pairwise_persistence_diagram_kernels(X, self.diagrams_, metric="sliced_wasserstein", bandwidth=self.bandwidth, num_directions=self.num_directions) 

class PersistenceWeightedGaussianKernel(BaseEstimator, TransformerMixin):
    """
    This is a class for computing the persistence weighted Gaussian kernel matrix from a list of persistence diagrams. The persistence weighted Gaussian kernel is computed by convolving the persistence diagram points with weighted Gaussian kernels. See http://proceedings.mlr.press/v48/kusano16.html for more details. 
    """
    def __init__(self, bandwidth=1., weight=lambda x: 1, kernel_approx=None):
        """
        Constructor for the PersistenceWeightedGaussianKernel class.
  
        Parameters:
            bandwidth (double): bandwidth of the Gaussian kernel with which persistence diagrams will be convolved (default 1.)
            weight (function): weight function for the persistence diagram points (default constant function, ie lambda x: 1). This function must be defined on 2D points, ie lists or numpy arrays of the form [p_x,p_y].
            kernel_approx (class): kernel approximation class used to speed up computation (default None). Common kernel approximations classes can be found in the scikit-learn library (such as RBFSampler for instance).
        """
        self.bandwidth, self.weight = bandwidth, weight
        self.kernel_approx = kernel_approx

    def fit(self, X, y=None):
        """
        Fit the PersistenceWeightedGaussianKernel class on a list of persistence diagrams: persistence diagrams are stored in a numpy array called **diagrams** and the kernel approximation class (if not None) is applied on them. 

        Parameters:
            X (list of n x 2 numpy arrays): input persistence diagrams.
            y (n x 1 array): persistence diagram labels (unused).
        """
        self.diagrams_ = X
        return self

    def transform(self, X):
        """
        Compute all persistence weighted Gaussian kernel values between the persistence diagrams that were stored after calling the fit() method, and a given list of (possibly different) persistence diagrams.

        Parameters:
            X (list of n x 2 numpy arrays): input persistence diagrams.

        Returns:
            numpy array of shape (number of diagrams in **diagrams**) x (number of diagrams in X): matrix of pairwise persistence weighted Gaussian kernel values.
        """
        return pairwise_persistence_diagram_kernels(X, self.diagrams_, metric="persistence_weighted_gaussian", bandwidth=self.bandwidth, weight=self.weight, kernel_approx=self.kernel_approx) 

class PersistenceScaleSpaceKernel(BaseEstimator, TransformerMixin):
    """
    This is a class for computing the persistence scale space kernel matrix from a list of persistence diagrams. The persistence scale space kernel is computed by adding the symmetric to the diagonal of each point in each persistence diagram, with negative weight, and then convolving the points with a Gaussian kernel. See https://www.cv-foundation.org/openaccess/content_cvpr_2015/papers/Reininghaus_A_Stable_Multi-Scale_2015_CVPR_paper.pdf for more details. 
    """
    def __init__(self, bandwidth=1., kernel_approx=None):
        """
        Constructor for the PersistenceScaleSpaceKernel class.
  
        Parameters:
            bandwidth (double): bandwidth of the Gaussian kernel with which persistence diagrams will be convolved (default 1.)
            kernel_approx (class): kernel approximation class used to speed up computation (default None). Common kernel approximations classes can be found in the scikit-learn library (such as RBFSampler for instance).
        """
        self.bandwidth, self.kernel_approx = bandwidth, kernel_approx

    def fit(self, X, y=None):
        """
        Fit the PersistenceScaleSpaceKernel class on a list of persistence diagrams: symmetric to the diagonal of all points are computed and an instance of the PersistenceWeightedGaussianKernel class is fitted on the diagrams and then stored. 

        Parameters:
            X (list of n x 2 numpy arrays): input persistence diagrams.
            y (n x 1 array): persistence diagram labels (unused).
        """
        self.diagrams_ = X
        return self

    def transform(self, X):
        """
        Compute all persistence scale space kernel values between the persistence diagrams that were stored after calling the fit() method, and a given list of (possibly different) persistence diagrams.

        Parameters:
            X (list of n x 2 numpy arrays): input persistence diagrams.

        Returns:
            numpy array of shape (number of diagrams in **diagrams**) x (number of diagrams in X): matrix of pairwise persistence scale space kernel values.
        """
        return pairwise_persistence_diagram_kernels(X, self.diagrams_, metric="persistence_scale_space", bandwidth=self.bandwidth, kernel_approx=self.kernel_approx)

class PersistenceFisherKernel(BaseEstimator, TransformerMixin):
    """
    This is a class for computing the persistence Fisher kernel matrix from a list of persistence diagrams. The persistence Fisher kernel is computed by exponentiating the corresponding persistence Fisher distance with a Gaussian kernel. See papers.nips.cc/paper/8205-persistence-fisher-kernel-a-riemannian-manifold-kernel-for-persistence-diagrams for more details. 
    """
    def __init__(self, bandwidth_fisher=1., bandwidth=1., kernel_approx=None):
        """
        Constructor for the PersistenceFisherKernel class.

        Parameters:
            bandwidth (double): bandwidth of the Gaussian kernel applied to the persistence Fisher distance (default 1.).
            bandwidth_fisher (double): bandwidth of the Gaussian kernel used to turn persistence diagrams into probability distributions by PersistenceFisherDistance class (default 1.).
            kernel_approx (class): kernel approximation class used to speed up computation (default None). Common kernel approximations classes can be found in the scikit-learn library (such as RBFSampler for instance).
        """
        self.bandwidth = bandwidth
        self.bandwidth_fisher, self.kernel_approx = bandwidth_fisher, kernel_approx

    def fit(self, X, y=None):
        """
        Fit the PersistenceFisherKernel class on a list of persistence diagrams: an instance of the PersistenceFisherDistance class is fitted on the diagrams and then stored. 

        Parameters:
            X (list of n x 2 numpy arrays): input persistence diagrams.
            y (n x 1 array): persistence diagram labels (unused).
        """
        self.diagrams_ = X
        return self

    def transform(self, X):
        """
        Compute all persistence Fisher kernel values between the persistence diagrams that were stored after calling the fit() method, and a given list of (possibly different) persistence diagrams.

        Parameters:
            X (list of n x 2 numpy arrays): input persistence diagrams.

        Returns:
            numpy array of shape (number of diagrams in **diagrams**) x (number of diagrams in X): matrix of pairwise persistence Fisher kernel values.
        """
        return pairwise_persistence_diagram_kernels(X, self.diagrams_, metric="persistence_fisher", bandwidth=self.bandwidth, bandwidth_fisher=self.bandwidth_fisher, kernel_approx=self.kernel_approx)

