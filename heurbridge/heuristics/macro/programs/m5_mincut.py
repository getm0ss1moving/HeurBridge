# M5 recursive min-cut bisection with macro slots.  The region is cut along its longer side; macros are
# bisected by Kernighan-Lin on the affinity graph (terminal propagation: each macro's anchor pull adds a
# side preference), region halves are sized by macro area, recursion until one macro per region.
# PARAMS: kl_iters, pull_w
def heuristic(design, upstream, rng):
    import networkx as nx
    from networkx.algorithms.community import kernighan_lin_bisection
    P = PARAMS
    sz, aff = design.macro_size, design.macro_aff
    M = len(sz)
    area = sz[:, 0] * sz[:, 1]
    out = {}

    def rec(members, box):
        x0, y0, x1, y1 = box
        if len(members) == 1:
            k = members[0]
            out[k] = clip_centres(np.array([(x0 + x1) / 2, (y0 + y1) / 2]), sz[k])
            return
        vertical = (x1 - x0) >= (y1 - y0)
        mid_axis = 0 if vertical else 1
        G = nx.Graph()
        for k in members:                                   # canonical insertion order
            G.add_node(int(k))
        for a_ in range(len(members)):
            for b_ in range(a_ + 1, len(members)):
                ka, kb = members[a_], members[b_]
                if aff[ka, kb] > 0:
                    G.add_edge(int(ka), int(kb), weight=float(aff[ka, kb]))
        # initial split by anchor pull along the cut axis (terminal propagation)
        key = sorted(members, key=lambda k: (design.io_pull[k][mid_axis] * P["pull_w"] + 0.0, k))
        half = len(key) // 2
        init = (set(int(k) for k in key[:half]), set(int(k) for k in key[half:]))
        seed = int(rng.integers(0, 2 ** 31 - 1))
        try:
            A, B = kernighan_lin_bisection(G, partition=init, max_iter=P["kl_iters"], weight="weight", seed=seed)
        except Exception:
            A, B = init
        A = sorted(A)
        B = sorted(B)
        if not A or not B:
            A, B = sorted(int(k) for k in key[:half]), sorted(int(k) for k in key[half:])
        # left/bottom half gets the part whose anchors pull lower along the axis
        pa = np.mean([design.io_pull[k][mid_axis] for k in A])
        pb = np.mean([design.io_pull[k][mid_axis] for k in B])
        if pa > pb:
            A, B = B, A
        fa = area[A].sum() / max(area[A].sum() + area[B].sum(), 1e-12)
        if vertical:
            xm = x0 + fa * (x1 - x0)
            rec(A, (x0, y0, xm, y1))
            rec(B, (xm, y0, x1, y1))
        else:
            ym = y0 + fa * (y1 - y0)
            rec(A, (x0, y0, x1, ym))
            rec(B, (x0, ym, x1, y1))
    if M:
        rec(list(range(M)), (0.0, 0.0, 1.0, 1.0))
    return write_back(design, out)
