# M2 simulated annealing on Hier-RTLMP-style cost terms over macro positions (+ orientation pass).
# cost = a*bbox_area + b*WL + c*outline + d*boundary + e*notch + f*overlap, each normalized by its
# value at the start.  Moves: shift (Gaussian, shrinking), swap two macros of the same group, swap any two.
# Start: M6 greedy (conn order).  PARAMS: iters, w (dict of weights), step0, T0, notch_gap, flip
def heuristic(design, upstream, rng):
    P = PARAMS
    sz, aff, obst = design.macro_size, design.macro_aff, design.obstacles
    M = len(sz)
    if M == 0:
        return np.array(design.init_pos, dtype=float)
    order = sorted(range(M), key=lambda k: (-(aff[k].sum() + design.io_w[k]), k))
    grid = Grid(64, obst, design.misc["halo"])

    def gcost(k, cand, placed):
        c = design.io_w[k] * np.abs(cand - design.io_pull[k]).sum(1)
        for j, cj in placed.items():
            if aff[k, j] > 0:
                c = c + aff[k, j] * np.abs(cand - cj).sum(1)
        return c
    start = greedy_place(order, sz, gcost, grid)
    c = np.array([start.get(k, np.array([0.5, 0.5])) for k in range(M)], dtype=float)
    g = P["notch_gap"]

    def terms(c):
        lo, hi = c - sz / 2, c + sz / 2
        bbox = float((hi[:, 0].max() - lo[:, 0].min()) * (hi[:, 1].max() - lo[:, 1].min()))
        wl = wirelength(c, aff, design.io_pull, design.io_w)
        outline = float((np.clip(-lo, 0, None).sum() + np.clip(hi - 1, 0, None).sum()))
        bd = float(np.clip(boundary_dist(c, sz), 0, None).sum())
        gx = np.maximum(lo[:, None, 0] - hi[None, :, 0], lo[None, :, 0] - hi[:, None, 0])
        gy = np.maximum(lo[:, None, 1] - hi[None, :, 1], lo[None, :, 1] - hi[:, None, 1])
        side = ((gx > 0) & (gx < g) & (gy < 0)) | ((gy > 0) & (gy < g) & (gx < 0))
        notch = float((side * (g - np.maximum(gx, gy))).sum() / 2)
        ov = float(overlap_pairs(c, sz).sum() / 2 + obstacle_overlap(c, sz, obst).sum())
        return np.array([bbox, wl, outline, bd, notch, ov])
    t0 = terms(c)
    scale = np.where(t0 > 1e-12, t0, 1.0)
    scale[5] = max(float((sz[:, 0] * sz[:, 1]).sum()) * 0.01, 1e-9)       # overlap normalized by macro area
    scale[2] = scale[5]
    wv = np.array([P["w"][k] for k in ("area", "wl", "outline", "boundary", "notch", "overlap")])
    cur = float((wv * terms(c) / scale).sum())
    best_c, best = c.copy(), cur
    T = P["T0"]
    n = P["iters"]
    groups = design.macro_group
    for it in range(n):
        step = P["step0"] * (1.0 - it / n) + 0.002
        u = rng.random()
        new = c.copy()
        if u < 0.7 or M < 2:
            k = int(rng.integers(M))
            new[k] = new[k] + rng.normal(0.0, step, 2)
        elif u < 0.85:
            k = int(rng.integers(M))
            same = np.flatnonzero(groups == groups[k])
            j = int(same[int(rng.integers(len(same)))])
            new[[k, j]] = new[[j, k]]
        else:
            k, j = int(rng.integers(M)), int(rng.integers(M))
            new[[k, j]] = new[[j, k]]
        new = clip_centres(new, sz)
        val = float((wv * terms(new) / scale).sum())
        if val <= cur or rng.random() < math.exp(-(val - cur) / max(T, 1e-12)):
            c, cur = new, val
            if cur < best:
                best_c, best = c.copy(), cur
        T *= P["cool"]
    pos = write_back(design, {k: best_c[k] for k in range(M)})
    if not P["flip"]:
        return pos
    # orientation pass: per macro choose among R0/MX/MY/R180 the flip that minimizes its pins' distance to
    # the centroid of the other pins on each net (pin offsets rotate with the orientation)
    ori = np.array(design.orient, dtype=np.int64)
    mats = {0: np.array([[1, 0], [0, 1]]), 4: np.array([[1, 0], [0, -1]]), 5: np.array([[-1, 0], [0, 1]]),
            2: np.array([[-1, 0], [0, -1]])}
    mo = design.macro_order
    pin_net = np.repeat(np.arange(design.n_nets), np.diff(design.net_ptr))
    objs = design.pin_obj[design.pin_idx]
    offs = design.pin_off[design.pin_idx]
    pp = pos[objs] + offs
    ok = np.isfinite(pp).all(1)
    sums = np.zeros((design.n_nets, 2))
    cnt = np.zeros(design.n_nets)
    np.add.at(sums, pin_net[ok], pp[ok])
    np.add.at(cnt, pin_net[ok], 1.0)
    for k in range(M):
        i = mo[k]
        sel = np.flatnonzero(objs == i)
        if len(sel) == 0 or ori[i] not in mats:
            continue
        nets = pin_net[sel]
        other = (sums[nets] - pp[sel]) / np.maximum(cnt[nets] - 1, 1)[:, None]
        has = cnt[nets] > 1
        if not has.any():
            continue
        base = np.linalg.inv(mats[ori[i]]) @ offs[sel].T          # offsets in the master frame
        best_o, best_d = ori[i], None
        for o, m in mats.items():
            d = np.abs((pos[i][:, None] + m @ base).T[has] - other[has]).sum()
            if best_d is None or d < best_d - 1e-12:
                best_o, best_d = o, d
        ori[i] = best_o
    return pos, ori
