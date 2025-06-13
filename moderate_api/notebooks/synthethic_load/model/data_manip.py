import numpy as np


def revert_reshape_arr(arr: np.ndarray) -> np.ndarray:
    """
    Reverts the operation of `reshape_arr`.
    """
    arr = arr.T.reshape(-1, arr.shape[0])
    return arr


def invert_min_max_scaler(
    arr_scaled: np.ndarray, arr_minMax: np.ndarray, featureRange: tuple[int, int]
) -> np.ndarray:
    """
    Reverts the operation of `min_max_scaler`.
    """
    valMin, valMax = arr_minMax[0], arr_minMax[1]
    arr = (arr_scaled - featureRange[0]) * (valMax - valMin) / (
        featureRange[1] - featureRange[0]
    ) + valMin
    return arr
