"""alpha-spending ledger (task T7.3, proposal Proposition 5).

Every promotion test j of a campaign (program, bridge checkpoint, skill edit)
runs at alpha_j = alpha * 2^-j, so the campaign-wise probability of promoting any
non-improving artifact is <= sum_j alpha_j < alpha.  A test is invalid without a
ledger entry: ``reserve`` must be called *before* the data are looked at, and
``record`` closes the entry with the outcome.
"""

from __future__ import annotations

import fcntl
import json
import time
from pathlib import Path


class AlphaLedger:
    def __init__(self, path: str | Path, campaign: str, alpha: float = 0.05):
        self.path, self.campaign, self.alpha = Path(path), campaign, float(alpha)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _entries(self) -> list:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text().splitlines():
            if line.strip():
                e = json.loads(line)
                if e.get("campaign") == self.campaign:
                    out.append(e)
        return out

    def reserve(self, kind: str, artifact: str, test: str, meta: dict | None = None) -> dict:
        """Allocate the next alpha_j.  Returns the entry (with 'ledger_id' and 'alpha_j')."""
        with open(self.path, "a+") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            fh.seek(0)
            n = sum(1 for line in fh.read().splitlines()
                    if line.strip() and json.loads(line).get("campaign") == self.campaign
                    and json.loads(line).get("event") == "reserve")
            j = n + 1
            entry = {"event": "reserve", "campaign": self.campaign, "j": j, "alpha": self.alpha,
                     "alpha_j": self.alpha * 2.0 ** (-j), "kind": kind, "artifact": artifact, "test": test,
                     "meta": meta or {}, "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
                     "ledger_id": "%s#%d" % (self.campaign, j)}
            fh.write(json.dumps(entry) + "\n")
            fh.flush()
            fcntl.flock(fh, fcntl.LOCK_UN)
        return entry

    def record(self, entry: dict, p_value: float, n: int, extra: dict | None = None) -> dict:
        promoted = bool(p_value <= entry["alpha_j"])
        out = {"event": "result", "campaign": self.campaign, "ledger_id": entry["ledger_id"], "j": entry["j"],
               "alpha_j": entry["alpha_j"], "p": float(p_value), "n": int(n), "promoted": promoted,
               "extra": extra or {}, "time": time.strftime("%Y-%m-%dT%H:%M:%S")}
        with open(self.path, "a") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            fh.write(json.dumps(out) + "\n")
            fcntl.flock(fh, fcntl.LOCK_UN)
        return out

    def spent(self) -> float:
        return sum(e["alpha_j"] for e in self._entries() if e.get("event") == "reserve")

    def summary(self) -> dict:
        es = self._entries()
        res = [e for e in es if e.get("event") == "result"]
        return {"campaign": self.campaign, "alpha": self.alpha, "tests": sum(e.get("event") == "reserve" for e in es),
                "spent": self.spent(), "promoted": sum(e["promoted"] for e in res),
                "open": sorted({e["ledger_id"] for e in es if e.get("event") == "reserve"} - {e["ledger_id"] for e in res})}
