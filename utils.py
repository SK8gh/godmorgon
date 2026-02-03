import numpy.typing as npt
from typing import Tuple
import numpy as np


def distance(a: npt.ArrayLike, b: npt.ArrayLike, p: int = 2) -> float:
    """
    Compute the L^p distance between two vectors a and b having the same dimension, p defaulted to 2 (Euclidean distance)
    """
    a = np.array(a)
    b = np.array(b)

    assert a.shape == b.shape

    return np.linalg.norm(a - b, ord=p)


def max_n(arr: npt.ArrayLike, n: int, descending: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    """
    Return the n max values and their indices from the input array, in descending order by default
    """
    arr = np.array(arr)
    if n <= 0:
        return np.array([]), np.array([])

    # Get indices of the n max values
    indices = np.argpartition(a=arr, kth=-n)[-n:]

    # Sort these n values in descending order
    indices = indices[np.argsort(arr[indices])]

    if descending:
        indices = indices[::-1]

    values = arr[indices]

    return values, indices


def _offset_values(arr: npt.ArrayLike, v: float = np.inf, left: bool = True) -> np.ndarray:
    """
    Offsetting values from an array, adding a default value at the beginning or end. The returned array has the same
    size as 'arr' so this is not an append operation (left or right) nor an extension
    """
    arr = np.asarray(arr)
    out = np.empty_like(arr)

    if left:
        out[0] = v
        out[1:] = arr[:-1]

    else:
        out[-1] = v
        out[:-1] = arr[1:]

    return out
