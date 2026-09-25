"""Report generation with the mandatory fields of task T7.4.

Every report states node, date, tool versions, track, metric-convention versions, sample sizes, all
failures by name, the gate it feeds and the exact command lines.  ``render`` refuses to produce a report
with an empty mandatory field, and a report may only claim an improvement when its gate passed
(red line A.2 "Claims")."""

from __future__ import annotations

import time
from pathlib import Path

from . import __version__
from .meta import git_sha

TEMPLATE = Path(__file__).resolve().parent.parent / "reports" / "templates" / "experiment_report.md"
MANDATORY = ("title", "report_id", "node", "track", "tools", "metric_conventions", "gate", "samples", "failures",
             "commands")
METRIC_CONVENTIONS = "timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v1_2026-09-25"


def public_paths(text: str) -> str:
    """Reports go to a public repository: the repo root becomes '.', the home directory '~'."""
    from .paths import REPO_ROOT
    return text.replace(str(REPO_ROOT), ".").replace(str(Path.home()), "~")


def render(fields: dict, gate_passed: bool | None, out: str | Path | None = None) -> str:
    f = {"date": time.strftime("%Y-%m-%d %H:%M"), "version": __version__, "git_sha": git_sha(),
         "metric_conventions": METRIC_CONVENTIONS, "test": "-", "alpha_ledger_id": "-", "results": "", "notes": ""}
    f.update(fields)
    missing = [k for k in MANDATORY if not str(f.get(k, "")).strip()]
    if missing:
        raise ValueError("report is missing mandatory fields: %s" % missing)
    if gate_passed is None:
        f["claim_status"] = "no claim (development / descriptive run)"
    else:
        f["claim_status"] = "gate PASSED: the pre-registered claim may be stated" if gate_passed else \
            "gate FAILED: negative result, no improvement may be claimed"
    text = public_paths(TEMPLATE.read_text().format(**f))
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text)
    return text
