import numpy as np

from .test_common import check_init_distance
from .test_common import check_distance
from .test_common import DummyLVQ


def test_adaptive_squared_euclidean():
    distance_class = check_init_distance("local-adaptive-squared-euclidean")

    distfun = distance_class()

    # Some X and prototypes
    data = np.array([[1, 2, 3], [-1, -2, -3]])
    p = np.array([[1, 2, 3], [-1, -2, -3], [0, 0, 0]])

    shape = (data.shape[1], data.shape[1])
    o = np.array([np.eye(*shape) for _ in range(p.shape[0])])

    model = DummyLVQ(p, np.array([0, 1]), o)
    model.relevance_params = {"localization": "prototypes"}

    check_distance(distfun, data, model)

    # Check force_all_finite settings

    # Rectangular omega