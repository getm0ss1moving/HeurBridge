# M6 OrderPlace-style ordering policy + deterministic greedy placement.
# Order by a score (PARAMS["order"]: "area" | "conn" | "io"), then each macro takes the free slot that
# minimizes connectivity-weighted distance to placed macros and anchors plus a boundary term.
def heuristic(design, upstream, rng):
    P = PARAMS
    sz, aff = design.macro_size, design.macro_aff
    M = len(sz)
    area = sz[:, 0] * sz[:, 1]
    score = {"area": area, "conn": aff.sum(1) + design.io_w, "io": design.io_w + 1e-9 * area}[P["order"]]
    order = sorted(range(M), key=lambda k: (-score[k], k))
    grid = Grid(P["grid"], design.obstacles, design.misc["halo"])

    def cost(k, cand, placed):
        c = design.io_w[k] * np.abs(cand - design.io_pull[k]).sum(1)
        for j, cj in placed.items():
            if aff[k, j] > 0:
                c = c + aff[k, j] * np.abs(cand - cj).sum(1)
        norm = (design.io_w[k] + aff[k].sum()) or 1.0
        lo, hi = cand - sz[k] / 2, cand + sz[k] / 2
        bd = np.minimum(np.minimum(lo[:, 0], lo[:, 1]), np.minimum(1 - hi[:, 0], 1 - hi[:, 1]))
        return c / norm + P["beta"] * bd
    out = greedy_place(order, sz, cost, grid)
    return write_back(design, out)
