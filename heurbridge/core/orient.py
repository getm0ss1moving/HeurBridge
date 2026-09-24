"""Orientation enum and pin-offset transforms (OpenDB semantics).

Index order follows the task spec: R0, R90, R180, R270, MX, MY, MX90, MY90.
DEF / bookshelf names: N, W, S, E, FS, FN, FW, FE respectively.

Transforms act on offsets measured from the object *centre* in the master
(R0) frame, so no bounding-box shift is needed.  Matrices match OpenDB's
``dbTransform::apply``:
  R90 (x,y)->(-y,x)   R180 (-x,-y)   R270 (y,-x)
  MX  (x,-y)          MY   (-x,y)    MXR90 (y,x)   MYR90 (-y,-x)
"""

from __future__ import annotations

import numpy as np

NAMES = ("R0", "R90", "R180", "R270", "MX", "MY", "MX90", "MY90")
DEF_NAMES = ("N", "W", "S", "E", "FS", "FN", "FW", "FE")
R0, R90, R180, R270, MX, MY, MX90, MY90 = range(8)

_FROM_DEF = {n: i for i, n in enumerate(DEF_NAMES)}
_FROM_ODB = {n: i for i, n in enumerate(NAMES)}
_FROM_ODB.update({"MXR90": MX90, "MYR90": MY90})

# 2x2 matrices M such that offset' = M @ offset
MATS = np.array([
    [[1, 0], [0, 1]],     # R0
    [[0, -1], [1, 0]],    # R90
    [[-1, 0], [0, -1]],   # R180
    [[0, 1], [-1, 0]],    # R270
    [[1, 0], [0, -1]],    # MX
    [[-1, 0], [0, 1]],    # MY
    [[0, 1], [1, 0]],     # MX90 (MXR90)
    [[0, -1], [-1, 0]],   # MY90 (MYR90)
], dtype=np.float64)

SWAPS_WH = np.array([False, True, False, True, False, False, True, True])


def from_def(name: str) -> int:
    return _FROM_DEF[name.upper()]


def from_odb(name: str) -> int:
    return _FROM_ODB[name.upper()]


def to_def(idx: int) -> str:
    return DEF_NAMES[int(idx)]


def effective_size(size: np.ndarray, orient: np.ndarray) -> np.ndarray:
    """Footprint (w', h') after orientation; size is N x 2 master (w, h)."""
    out = np.array(size, dtype=np.float64, copy=True)
    sw = SWAPS_WH[np.asarray(orient, dtype=np.int64)]
    out[sw] = out[sw][:, ::-1]
    return out


def apply(offsets: np.ndarray, orient: np.ndarray) -> np.ndarray:
    """Transform centre-relative offsets (P x 2) by per-row orientation indices (P,)."""
    m = MATS[np.asarray(orient, dtype=np.int64)]
    return np.einsum("pij,pj->pi", m, offsets)


def lef_def_v1_offset(ll_offset: np.ndarray, orient: np.ndarray) -> np.ndarray:
    """Reproduce ``eda/harness/lef_def._transform`` exactly (compatibility only).

    It applies the linear map to the lower-left-relative offset without the
    bounding-box shift and swaps FE/FW relative to OpenDB, so it differs from
    the geometric pin position for any orientation other than N.
    """
    dx, dy = ll_offset[:, 0], ll_offset[:, 1]
    o = np.asarray(orient, dtype=np.int64)
    out = np.stack([dx, dy], 1).astype(np.float64)
    table = {
        R0: (dx, dy), R180: (-dx, -dy), R90: (-dy, dx), R270: (dy, -dx),
        MY: (-dx, dy), MX: (dx, -dy), MY90: (dy, dx), MX90: (-dy, -dx),  # FE->(dy,dx), FW->(-dy,-dx)
    }
    for k, (vx, vy) in table.items():
        sel = o == k
        out[sel, 0] = vx[sel]
        out[sel, 1] = vy[sel]
    return out
