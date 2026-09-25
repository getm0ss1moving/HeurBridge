"""T0.5 GPU smoke test: a ~1M-parameter GNN forward+backward on a 20k-node graph in under 1 s.

  CUDA_VISIBLE_DEVICES=1 python gpu_smoke.py     -> prints GPU_SMOKE_PASS / GPU_SMOKE_FAIL with timings
Uses the HeurBridge BridgeNet (small) on a random 20k-node, 120k-edge graph, batch 4.
"""

import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from heurbridge.bridge.model import BridgeConfig, BridgeNet  # noqa: E402


def main(n=20000, e=120000, B=4, reps=5):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(0)
    m = BridgeNet(BridgeConfig.small()).to(dev)
    g = {"static": torch.rand(n, 15, device=dev), "edge_index": torch.randint(0, n, (2, e), device=dev),
         "edge_attr": torch.rand(e, 6, device=dev), "graph_attr": torch.rand(9, device=dev),
         "attn": torch.arange(0, 600, device=dev), "movable": torch.ones(n, device=dev)}
    x = torch.rand(B, n, 2, device=dev)
    opt = torch.optim.AdamW(m.parameters(), 1e-4)
    times = []
    for r in range(reps + 1):
        if dev == "cuda":
            torch.cuda.synchronize()
        t = time.time()
        with torch.autocast(device_type=dev, dtype=torch.bfloat16, enabled=dev == "cuda"):
            v = m(x, torch.rand(B, device=dev), g)
            loss = (v.float() ** 2).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
        if dev == "cuda":
            torch.cuda.synchronize()
        if r:
            times.append(time.time() - t)
    med = sorted(times)[len(times) // 2]
    mem = torch.cuda.max_memory_allocated() / 2 ** 30 if dev == "cuda" else 0.0
    name = torch.cuda.get_device_name() if dev == "cuda" else "cpu"
    ok = med < 1.0 and dev == "cuda"
    print("%s device=%s params=%.2fM nodes=%d edges=%d batch=%d median_step=%.3fs peak_mem=%.2fGB" % (
        "GPU_SMOKE_PASS" if ok else "GPU_SMOKE_FAIL", name, m.n_params() / 1e6, n, e, B, med, mem))


if __name__ == "__main__":
    main()
