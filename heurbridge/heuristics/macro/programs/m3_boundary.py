# M3 boundary-biased greedy mask placement (FlowPlace data-generation prior used as a heuristic).
# Macros largest first; each samples a free grid slot with probability ~ exp(-cost/temp),
# cost = boundary distance / lam + wl_w * connectivity pull.  PARAMS: grid, lam, wl_w, temp
def heuristic(design, upstream, rng):
    P = PARAMS
    sz, aff = design.macro_size, design.macro_aff
    M = len(sz)
    order = sorted(range(M), key=lambda k: (-(sz[k, 0] * sz[k, 1]), k))
    grid = Grid(P["grid"], design.obstacles, design.misc["halo"])

    def cost(k, cand, placed):
        lo, hi = cand - sz[k] / 2, cand + sz[k] / 2
        bd = np.minimum(np.minimum(lo[:, 0], lo[:, 1]), np.minimum(1 - hi[:, 0], 1 - hi[:, 1]))
        wl = design.io_w[k] * np.abs(cand - design.io_pull[k]).sum(1)
        for j, cj in placed.items():
            if aff[k, j] > 0:
                wl = wl + aff[k, j] * np.abs(cand - cj).sum(1)
        norm = (design.io_w[k] + aff[k].sum()) or 1.0
        return bd / P["lam"] + P["wl_w"] * wl / norm
    out = greedy_place(order, sz, cost, grid, rng=rng, temp=P["temp"])
    return write_back(design, out)
