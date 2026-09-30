"""Cell-stage predictor for the look-ahead (sketch redesign S2, 30 Sep 2026).

Given a committed macro layout, predict where the placer puts each standard-cell cluster: its centroid and its
spread.  One forward pass of the bridge's encoder at tau = 0 on the macro layout with the clusters at their quadratic
placement (``sample.source_nodes``), then two heads on every node (only the cluster rows are used):

  centroid  quadratic position + shift            (the shift head is the bridge's decoder: zero at initialization)
  spread    log var_x, log var_y, atanh(rho)       (the second moments of ``heurbridge.bridge.lookahead``)

No transport and no sampling: the prediction is deterministic.  The encoder can start from a bridge checkpoint (same
BridgeConfig).  Loss: area-weighted squared centroid error + lam_cov x the area-weighted squared error of the spread
terms, with cluster areas as weights (the graph's cluster loss weights are proportional to area).
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn

from .graph import KIND_CL
from .model import BridgeConfig, BridgeNet, mlp

VAR_FLOOR = 1e-6
RHO_CAP = 0.95


def spread_targets(cov: torch.Tensor, floor: float = VAR_FLOOR) -> torch.Tensor:
    """(..., 3) second moments (var_x, var_y, cov_xy) -> (log var_x, log var_y, atanh rho)."""
    vx, vy = cov[..., 0].clamp_min(floor), cov[..., 1].clamp_min(floor)
    rho = (cov[..., 2] / torch.sqrt(vx * vy)).clamp(-RHO_CAP, RHO_CAP)
    return torch.stack([torch.log(vx), torch.log(vy), torch.atanh(rho)], dim=-1)


def spread_moments(s: torch.Tensor) -> torch.Tensor:
    """Inverse of ``spread_targets``: (log var_x, log var_y, atanh rho) -> (var_x, var_y, cov_xy)."""
    vx, vy = torch.exp(s[..., 0]), torch.exp(s[..., 1])
    return torch.stack([vx, vy, torch.tanh(s[..., 2]) * torch.sqrt(vx * vy)], dim=-1)


class LookaheadNet(BridgeNet):
    def __init__(self, cfg: BridgeConfig | None = None, init_var: float = 1e-3):
        super().__init__(cfg)
        W = self.cfg.width
        self.spread = mlp(W, W, 3)
        nn.init.zeros_(self.spread[-1].weight)
        with torch.no_grad():
            self.spread[-1].bias.copy_(torch.tensor([math.log(init_var), math.log(init_var), 0.0]))

    def predict(self, x: torch.Tensor, g: dict) -> tuple[torch.Tensor, torch.Tensor]:
        """x: (B, N, 2) node positions (macros committed, clusters quadratic) -> centroids (B, N, 2) (non-cluster
        rows unchanged) and spread terms (B, N, 3)."""
        B, N, _ = x.shape
        h = self.n_out(self.encode(x, torch.zeros(B, device=x.device), g))
        cl = (g["kind"] == KIND_CL).view(1, N, 1).to(x.dtype)
        return x + self.dec(h).view(B, N, 2) * cl, self.spread(h).view(B, N, 3)


def lookahead_loss(model: LookaheadNet, g: dict, x: torch.Tensor, y_pos: torch.Tensor, y_cov: torch.Tensor,
                   lam_cov: float = 0.1) -> tuple[torch.Tensor, dict]:
    """x (B, N, 2); y_pos (B, C, 2) placed cluster centroids; y_cov (B, C, 3) their second moments."""
    pos, sp = model.predict(x, g)
    cl = g["kind"] == KIND_CL
    a = g["area_w"][cl].view(1, -1)
    e_pos = ((pos[:, cl] - y_pos) ** 2).sum(-1)
    e_cov = ((sp[:, cl] - spread_targets(y_cov)) ** 2).sum(-1)
    loss = ((a * (e_pos + lam_cov * e_cov)).sum(-1) / a.sum()).mean()
    with torch.no_grad():
        rms = torch.sqrt((a * e_pos).sum(-1) / a.sum())
        rms_quad = torch.sqrt((a * ((x[:, cl] - y_pos) ** 2).sum(-1)).sum(-1) / a.sum())
    return loss, {"loss": float(loss.detach()), "rms": rms.cpu(), "rms_quad": rms_quad.cpu()}


def from_bridge(path: str, device: str = "cpu") -> LookaheadNet:
    """A LookaheadNet whose encoder and shift head start from a bridge checkpoint's EMA weights."""
    z = torch.load(path, map_location=device, weights_only=False)
    m = LookaheadNet(BridgeConfig(**z["model_config"]))
    missing, unexpected = m.load_state_dict(z["ema"], strict=False)
    assert not unexpected and all(k.startswith("spread.") for k in missing), (missing, unexpected)
    return m.to(device)
