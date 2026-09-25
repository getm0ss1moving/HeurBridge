"""T7.5: a copied reference is flagged as rediscovery; an unrelated seed program is not."""

from heurbridge.heuristics.macro.registry import program_source
from heurbridge.verify import originality as OR

REF_PY = '''
import numpy as np
def spread(x, alpha):
    out = x.copy()
    for d in (0, 1):
        r = np.argsort(np.argsort(x[:, d])); u = (r + 0.5) / len(x)
        out[:, d] = (1 - alpha) * x[:, d] + alpha * (0.05 + 0.9 * u)
    return out
def heuristic(design, upstream, rng):
    pos = np.array(design.init_pos, dtype=float)
    return spread(pos, 0.5)
'''


def test_rediscovery_flags(tmp_path):
    (tmp_path / "ref").mkdir()
    (tmp_path / "ref" / "spread.py").write_text(REF_PY)
    (tmp_path / "ref" / "gpl.cpp").write_text("int main(){ for(int i=0;i<10;i++){ x[i]+=y[i]*0.5; } return 0; }")
    corpus = OR.build_corpus({"refcode": tmp_path / "ref"})
    renamed = REF_PY.replace("spread", "my_spread").replace("alpha", "a").replace("out", "res")
    rep = OR.rediscovery_report(renamed, corpus)
    assert rep["rediscovery"] and rep["references"]["refcode"]["tokens"] > 0.8
    rep2 = OR.rediscovery_report(program_source("M5", 0), corpus)
    assert not rep2["rediscovery"]
