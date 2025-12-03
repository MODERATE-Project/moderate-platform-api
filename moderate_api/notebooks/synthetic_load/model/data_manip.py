from typing import Any

from numpy.typing import NDArray


def revert_reshape_arr(arr: NDArray[Any]) -> NDArray[Any]:
    """
    Reverts the operation of `reshape_arr`.
    """
    arr = arr.T.reshape(-1, arr.shape[0])
    return arr


def invert_min_max_scaler(
    arr_scaled: NDArray[Any],
    arr_minMax: NDArray[Any],
    featureRange: tuple[int, int],
) -> NDArray[Any]:
    """
    Reverts the operation of `min_max_scaler`.
    """
    valMin, valMax = arr_minMax[0], arr_minMax[1]
    arr: NDArray[Any] = (arr_scaled - featureRange[0]) * (valMax - valMin) / (
        featureRange[1] - featureRange[0]
    ) + valMin
    return arr
