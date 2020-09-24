from ._base import SolverBaseClass, ScipyBaseSolver
from sklvq._utils import _import_class_from_string

__all__ = ["SolverBaseClass", "ScipyBaseSolver"]

ALIASES = {
    "sgd": "steepest-gradient-descent",
    "bgd": "steepest-gradient-descent",
    "bfgs": "broyden-fletcher-goldfarb-shanno",
    "lbfgs": "limited-memory-bfgs",
    "adam": "adaptive-moment-estimation",
}


def import_from_string(class_string, valid_strings=None) -> type:
    if class_string in ALIASES.keys():
        class_string = ALIASES[class_string]

    if valid_strings is not None:
        if not (class_string in valid_strings):
            raise ValueError("Provided solver_type is invalid.")

    return _import_class_from_string(__name__, class_string)
