# Bridge training targets: audit

| Field | Value |
|---|---|
| Report | bridge_target_audit |
| Data | round-0 pair shards of Algorithm R on Track A (runs/remote/algR_trackA2/checkpoints/algR_trackA/round0/pairs/round0); archive runs/tmp_audit/archive_A0_trackA |
| Status of the claim | development / descriptive (no claim) |

Tool = DREAMPlace's own mixed-size macro placement, J = 0.45 by construction. A target at or below the tool: J <= 0.4505.

| design | pairs | target J min | median | max | share of pairs with target <= tool | share whose target is the tool's layout | target programs (pairs) |
|---|---|---|---|---|---|---|---|
| ibm01 | 128 | 0.4500 | 0.5170 | 0.5186 | 0.41 | 0.41 | LS (75), BASELINE (53) |
| ibm02 | 128 | 0.1636 | 0.1640 | 0.1640 | 1.00 | 0.00 | M6.v0 (92), LS (36) |
| ibm03 | 128 | 0.4500 | 0.4998 | 0.5015 | 0.05 | 0.05 | M3.v2 (71), M6.v0 (48), BASELINE (6), LS (3) |
| ibm04 (validation) | 128 | 0.4497 | 0.4593 | 0.4734 | 0.30 | 0.30 | M3.v2 (47), BASELINE (38), LS (36), M6.v1 (7) |
| ibm06 (validation) | 128 | 0.4254 | 0.4254 | 0.4256 | 1.00 | 0.00 | LS (100), M6.v0 (28) |
| ibm07 | 128 | 0.4497 | 0.4526 | 0.4791 | 0.13 | 0.13 | LS (55), M3.v2 (54), BASELINE (17), M6.v0 (2) |
| ibm09 | 128 | 0.4500 | 0.4559 | 0.4722 | 0.17 | 0.17 | M6.v0 (69), LS (30), BASELINE (22), M3.v2 (7) |
| ibm10 | 104 | 0.4498 | 0.4498 | 0.5984 | 0.54 | 0.54 | BASELINE (56), LS (32), M6.v1 (16) |
| ibm11 | 128 | 0.4493 | 0.5057 | 0.5204 | 0.27 | 0.27 | M3.v2 (38), BASELINE (35), LS (33), M3.v1 (19) |
| ibm13 | 128 | 0.4498 | 0.4498 | 0.5549 | 0.52 | 0.52 | BASELINE (66), LS (62) |
| ibm14 | 120 | 0.4499 | 0.5819 | 0.6041 | 0.23 | 0.23 | M6.v0 (51), M6.v1 (34), BASELINE (27), LS (8) |
| ibm15 | 128 | 0.4501 | 0.5188 | 0.5291 | 0.38 | 0.38 | BASELINE (49), LS (46), M3.v1 (23), M6.v2 (10) |
| ibm16 | 128 | 0.4500 | 0.4842 | 0.4879 | 0.47 | 0.47 | BASELINE (60), M6.v2 (37), LS (31) |
| ibm17 | 104 | 0.4500 | 0.4829 | 0.4829 | 0.32 | 0.32 | LS (71), BASELINE (33) |
| ibm18 | 128 | 0.4503 | 0.4644 | 0.4644 | 0.48 | 0.48 | LS (67), BASELINE (61) |

Training designs (13): 1608 pairs; target at or below the tool 613 (0.38); target is the tool's layout 485 (0.30).

