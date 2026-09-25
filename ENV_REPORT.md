# ENV_REPORT — T0 environment and feasibility

**Status (2026-09-25): DRAFT — local part complete, server part blocked.** Server probing (T0.2), the recent
OpenROAD install on 224 (T0.3), the `hb` GPU env (T0.5) and the server-side T0.1 are waiting for SSH key
authorization (password login is not used by the agent). All server scripts are ready in `scripts/server/`.
**Track decision: provisional (see §5).**

## 1. Local machine (development)

| Item | Value |
|---|---|
| OS | macOS (Darwin 25.5, arm64) |
| Python | 3.11.16 venv `.venv/` (uv); numpy 2.4, scipy 1.17, torch 2.14 (CPU), torch_geometric 2.8 |
| Tests | `.venv/bin/python -m pytest -q tests` |
| Docker | colima (Virtualization.Framework, aarch64) with `efabless/openlane:master-arm64v8` |
| EDA tools in that image | OpenROAD `b16bda7e82721d10566ff7e2b68f1ff0be9f9e38`, Yosys, Magic, KLayout, Netgen |
| HA-PR harness | `/Users/duanzeyu/Desktop/heura_repro_en/eda` (English copy; the task list's `papers/heura_repro` path no longer exists) |

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

Loader checks (T1.1): bookshelf load → write → load is the identity on ibm01, ibm18 and adaptec1 (load 0.1–1.2 s).

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

## 6. Pending (blocked on server access)

1. T0.1 on 224 (`scripts/server/t0_inherit.sh`).
2. T0.2 probe on 224 and 227 (`scripts/server/probe_env.sh` → `reports/env/probe_<port>.json`).
3. T0.3 install + probe of the new OpenROAD; OpenROAD 2022 probe; ariane133 to detailed route.
4. T0.5 `hb` env, GPU smoke test, ChipDiffusion ibm01 reproduction, DREAMPlace build.
5. T0.6 DeepSeek 16-token self-test (needs `DEEPSEEK_LAB_API_KEY` in the server environment).
