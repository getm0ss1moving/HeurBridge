# M7 random legal placement (control).  PARAMS: tries (rejection samples per macro; 1 = pure uniform)
def heuristic(design, upstream, rng):
    P = PARAMS
    sz = design.macro_size
    M = len(sz)
    placed_c, placed_s, out = [], [], {}
    for k in range(M):                                   # canonical order
        best = None
        for t in range(P["tries"]):
            c = rng.uniform(sz[k] / 2, 1 - sz[k] / 2)
            if not placed_c:
                best = c
                break
            pc, ps = np.array(placed_c), np.array(placed_s)
            ov = (np.clip(np.minimum(c[0] + sz[k, 0] / 2, pc[:, 0] + ps[:, 0] / 2) - np.maximum(c[0] - sz[k, 0] / 2, pc[:, 0] - ps[:, 0] / 2), 0, None)
                  * np.clip(np.minimum(c[1] + sz[k, 1] / 2, pc[:, 1] + ps[:, 1] / 2) - np.maximum(c[1] - sz[k, 1] / 2, pc[:, 1] - ps[:, 1] / 2), 0, None)).sum()
            ov += obstacle_overlap(c[None], sz[k][None], design.obstacles)[0]
            if best is None or ov < best[1]:
                best = (c, ov)
            if ov == 0:
                break
        c = best[0] if isinstance(best, tuple) else best
        placed_c.append(c)
        placed_s.append(sz[k])
        out[k] = c
    return write_back(design, out)
