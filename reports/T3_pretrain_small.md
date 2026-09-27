# T3.4 pretraining (warm start): pretrain_small

| Field | Value |
|---|---|
| Report | T3_pretrain_small |
| Date | 2026-09-27 18:30 |
| Node | 225 (RTX 3090, GPU 0); thinklab-105-225 |
| Track | Track-independent (synthetic circuits, heurbridge.core.synth) |
| Tool versions | PyTorch 2.6.0+cu118, bf16 autocast |
| HeurBridge version / git | 0.11.0 / b443316b08795e4e5895b5eebc06d223edf9f49f+dirty (b443316-dirty-20260927134552) |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v1_2026-09-25 |
| Feeds gate | T3.4 (warm start for T3.7); no gate |
| Pre-registered test | - |
| alpha-ledger entry | - |
| Status of the claim | no claim (development / descriptive run) |

## Sample sizes

200000 steps x batch 64; stage 1: 100000:200 circuits (objects); stage 2: 5000:1000 from step 150500

## Results

Checkpoint `pretrain_small/pretrain_small.pt`, sha256 `6a5ee4b82249eab058c812cf207f4bd8368cea35cd2d35dc3dc53be8cb535bc0` (200000 steps).

Throughput: 0.048 s/step in stage 1, 0.106 s/step in stage 2; total 3.47 h.

| step | stage | loss | flow-matching term | overlap term | elapsed h |
|---|---|---|---|---|---|
| 500 | 1 | 0.2494 | 0.2432 | 0.0625 | 0.01 |
| 20000 | 1 | 0.1200 | 0.1156 | 0.0432 | 0.26 |
| 40000 | 1 | 0.1103 | 0.1070 | 0.0331 | 0.53 |
| 60000 | 1 | 0.1091 | 0.1062 | 0.0292 | 0.81 |
| 80000 | 1 | 0.1064 | 0.1038 | 0.0263 | 1.06 |
| 100000 | 1 | 0.1063 | 0.1037 | 0.0267 | 1.33 |
| 120000 | 1 | 0.1034 | 0.1012 | 0.0216 | 1.59 |
| 140000 | 1 | 0.1019 | 0.0997 | 0.0216 | 1.86 |
| 160000 | 2 | 0.0953 | 0.0810 | 0.1432 | 2.28 |
| 180000 | 2 | 0.0913 | 0.0785 | 0.1284 | 2.88 |
| 200000 | 2 | 0.0892 | 0.0766 | 0.1265 | 3.47 |

## Failures (by name, counted as +inf in statistics)

none

## Exact commands

```bash
python scripts/pretrain_bridge.py --steps 200000 --batch 64 --stage1 100000:200 --stage2 5000:1000 --model small --lr 0.0002 --workers 8 --device cuda --out checkpoints/pretrain_small --log-every 500 --save-every 10000 --seed 0 --resume True
```

## Notes

Loss = flow-matching (area-weighted velocity residual) + 0.1 x overlap penalty of the extrapolated endpoint (T3.5, sigma 0.01, logit-normal tau), noise source uniform on the canvas. Values are 500-step means of the training loss; there is no validation set for synthetic pretraining (T3.6 validation starts with Algorithm R on real designs).
