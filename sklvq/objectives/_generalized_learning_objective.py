import numpy as np

from ..objectives._base import ObjectiveBaseClass
from .. import activations, discriminants

from typing import Union
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import LVQBaseClass


ACTIVATION_FUNCTIONS = [
    "identity",
    "sigmoid",
    "soft-plus",
    "swish",
]

DISCRIMINANT_FUNCTIONS = [
    "relative-distance",
]


class GeneralizedLearningObjective(ObjectiveBaseClass):
    def __init__(
        self,
        activation_type: Union[str, type],
        activation_params: dict,
        discriminant_type: Union[str, type],
        discriminant_params: dict,
    ):

        if isinstance(activation_type, str):
            activation_class = activations.import_from_string(activation_type)

        if activation_params is None:
            activation_params = {}

        self.activation = activation_class(**activation_params)

        if isinstance(discriminant_type, str):
            discriminant_class = discriminants.import_from_string(discriminant_type)

        if discriminant_params is None:
            discriminant_params = {}

        self.discriminant = discriminant_class(**discriminant_params)

    def __call__(
        self, model: "LVQBaseClass", data: np.ndarray, labels: np.ndarray,
    ) -> np.ndarray:
        """ Computes the Generalized Learning Objective function
            .. math::

                E_{GLVQ} = \\Sigma_{i=1}^{N} f(\\mu(x_i))

        with :math:`\\mu(\\cdot)` the discriminative function and :math:`f(\\cdot)` the activation
        function.

        Parameters
        ----------
        variables: ndarray with shape depending on model parameters
            Flattened 1D array of the variables that are changed, i.e., the model parameters

        model : LVQBaseClass
            The model which can be any LVQBaseClass compatible with this objective function.

        data: ndarray with shape (n_samples, n_features)
            The X

        labels: ndarray with shape (n_samples)

        Returns
        -------
        float:
            The cost
        """
        # model.set_model_params(model.to_params(variables))

        dist_same, dist_diff, _, _ = _compute_distance(data, labels, model)

        # return np.sum(self.activation(self.discriminant(data, labels)))

        return np.sum(self.activation(self.discriminant(dist_same, dist_diff)))

    def gradient(
        self, model: "LVQBaseClass", data: np.ndarray, labels: np.ndarray,
    ) -> np.ndarray:
        """ Computes the Generalized Learning Objective function's gradient
            .. math::
                \\frac{\\partial E_{GLVQ}}{\\partial w_0} = \\frac{\\partial f}{\\partial \\mu}
                \\frac{\\partial \\mu}{\\partial d_0} \\frac{\\partial d_0}{\\partial w_0}

        with :math:`w_0` the prototype with a different label than the X and :math:`d_0`
        the distance to that prototype.

            .. math::
                 \\frac{\\partial E_{GLVQ}}{\\partial w_1} = \\frac{\\partial f}{\\partial \\mu}
                 \\frac{\\partial \\mu}{\\partial d_1} \\frac{\\partial d_1}{\\partial w_1}

        with :math:`w_1` the prototype with the same label as the X and :math:`d_1`
        the distance to that prototype.

        Parameters
        ----------
        variables: ndarray with shape depending on model parameters
            Flattened 1D array of the variables that are changed, i.e., the model parameters

        model : LVQBaseClass
            The model which can be any LVQBaseClass compatible with this objective function.

        data: ndarray with shape (n_samples, n_features)
            The X

        labels: ndarray with shape (n_samples)

        Returns
        -------
            ndarray with shape of input variables
                The generalized learning objective function's gradient

        """

        # model.set_model_params(model.to_params(variables))

        dist_same, dist_diff, i_dist_same, i_dist_diff = _compute_distance(
            data, labels, model
        )
        #  Distance from every sample to every prototype...

        # Distances plus dist_same / dist_diff indices...
        discriminant_score = self.discriminant(dist_same, dist_diff)

        # Gradient is basically model._variables... way to view params but also single
        # prototype/omega?
        gradient_buffer = np.zeros(model.get_variables().size)


        # For each prototype
        for i_prototype in range(0, model.prototypes_labels_.size):
            # Find for which samples it is the closest/winner AND has the same label
            ii_winner_same = i_prototype == i_dist_same
            if any(ii_winner_same):
                # Only if these cases exist we can compute an update
                # Computes the following partial derivative: df/du
                activation_gradient = self.activation.gradient(
                    discriminant_score[ii_winner_same]
                )

                #  Computes the following partial derivatives: du/ddi, with i = 1
                discriminant_gradient = self.discriminant.gradient(
                    dist_same[ii_winner_same], dist_diff[ii_winner_same], True
                )

                # Computes the following partial derivatives: ddi/dwi, with i = 1
                distance_gradient = model._distance.gradient(
                    data[ii_winner_same, :], model, i_prototype
                )

                # The distance vectors weighted by the activation and discriminant partial
                # derivatives.
                model.add_partial_gradient(gradient_buffer, (
                    activation_gradient * discriminant_gradient
                ).dot(distance_gradient), i_prototype)

            # Find for which samples this prototype is the closest and has a different label
            ii_winner_diff = i_prototype == i_dist_diff
            if any(ii_winner_diff):
                # Computes the following partial derivative: df/du
                activation_gradient = self.activation.gradient(
                    discriminant_score[ii_winner_diff]
                )

                #  Computes the following partial derivatives: du/ddi, with i = 2
                discriminant_gradient = self.discriminant.gradient(
                    dist_same[ii_winner_diff], dist_diff[ii_winner_diff], False
                )

                # Computes the following partial derivatives: ddi/dwi, with i = 2
                distance_gradient = model._distance.gradient(
                    data[ii_winner_diff, :], model, i_prototype
                )

                # The distance vectors weighted by the activation and discriminant partial
                # derivatives.
                model.add_partial_gradient(gradient_buffer, (
                    activation_gradient * discriminant_gradient
                ).dot(distance_gradient), i_prototype)

        return gradient_buffer


def _find_min(indices: np.ndarray, distances: np.ndarray) -> (np.ndarray, np.ndarray):
    """ Helper function to find the minimum distance and the index of this distance. """
    dist_temp = np.where(indices, distances, np.inf)
    return dist_temp.min(axis=1), dist_temp.argmin(axis=1)


def _compute_distance(data: np.ndarray, labels: np.ndarray, model: "LVQBaseClass"):
    """ Computes the distances between each prototype and each observation and finds all indices
    where the shortest distance is that of the prototype with the same label and with a different label. """

    # Step 1: Compute distances between X and the model (how is depending on model and coupled
    # distance function)
    distances = model._distance(data, model)

    # Step 2: Find for all samples the distance between closest prototype with same label (d1)
    # and different label (d2). ii_same marks for all samples the prototype with the same label.
    ii_same = np.transpose(
        np.array(
            [labels == prototype_label for prototype_label in model.prototypes_labels_]
        )
    )

    # For each prototype mark the samples that have a different label
    ii_diff = ~ii_same

    # For each sample find the closest prototype with the same label. Returns distance and index
    # of prototype
    dist_same, i_dist_same = _find_min(ii_same, distances)

    # For each sample find the closest prototype with a different label. Returns distance and
    # index of prototype
    dist_diff, i_dist_diff = _find_min(ii_diff, distances)

    return dist_same, dist_diff, i_dist_same, i_dist_diff