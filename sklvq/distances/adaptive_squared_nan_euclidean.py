from . import DistanceBaseClass

import numpy as np
from sklearn.metrics.pairwise import pairwise_distances

from functools import partial

from typing import TYPE_CHECKING
from typing import Dict

if TYPE_CHECKING:
    from sklvq.models import LVQClassifier


class AdaptiveSquaredNanEuclidean(DistanceBaseClass):
    def __init__(self, other_kwargs: Dict = None):
        self.metric_kwargs = {"force_all_finite": "allow-nan"}

        if other_kwargs is not None:
            self.metric_kwargs.update(other_kwargs)

    def __call__(self, data: np.ndarray, model: "LVQClassifier") -> np.ndarray:
        """ Implements a weighted variant of the squared euclidean distance:
            .. math::
                d^{\\Lambda}(w, x) = (x - w)^T \\Lambda (x - w)

        Parameters
        ----------
        data : ndarray
            A matrix containing the samples on the rows.
        model : LVQClassifier
            In principle any LVQClassifier that calls it's relevance matrix omega.
            Specifically here, GMLVQClassifier.

        Returns
        -------
        ndarray


            The adaptive squared euclidean distance for every sample to every prototype stored row-wise.
        """
        _adaptive_squared_nan_euclidean_callable = partial(
            _adaptive_squared_nan_euclidean,
            lambda_matrix=model.omega_.T.dot(model.omega_),
        )

        self.metric_kwargs.update({"metric": _adaptive_squared_nan_euclidean_callable})

        return pairwise_distances(data, model.prototypes_, **self.metric_kwargs) ** 2

    def gradient(
        self, data: np.ndarray, model: "LVQClassifier", i_prototype: int
    ) -> np.ndarray:
        """ The partial derivative of the adaptive squared euclidean distance function, with respect
        to a specified prototype and the matrix omega.

        Parameters
        ----------
        data : ndarray
            A matrix containing the samples on the rows.
        model : LVQClassifier
            In principle any LVQClassifier that calls it's relevance matrix omega.
            Specifically here, GMLVQClassifier.
        i_prototype : int
            An integer index value of the relevant prototype

        Returns
        -------
        ndarray
            The gradient for every feature/dimension. Returned in one 1D vector. The non-relevant prototype's
            gradient is set to 0, but is still included in the output.
        """
        (prototypes, omega) = model.get_model_params()
        (num_samples, num_features) = data.shape

        distance_gradient = np.zeros((num_samples, prototypes.size + omega.size))

        ip_start = i_prototype * num_features
        ip_end = ip_start + num_features

        distance_gradient[:, ip_start:ip_end] = _prototype_gradient(
            data, prototypes[i_prototype, :], omega
        )

        io_start = prototypes.size

        distance_gradient[:, io_start:] = _omega_gradient(
            data, prototypes[i_prototype, :], omega
        ).reshape(num_samples, omega.size)

        return distance_gradient


def _prototype_gradient(
    data: np.ndarray, prototype: np.ndarray, omega: np.ndarray
) -> np.ndarray:
    difference = -2 * (data - prototype)
    difference[np.isnan(difference)] = 0
    return np.einsum("ji,ik ->jk", difference, np.dot(omega.T, omega))


def _omega_gradient(
    data: np.ndarray, prototype: np.ndarray, omega: np.ndarray
) -> np.ndarray:
    difference = data - prototype
    difference[np.isnan(difference)] = 0
    scaled_omega = omega.dot(difference.T)
    return np.einsum("ij,jk->jik", scaled_omega, (2 * difference))


def _adaptive_squared_nan_euclidean(sample, prototype, lambda_matrix=None):
    difference = sample - prototype
    difference[np.isnan(difference)] = 0
    return difference.dot(lambda_matrix).dot(difference)
