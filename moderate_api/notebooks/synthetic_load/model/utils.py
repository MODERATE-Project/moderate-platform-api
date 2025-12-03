from typing import Any

import numpy as np
from numba import njit
from numpy.typing import NDArray
from scipy.stats import skew


def compute_trends(
    arr: NDArray[Any], arr_dt: Any, res: list[str] | None = None
) -> dict[str, NDArray[np.float32]]:
    if res is None:
        res = ["hour", "day", "week", "month"]
    trend_dict = {}
    groups = {}
    if "hour" in res:
        groups["hour"] = arr_dt.hour.to_numpy()
    if "day" in res:
        groups["day"] = arr_dt.day.to_numpy()
    if "week" in res:
        groups["week"] = arr_dt.isocalendar().week.to_numpy()
    if "month" in res:
        groups["month"] = arr_dt.month.to_numpy()

    for key in res:
        groupKeys = groups[key]
        sortedIdx = np.argsort(groupKeys)
        sortedKeys = groupKeys[sortedIdx]
        boundaries_list = [0]
        for idx in range(1, len(sortedKeys)):
            if sortedKeys[idx] != sortedKeys[idx - 1]:
                boundaries_list.append(idx)
        boundaries_list.append(len(sortedKeys))
        boundaries: NDArray[np.int_] = np.array(boundaries_list)
        groupCount = len(boundaries) - 1
        arr_trend = compute_group_stats(
            arr, sortedIdx, boundaries, groupCount, arr.shape[1]
        )
        trend_dict[key] = arr_trend
    return trend_dict


@njit  # type: ignore[untyped-decorator]
def compute_group_stats(
    X: NDArray[Any],
    sortedIdx: NDArray[Any],
    boundaries: NDArray[Any],
    groupCount: int,
    colCount: int,
) -> NDArray[np.float32]:
    out = np.empty((groupCount, 6), dtype=np.float32)
    for i in range(groupCount):
        start, end = boundaries[i], boundaries[i + 1]
        groupSize = end - start
        meanTotal, stdTotal, minTotal, maxTotal, medianTotal, skewTotal = (
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        )
        for j in range(colCount):
            n = groupSize
            tmp = np.empty(n, dtype=np.float32)
            for k in range(n):
                tmp[k] = X[sortedIdx[start + k], j]

            # Compute mean, min and max in one pass.
            s = tmp[0]
            min = tmp[0]
            max = tmp[0]
            for k in range(1, n):
                v = tmp[k]
                s += v
                if v < min:
                    min = v
                if v > max:
                    max = v
            mean = s / n

            # Compute standard deviation and the third central moment for skew.
            ssd = 0.0
            scd = 0.0
            for k in range(n):
                diff = tmp[k] - mean
                ssd += diff * diff
                scd += diff * diff * diff
            std = np.sqrt(ssd / n)

            # Compute median via sorting.
            arr = tmp.copy()
            arr.sort()
            if n % 2 == 1:
                median = arr[n // 2]
            else:
                median = 0.5 * (arr[n // 2 - 1] + arr[n // 2])

            # Compute skew; if std is zero, define skew as 0.
            if std == 0:
                skew_val = 0.0
            else:
                skew_val = (scd / n) / (std**3)

            meanTotal += mean
            stdTotal += std
            medianTotal += median
            minTotal += min
            maxTotal += max
            skewTotal += skew_val

        # Order must match: ['mean', 'std', 'median', 'min', 'max', 'skew']
        out[i, 0] = meanTotal / colCount  # mean
        out[i, 1] = stdTotal / colCount  # std
        out[i, 2] = medianTotal / colCount  # median
        out[i, 3] = minTotal / colCount  # min
        out[i, 4] = maxTotal / colCount  # max
        out[i, 5] = skewTotal / colCount  # skew
    return out


def calc_features(arr: NDArray[Any], axis: int) -> NDArray[np.float32]:
    """
    Calculate statistical features of the input array along the specified axis.
    Handles NaN values and edge cases safely.
    """
    # Safety check for NaN values in input
    if np.isnan(arr).any():
        print("Warning: NaN values detected in input array for feature calculation")
        # Replace NaN values with 0 for calculation
        arr = np.nan_to_num(arr, nan=0.0)

    # Initialize output array
    arr_features = np.zeros(
        (9, arr.shape[1] if axis == 0 else arr.shape[0]), dtype=np.float32
    )

    try:
        # Calculate mean
        arr_features[0] = np.mean(arr, axis=axis)

        # Calculate standard deviation
        std = np.std(arr, axis=axis)
        arr_features[1] = np.nan_to_num(std, nan=0.0)  # Replace NaN with 0

        # Calculate min and max
        arr_features[2] = np.min(arr, axis=axis)
        arr_features[3] = np.max(arr, axis=axis)

        # Calculate median
        arr_features[4] = np.median(arr, axis=axis)

        # Calculate skewness with safety checks
        try:
            skewness = skew(arr, axis=axis)
            # Replace NaN and inf values in skewness with 0
            arr_features[5] = np.nan_to_num(skewness, nan=0.0, posinf=0.0, neginf=0.0)
        except Exception as e:
            print(f"Warning: Error calculating skewness: {e}")
            arr_features[5] = 0.0

        # Calculate peak to peak range
        arr_features[6] = np.ptp(arr, axis=axis)

        # Calculate quartiles
        try:
            arr_features[7] = np.percentile(arr, 25, axis=axis)
            arr_features[8] = np.percentile(arr, 75, axis=axis)
        except Exception as e:
            print(f"Warning: Error calculating quartiles: {e}")
            # If quartile calculation fails, use min and max as fallback
            arr_features[7] = arr_features[2]  # Use min as lower quartile
            arr_features[8] = arr_features[3]  # Use max as upper quartile

    except Exception as e:
        print(f"Warning: Error in feature calculation: {e}")
        # Return zeros if calculation fails
        return np.zeros(
            (9, arr.shape[1] if axis == 0 else arr.shape[0]), dtype=np.float32
        )

    # Final safety check for any remaining NaN values
    if np.isnan(arr_features).any():
        print("Warning: NaN values detected in calculated features")
        arr_features = np.nan_to_num(arr_features, nan=0.0)

    return arr_features
