#!/usr/bin/env python3
"""T1.1 exit test: load -> write -> load is the identity and exact HPWL is preserved, on every T0.4 design.

  python scripts/roundtrip_all.py              # bookshelf: ibm01-18, adaptec1-4, bigblue1-4 (.pl writer)
  python scripts/roundtrip_all.py --lefdef     # LEF/DEF: ibm01-18 (DEF COMPONENTS writer)
"""
import argparse, json, math, sys, tempfile, time
import numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from heurbridge.core import bookshelf, defio, design as D  # noqa: E402


def bookshelf_rows():
    for suite, names in (("ibm_bookshelf", ["ibm%02d" % i for i in range(1, 19)]),
                         ("ispd2005", ["adaptec%d" % i for i in range(1, 5)] + ["bigblue%d" % i for i in range(1, 5)])):
        for n in names:
            aux = ROOT / "benchmarks" / suite / n / (n + ".aux")
            t = time.time()
            d, l = bookshelf.load_bookshelf(aux)
            with tempfile.TemporaryDirectory() as td:
                d2, l2 = bookshelf.load_bookshelf(bookshelf.write_bookshelf_copy(d, l, td))
            yield suite, n, d, l, d2, l2, t


def lefdef_rows():
    for n in ["ibm%02d" % i for i in range(1, 19)]:
        dd = ROOT / "benchmarks" / "ibm_lefdef" / n
        t = time.time()
        d, l = defio.load_def_design(dd / (n + ".def"), [dd / (n + ".lef")], design_id=n)
        with tempfile.TemporaryDirectory() as td:
            out = defio.write_def(d, l, Path(td) / (n + ".def"))
            d2, l2 = defio.load_def_design(out, [dd / (n + ".lef")], design_id=n)
        yield "ibm_lefdef", n, d, l, d2, l2, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lefdef", action="store_true")
    a = ap.parse_args()
    rows = []
    for suite, n, d, l, d2, l2, t in (lefdef_rows() if a.lefdef else bookshelf_rows()):
        h1, h2 = D.hpwl(d, l), D.hpwl(d2, l2)
        same_hpwl = h1 == h2 or (math.isnan(h1) and math.isnan(h2))    # NaN: the source leaves objects unplaced
        ok = d.schema_hash() == d2.schema_hash() and l.equals(l2) and same_hpwl
        rows.append({"design": n, "suite": suite, "objects": d.n_objects, "nets": d.n_nets, "identity": bool(ok),
                     "unplaced": int(np.isnan(l.pos).any(1).sum()), "hpwl": None if math.isnan(h1) else h1,
                     "seconds": round(time.time() - t, 1)})
        print(json.dumps(rows[-1]), flush=True)
    name = "T1_roundtrip_lefdef.json" if a.lefdef else "T1_roundtrip_bookshelf.json"
    (ROOT / "reports" / name).write_text(json.dumps(rows, indent=1))
    print("ALL_IDENTITY" if all(r["identity"] for r in rows) else "IDENTITY_FAILURES", sum(r["identity"] for r in rows), "/", len(rows))


if __name__ == "__main__":
    main()
