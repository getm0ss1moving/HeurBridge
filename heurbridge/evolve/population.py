"""Population manager (task T5.3): MAP-Elites grid per island, migration, parent selection, portfolio.

Descriptor of a program = (family tag, structural decision type from RLCE, runtime class).
  family tag      inherited from the seed family (M2..M7) or "new"
  decision type   dominant structural error the program's last diagnosis targeted: orientation | grouping |
                  position | none
  runtime class   0: < 1 s, 1: 1-10 s, 2: 10-60 s
Each island keeps the best-F program per descriptor cell; every ``migrate_every`` generations the best
program of each island is copied to the next island (ring).  Parents are drawn uniformly over occupied
cells of an island (islands visited round-robin).  The portfolio is the greedy submodular top-q of all
programs by post-bridge costs.  Fitness re-anchoring replaces every program's B/F after a bridge promotion.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

import numpy as np

from .fitness import FitnessConfig, greedy_prune, refinability_fitness


def runtime_class(s: float) -> int:
    return 0 if s < 1.0 else (1 if s < 10.0 else 2)


@dataclass
class Individual:
    id: str
    source: str
    sha256: str
    family: str
    decision: str = "none"
    runtime_s: float = 0.0
    B: list = field(default_factory=list)          # post-bridge cost per evo design
    A: list = field(default_factory=list)          # raw cost per evo design (baselines / ablation)
    F: float = -np.inf
    parent: str | None = None
    generation: int = 0
    island: int = 0
    strategy: str = ""

    @property
    def cell(self):
        return (self.family, self.decision, runtime_class(self.runtime_s))


class Population:
    def __init__(self, n_islands: int = 4, migrate_every: int = 5, q: int = 8, fcfg: FitnessConfig | None = None):
        self.n_islands, self.migrate_every, self.q = n_islands, migrate_every, q
        self.fcfg = fcfg or FitnessConfig()
        self.grids = [dict() for _ in range(n_islands)]
        self.all: dict = {}
        self._rr = 0

    # ------------------------------------------------------------------ insertion
    def portfolio_B(self, exclude: str | None = None) -> np.ndarray:
        members = [self.all[i] for i in self.portfolio() if i != exclude]
        return np.array([m.B for m in members]) if members else np.zeros((0, 0))

    def score(self, ind: Individual) -> Individual:
        pb = self.portfolio_B(exclude=ind.id)
        f = refinability_fitness(ind.B, pb if pb.size else None, ind.runtime_s, self.fcfg)
        ind.F = f["F"]
        return ind

    def add(self, ind: Individual) -> bool:
        self.all[ind.id] = ind
        g = self.grids[ind.island]
        cur = g.get(ind.cell)
        if cur is None or self.all[cur].F < ind.F:
            g[ind.cell] = ind.id
            return True
        return False

    # ------------------------------------------------------------------ selection
    def select_parents(self, n: int, rng: np.random.Generator) -> list:
        out = []
        for _ in range(n):
            for _ in range(self.n_islands):
                g = self.grids[self._rr % self.n_islands]
                self._rr += 1
                if g:
                    cells = sorted(g)
                    out.append(self.all[g[cells[int(rng.integers(len(cells)))]]])
                    break
        return out

    def migrate(self, generation: int):
        if generation == 0 or generation % self.migrate_every:
            return
        bests = []
        for g in self.grids:
            ids = list(g.values())
            bests.append(max(ids, key=lambda i: self.all[i].F) if ids else None)
        for k, b in enumerate(bests):
            if b is None:
                continue
            src = self.all[b]
            dst = (k + 1) % self.n_islands
            clone = Individual(**{**asdict(src), "id": src.id + "@i%d" % dst, "island": dst})
            self.add(clone)

    # ------------------------------------------------------------------ portfolio / re-anchoring
    def portfolio(self, B0: np.ndarray | None = None) -> list:
        ids = [i for i, ind in self.all.items() if len(ind.B) and "@i" not in i]
        if not ids:
            return []
        B = np.array([self.all[i].B for i in ids], float)
        base = B0 if B0 is not None else B.max(0) + 1e-6
        return [ids[k] for k in greedy_prune(B, base, self.q)]

    def reanchor(self, new_B: dict):
        """After a bridge promotion: replace post-bridge costs and recompute every fitness."""
        for i, b in new_B.items():
            if i in self.all:
                self.all[i].B = list(b)
        for ind in self.all.values():
            self.score(ind)
        for g in self.grids:
            for cell in list(g):
                members = [i for i, ind in self.all.items() if ind.cell == cell and ind.island == self.grids.index(g)]
                if members:
                    g[cell] = max(members, key=lambda i: self.all[i].F)

    def to_json(self) -> str:
        return json.dumps({"islands": [{"|".join(map(str, c)): v for c, v in g.items()} for g in self.grids],
                           "programs": {i: {k: v for k, v in asdict(ind).items() if k != "source"} for i, ind in self.all.items()}},
                          default=str)
