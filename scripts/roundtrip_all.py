#!/usr/bin/env python3
"""T1.1 exit test on every bookshelf benchmark: load -> write .pl -> load is the identity; exact HPWL preserved."""
import json, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from heurbridge.core import bookshelf, design as D  # noqa: E402
rows = []
for suite, names in (("ibm_bookshelf", ["ibm%02d" % i for i in range(1, 19)]),
                     ("ispd2005", ["adaptec%d" % i for i in range(1, 5)] + ["bigblue%d" % i for i in range(1, 5)])):
    for n in names:
        aux = ROOT / "benchmarks" / suite / n / (n + ".aux")
        t = time.time()
        d, l = bookshelf.load_bookshelf(aux)
        with tempfile.TemporaryDirectory() as td:
            d2, l2 = bookshelf.load_bookshelf(bookshelf.write_bookshelf_copy(d, l, td))
        ok = d.schema_hash() == d2.schema_hash() and l.equals(l2) and D.hpwl(d, l) == D.hpwl(d2, l2)
        rows.append({"design": n, "suite": suite, "objects": d.n_objects, "nets": d.n_nets, "identity": bool(ok),
                     "hpwl": D.hpwl(d, l), "seconds": round(time.time() - t, 1)})
        print(json.dumps(rows[-1]), flush=True)
(ROOT / "reports" / "T1_roundtrip_bookshelf.json").write_text(json.dumps(rows, indent=1))
print("ALL_IDENTITY" if all(r["identity"] for r in rows) else "IDENTITY_FAILURES", sum(r["identity"] for r in rows), "/", len(rows))
