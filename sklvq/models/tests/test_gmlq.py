import pytest
import numpy as np

from sklearn import datasets
from sklearn import preprocessing
from sklearn.model_selection import (
    GridSearchCV,
    RepeatedStratifiedKFold,
)
from sklearn.pipeline import make_pipeline

from .. import GMLVQ


def test_gmlvq():
    iris = datasets.load_iris()

    estimator = GMLVQ()
    pipeline = make_pipeline(preprocessing.StandardScaler(), estimator)

    # Run each solver ones
    solvers_types = [
        "lbfgs",
        "bfgs",
        "steepest-gradient-descent",
        "waypoint-gradient-descent",
        "adaptive-moment-estimation",
    ]
    discriminant_types = ["relative-distance"]

    # Every compatible distance
    distance_types = ["adaptive-squared-euclidean"]

    # Every compatible activation
    activation_types = ["identity", "sigmoid", "soft-plus", "swish"]

    param_grid = [
        {
            "gmlvq__solver_type": solvers_types,
            "gmlvq__discriminant_type": discriminant_types,
            "gmlvq__distance_type": distance_types,
            "gmlvq__activation_type": activation_types,
        }
    ]

    repeated_kfolds = RepeatedStratifiedKFold(n_splits=2, n_repeats=1)

    search = GridSearchCV(
        pipeline,
        param_grid,
        scoring="accuracy",
        cv=repeated_kfolds,
        return_train_score=True,
    )

    search.fit(iris.data, iris.target)

    assert np.all(search.cv_results_["mean_train_score"] > 0.75)
    assert np.all(search.cv_results_["mean_test_score"] > 0.75)

    print("\nBest parameter (CV score=%0.3f):" % search.best_score_)
    print(search.best_params_)