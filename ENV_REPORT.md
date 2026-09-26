# ENV_REPORT — T0 environment and feasibility

**Status (2026-09-27): T0 run on the servers (224) through the encrypted workflow — see §6.** T0.1, T0.4 and
T0.6 pass on 224; T0.5 builds the environment but CUDA cannot initialize on 224 (host GPU fault, §6); T0.3 found
no complete recent OpenROAD in conda (a full prebuilt one awaits approval). **Track A proceeds; Track B waits for
a complete OpenROAD.**

## 1. Local machine (development)

| Item | Value |
|---|---|
| OS | macOS (Darwin 25.5, arm64) |
| Python | 3.11.16 venv `.venv/` (uv); numpy 2.4, scipy 1.17, torch 2.14 (CPU), torch_geometric 2.8 |
| Tests | `.venv/bin/python -m pytest -q tests` |
| Docker | colima (Virtualization.Framework, aarch64) with `efabless/openlane:master-arm64v8` |
| EDA tools in that image | OpenROAD `b16bda7e82721d10566ff7e2b68f1ff0be9f9e38`, Yosys, Magic, KLayout, Netgen |
| HA-PR harness | English copy `heura_repro_en/eda` next to the repo, `$HEURA_EDA_BASE` (the task list's `papers/heura_repro` path no longer exists) |

**T0.1 (local): PASS** — `SMOKE_TEST_PASS`; 222 v2 records, control coverage 46/46; `VALIDATE_REPLAY_V2_PASS`;
dataset 46 decisions / 176 samples / 0 errors.

## 2. OpenROAD command probe (T0.3)

`scripts/server/probe_openroad.tcl`, run in the local OpenLane image (full output:
`reports/env/openroad_probe_local_openlane_b16bda7e.txt`):

| Command | Available | Required flags found |
|---|---|---|
| `rtl_macro_placer`, `macro_placement`, `place_macro` | yes, yes, yes | — |
| `global_placement` | yes | `-skip_initial_place -incremental -routability_driven -timing_driven -overflow` (all) |
| `detailed_placement`, `check_placement` | yes | — |
| `estimate_parasitics` | yes | `-placement -global_routing` (all) |
| `report_wns`, `report_tns` | yes | — |
| `global_route` | yes | `-congestion_iterations -congestion_report_file` (all) |
| `set_global_routing_region_adjustment`, `set_global_routing_layer_adjustment` | yes | — |
| `detailed_route`, `write_db`, `read_db`, `write_guides`, `extract_parasitics` | yes | — |

Pending on 224: the same probe for OpenROAD 2022 (`eda/tools/openroad/bin/openroad`) and for the conda
`litex-hub::openroad` install in `/data/dzy/heura_repr/tools/openroad_new/` (`scripts/server/install_openroad.sh`).

## 3. Benchmarks (T0.4)

Downloaded on the Mac (fallback path "download on the Mac, then rsync"); sha256 manifests in `configs/manifests/`.

| Suite | Designs | Source | Archive sha256 | Manifest |
|---|---|---|---|---|
| ICCAD04 IBM-MSwPins, bookshelf | ibm01–ibm18 | vlsicad.eecs.umich.edu/BK/ICCAD04bench | `fd7e6d0b…538aed` | `ibm_bookshelf.sha256` (108 files) |
| ICCAD04 IBM-MSwPins, LEF/DEF | ibm01–ibm18 (3 routing layers, tracks, GCell grid) | same | `59f537b9…15aab5` | `ibm_lefdef.sha256` (72 files) |
| ISPD2005 | adaptec1–4, bigblue1–4 | Google Drive copy linked by lamda-bbo/BBOPlace-Bench (originals offline) | `bd8d44cc…672aa72` | `ispd2005.sha256` (80 files) |
| ORFS Nangate45 macro designs | ariane133, ariane136, bp_be_top, bp_fe_top, swerv_wrapper, black_parrot, bp_multi_top, bp_quad, mempool_group, tinyRocket, cva6 | OpenROAD-flow-scripts sparse checkout @ `e2e6b166` (2026-09-24) | git commit | `third_party/OpenROAD-flow-scripts` |
| sky130_small | gcd, aes, jpeg, ibex | HA-PR harness on 224 | — | — |
| ISPD07 GR, ISPD2024 GR | optional | not fetched yet | — | — |

ISPD2005 integrity: node/net/pin/terminal counts in the file headers equal the published suite statistics
(adaptec1: 211,447 nodes, 221,142 nets, 944,053 pins; …; bigblue4: 2,177,353 / 2,229,886 / 8,900,078).
IBM sizes: ibm01 12,752 nodes / 14,111 nets … ibm18 210,613 / 201,920.

Loader checks (T1.1): load → write → load is the identity on all 26 bookshelf designs (IBM + ISPD2005) and on the 18 IBM LEF/DEF designs (`reports/T1_roundtrip_*.json`). Pin geometry agrees exactly with OpenROAD's (`reports/V3_pin_geometry_vs_openroad.json`).

## 4. Python/GPU, reference code, LLM (T0.5, T0.6)

| Item | Status |
|---|---|
| `hb` env on 224/227 | script ready (`scripts/server/setup_env.sh`: py3.11, CUDA wheel chosen from the driver's CUDA version, PyG, pymetis/kahypar if installable) |
| GPU smoke test | script ready (`scripts/server/gpu_smoke.py`, BridgeNet-small 1.13M params, 20k nodes/120k edges, target < 1 s/step); local CPU: 1.8 s |
| GPU choice | default 224 GPU 1 (task spec B.3), to be confirmed by `nvidia-smi` |
| ChipDiffusion | cloned (`vint-1/chipdiffusion` @ `6973e90`); **no licence file** → private evaluation only, not vendored; checkpoints (Large+v2) and IBM DEF/LEF are Google Drive folders; clustered evaluation needs hMETIS binaries. Our bridge uses its own backbone (T3.3 fallback), so no ChipDiffusion weights are loaded. |
| DREAMPlace | cloned (`limbo018/DREAMPlace` @ `6627f33`, BSD-3); build on the server (Linux + CUDA) for Track A |
| DeepSeek | client + ledger ready (`heurbridge/evolve/llm.py`, offline tests pass); **no key locally**; server environment not yet checked |

## 5. Track decision (provisional)

- **Track B** requires a recent OpenROAD on 224 and ariane133 (ORFS Nangate45, fakeram) running to detailed
  routing. Every required command/flag exists in recent OpenROAD builds (probe above), so Track B is likely;
  it is confirmed only after `install_openroad.sh` + an ariane133 run on 224.
- **Track A** (bookshelf + DREAMPlace) is prepared in parallel: IBM and ISPD2005 are loaded and hashed.
- For bookshelf designs there are no liberty/timing files: `J` would lack the TNS and power terms. Proposed:
  IBM LEF/DEF designs get a routing-level fidelity via OpenROAD (global placement + `global_route`), and their
  cost uses the available terms with TNS/power marked `unchecked` (needs your confirmation, see HANDOFF).


## 5b. Local Track-B development flow (revised 2026-09-26)

The OpenLane image's OpenROAD (b16bda7e, early 2024) + Yosys 0.38 cannot run current ORFS (no `make`, older
commands), so `heurbridge/eval/miniflow.py` implements the ORFS stage sequence with verified commands only,
configured from the design's and the platform's `config.mk` with ORFS/Make semantics:
hierarchical Yosys synthesis (dont-use cells) -> floorplan (utilization, aspect, core margin 1.0, platform
tracks, IO exclusions) -> M1 = `rtl_macro_placer` -> **f1**: our macro placement (FIRM) -> tapcells ->
power grid (supply block pins dropped, see below) -> routability + timing-driven GP at the platform density
(0.30) -> port buffering, `repair_design`, tie cells -> DP -> placement-parasitics timing and power ->
`global_route -allow_congestion` (30 iterations). **f2** (one process per stage, as ORFS): CTS ->
`repair_timing` -> GRT + detailed route + fill -> OpenRCX + STA.

| Step on nangate45/bp_fe_top (11 fakeram macros) | Result |
|---|---|
| Synthesis / floorplan / M1 | 10 s / 3 s / 174 s |
| f1 with M1, 3 runs (6 threads) | bit-identical: GR WL 1,832,439 um, overflow 0, setup WNS -2.336 ns / TNS -113.5 ns (pre-CTS), hold +0.096 ns, 0.151 W; 109 s |
| f2 with M1 (smoke test, 2 threads) | 782 s (CTS 113 s, repair_timing 148 s, GRT + DRT + fill 506 s, RCX + STA 14 s): DRC 0, detailed WL 1,618,701 um, 264,348 vias, setup WNS -1.979 ns / TNS -57.8 ns, hold +0.096 ns, 0.169 W (CTS 4,774 sinks / 396 leaf buffers; repair_timing left 314 setup endpoints) |

Local-build defects worked around (each bisected on bp_fe_top; details in CHANGELOG 0.10.x):
`estimate_parasitics -global_routing` fails at random (bad_alloc exit / segfault / OOM kill) -> f1 timing from
placement parasitics; `report_power` segfaults when pdngen's VDD/VSS block pins exist -> pins dropped after
pdngen; `repair_timing` after CTS in the same process segfaults -> one process per f2 stage; a deterministic
gpl assertion on some macro layouts and PDN-0179 on layouts with narrow edge channels are recorded as named
tool failures. Results depend on the thread count, so a campaign fixes it (6).

This is a development path; the pre-registered experiments use ORFS with a current OpenROAD on the server.

## 6. Servers (T0 on 224, 2026-09-27)

Key-only SSH works on 6 of the 12 lab ports. The lab login is shared, so everything of ours on the servers is
encrypted at rest (`scripts/hbv.py`, `docs/SERVER_RUNBOOK.md`): ciphertext-only vault, key on the Mac, jobs in a RAM
workspace that is wiped at exit. The account's home directory is on a NAS whose quota is exhausted: all tool caches
go to local disks.

| Node | CPU / RAM | GPUs | CUDA from a job | Storage for us |
|---|---|---|---|---|
| 224 (EDA node) | 64 cores / 125 GB | 3x RTX 3090, GPU 0 "Unknown Error" | **fails** (`cuInit` error 3 on every device: the faulty GPU breaks the driver; needs an admin) | `/data` 3.6 TB, 300 GB free |
| 227 | 64 / 125 GB | 3x RTX 3090, GPU 0 faulty | fails the same way | `/data` not writable; `/tmp` |
| 225 | 24 / 125 GB | 4x RTX 3090, idle | works (driver 510.54) | `/data` 99 % full — **use needs approval (A.2)** |
| 231 | — | 5x RTX 4090, all busy | works | `/tmp` 5 GB free — **use needs approval (A.2)** |
| 232 | — | — | host does not answer commands | — |
| 234 | — | — | NVIDIA driver not running | `/tmp` |

| Item | Result on 224 |
|---|---|
| T0.1 inherit (on a copy of `eda/`) | **PASS**: `SMOKE_TEST_PASS`; v2 = 222, control coverage 46/46; `VALIDATE_REPLAY_V2_PASS`; 46 decisions / 176 samples / 0 errors |
| T0.2 probe | Ubuntu 20.04, Python 3.8 system, gcc 9.4, cmake; no Docker access (not in the `docker` group; Docker Hub unreachable); no conda on PATH; GitHub, PyPI, conda (TUNA mirror) and the DeepSeek API reachable |
| T0.3 OpenROAD 2022 (HA-PR binary) | runs with its bundled libraries; `rtl_macro_placer` yes, `place_macro` no, `global_route -congestion_report_file` no |
| T0.3 conda (litex-hub) | unpinned: 2022-03 build `f12e2f47` (no `place_macro`). Pinned `2.0-12381-g01bba3695` (2024-03, needs Anaconda `main` before conda-forge): every GP/GR/DRT/RCX command and flag, but **no `rtl_macro_placer` and no `place_macro`**. Yosys 0.38+92. |
| T0.3 candidate | prebuilt `openroad_2.0-17598-ga008522d8_amd64-ubuntu-20.04.deb` (2024-12, Precision Innovations, 53 MB), unpackable without root — waiting for approval to download |
| T0.4 benchmarks | IBM bookshelf + LEF/DEF, ISPD2005 and the ORFS checkout uploaded (public data, plaintext); **all 260 files match** the sha256 manifests |
| T0.5 env `hb` | Python 3.11, torch 2.7.1+cu118, PyG 2.8.0, pymetis, kahypar. GPU smoke test **FAIL** on 224 (CUDA cannot initialize; CPU fallback 8.1 s/step) |
| T0.6 LLM | **PASS**: DeepSeek reachable with the lab key (read by the client from the key file); models `deepseek-flash`, `deepseek-v4-pro`; the old names `deepseek-reasoner` / `deepseek-chat` are answered by `deepseek-flash` |

**Track decision.** Track A (bookshelf, HB-GP as the f1 stand-in; DREAMPlace not built yet) proceeds on 224's CPUs.
Track B needs an OpenROAD with Hier-RTLMP (M1) and ORFS-compatible commands: the conda builds lack them; the
prebuilt 2024-12 package is the next step (approval pending), a source build the fallback.
