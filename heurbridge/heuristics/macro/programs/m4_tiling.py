# M4 dataflow/hierarchy clustering + tiling.  Macros are grouped (agglomerative clustering on the affinity,
# average linkage), groups are ordered along a 1-D spectral (dataflow) order and packed as compact tiles
# along the core perimeter (or on a centred grid of blocks).  PARAMS: n_groups ("sqrt" or int), mode
# ("perimeter" | "blocks"), gap
def heuristic(design, upstream, rng):
    from scipy.cluster.hierarchy import linkage, fcluster
    P = PARAMS
    sz, aff = design.macro_size, design.macro_aff
    M = len(sz)
    if M == 0:
        return np.array(design.init_pos, dtype=float)
    k_g = max(1, int(round(math.sqrt(M)))) if P["n_groups"] == "sqrt" else min(M, int(P["n_groups"]))
    if M > 1 and k_g > 1:
        a = aff + aff.T
        s = a / (a.max() or 1.0)
        dist = 1.0 - s
        np.fill_diagonal(dist, 0.0)
        iu = np.triu_indices(M, 1)
        Z = linkage(dist[iu], method="average")
        lab = fcluster(Z, t=k_g, criterion="maxclust") - 1
    else:
        lab = np.zeros(M, dtype=int)
    groups = [np.flatnonzero(lab == g) for g in range(lab.max() + 1)]
    groups = [g for g in groups if len(g)]
    G = len(groups)
    # dataflow order of groups: Fiedler vector of the group affinity graph (ties -> group id)
    ga = np.zeros((G, G))
    for x in range(G):
        for y in range(G):
            if x != y:
                ga[x, y] = aff[np.ix_(groups[x], groups[y])].sum()
    if G > 2:
        L = np.diag(ga.sum(1)) - ga
        w, v = np.linalg.eigh(L)
        f = v[:, 1] * (1 if v[np.argmax(np.abs(v[:, 1])), 1] >= 0 else -1)
        gorder = sorted(range(G), key=lambda x: (f[x], x))
    else:
        gorder = list(range(G))
    out = {}
    gap = P["gap"]
    if P["mode"] == "blocks":
        cols = int(math.ceil(math.sqrt(G)))
        cells = [(0.5 + i) / cols for i in range(cols)]
        slots = [(cells[x % cols], cells[x // cols] if x // cols < cols else 0.5) for x in range(G)]
        for s_i, gidx in zip(slots, gorder):
            mem = sorted(groups[gidx], key=lambda k: (-(sz[k, 0] * sz[k, 1]), k))
            n = len(mem)
            r = int(math.ceil(math.sqrt(n)))
            wmax, hmax = sz[mem, 0].max(), sz[mem, 1].max()
            for q, k in enumerate(mem):
                out[k] = np.array([s_i[0] + (q % r - (r - 1) / 2) * (wmax + gap), s_i[1] + (q // r - (r - 1) / 2) * (hmax + gap)])
    else:
        # walk the perimeter counter-clockwise from the bottom-left corner, stacking each group's macros
        perim_t = 0.0
        for gidx in gorder:
            mem = sorted(groups[gidx], key=lambda k: (-(sz[k, 0] * sz[k, 1]), k))
            for k in mem:
                w, h = sz[k]
                side = int(perim_t) % 4
                u = perim_t - int(perim_t)
                if side == 0:
                    c = np.array([w / 2 + u * (1 - w), h / 2])
                elif side == 1:
                    c = np.array([1 - w / 2, h / 2 + u * (1 - h)])
                elif side == 2:
                    c = np.array([1 - w / 2 - u * (1 - w), 1 - h / 2])
                else:
                    c = np.array([w / 2, 1 - h / 2 - u * (1 - h)])
                out[k] = c
                perim_t += (w if side in (0, 2) else h) + gap
            perim_t += 2 * gap
    for k in out:
        out[k] = clip_centres(out[k], sz[k])
    return write_back(design, out)
