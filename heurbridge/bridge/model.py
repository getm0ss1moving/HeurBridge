"""Bridge velocity network v_phi(x_tau, tau; c) (task T3.3).

Encoder MLP -> [GATv2 (4 heads) -> MLP -> global self-attention over macro nodes +
top-512 cluster nodes] x L -> decoder MLP -> velocity (N x 2), times movable_mask.
tau: sinusoidal embedding added to node features + FiLM in every block.
Positions: raw and 2D sinusoidal encodings of the current state x_tau.

Deviation from the task spec (T3.2 lists "x^h position" as a node feature): the velocity is
NOT conditioned on the source x^h by default (use_source=False).  Conditioned on x^h, each
source is a point mass and the ODE can only follow the conditional-mean direction, i.e. the
bridge degenerates into a regressor that averages symmetric elite modes (bridge_theory s.5).
Measured on the multimodal toy (tests/test_bridge.py): overlap 8% with x^h conditioning vs
0.1% without, against 61.5% for one-shot regression.  use_source=True remains as an ablation.
Sizes: small (L=4, width 144, ~1.1M params), base (L=8, width 240, ~6M params); the spec's
widths 128/256 give 0.9M/6.8M with this block design, so widths were set to match the parameter targets.
The decoder's last layer is zero-initialized: an untrained bridge is the identity map.
All operations are permutation-equivariant in the node order.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import torch
import torch.nn as nn
from torch_geometric.nn import GATv2Conv

from .graph import N_STATIC


@dataclass
class BridgeConfig:
    width: int = 144
    layers: int = 4
    heads: int = 4
    attn_heads: int = 4
    edge_dim: int = 32
    pe_freqs: int = 8
    t_dim: int = 64
    graph_dim: int = 9
    dropout: float = 0.0
    use_source: bool = False         # condition on x^h: ablation only (collapses to regression)

    @classmethod
    def small(cls):
        return cls(width=144, layers=4)          # ~1.14M parameters

    @classmethod
    def base(cls):
        return cls(width=240, layers=8, edge_dim=64, pe_freqs=12)   # ~6.0M parameters


def sinusoidal(t: torch.Tensor, dim: int) -> torch.Tensor:
    half = dim // 2
    freqs = torch.exp(-math.log(10000.0) * torch.arange(half, device=t.device, dtype=torch.float32) / half)
    a = t.float().unsqueeze(-1) * freqs * 1000.0
    return torch.cat([torch.sin(a), torch.cos(a)], dim=-1)


def pos_encoding(x: torch.Tensor, n_freq: int) -> torch.Tensor:
    """(..., 2) in ~[0,1] -> (..., 4*n_freq) sin/cos at frequencies 2^k * pi."""
    k = torch.arange(n_freq, device=x.device, dtype=x.dtype)
    a = x.unsqueeze(-1) * (math.pi * (2.0 ** k))          # (..., 2, F)
    return torch.cat([torch.sin(a), torch.cos(a)], dim=-1).flatten(-2)


def mlp(i, h, o, act=nn.GELU):
    return nn.Sequential(nn.Linear(i, h), act(), nn.Linear(h, o))


class Block(nn.Module):
    def __init__(self, cfg: BridgeConfig):
        super().__init__()
        W = cfg.width
        self.n1 = nn.LayerNorm(W)
        self.gnn = GATv2Conv(W, W // cfg.heads, heads=cfg.heads, edge_dim=cfg.edge_dim, add_self_loops=True,
                             fill_value="mean", dropout=cfg.dropout)
        self.n2 = nn.LayerNorm(W)
        self.ff = mlp(W, 2 * W, W)
        self.n3 = nn.LayerNorm(W)
        self.attn = nn.MultiheadAttention(W, cfg.attn_heads, dropout=cfg.dropout, batch_first=True)
        self.film = nn.Linear(W, 2 * W)
        nn.init.zeros_(self.film.weight)
        nn.init.zeros_(self.film.bias)

    def forward(self, h, edge_index, edge_attr, cond, attn_idx, B, N):
        W = h.shape[-1]
        gamma, beta = self.film(cond).chunk(2, dim=-1)                      # (B, W)
        hn = self.n1(h).view(B, N, W) * (1 + gamma.unsqueeze(1)) + beta.unsqueeze(1)
        h = h + self.gnn(hn.reshape(B * N, W), edge_index, edge_attr)
        h = h + self.ff(self.n2(h))
        if attn_idx is not None and attn_idx.numel() > 1:
            hb = h.view(B, N, W)
            a = self.n3(hb[:, attn_idx])
            out, _ = self.attn(a, a, a, need_weights=False)
            hb = hb.index_add(1, attn_idx, out)
            h = hb.reshape(B * N, W)
        return h


class BridgeNet(nn.Module):
    def __init__(self, cfg: BridgeConfig | None = None):
        super().__init__()
        self.cfg = cfg = cfg or BridgeConfig.small()
        W = cfg.width
        pe = 4 * cfg.pe_freqs
        in_dim = N_STATIC + 2 + pe + ((2 + pe) if cfg.use_source else 0)
        self.enc = mlp(in_dim, W, W)
        self.edge_enc = mlp(6, cfg.edge_dim, cfg.edge_dim)
        self.t_mlp = mlp(cfg.t_dim, W, W)
        self.g_mlp = mlp(cfg.graph_dim, W, W)
        self.blocks = nn.ModuleList([Block(cfg) for _ in range(cfg.layers)])
        self.n_out = nn.LayerNorm(W)
        self.dec = mlp(W, W, 2)
        nn.init.zeros_(self.dec[-1].weight)
        nn.init.zeros_(self.dec[-1].bias)

    def n_params(self) -> int:
        return sum(p.numel() for p in self.parameters())

    @staticmethod
    def _batched_edges(edge_index: torch.Tensor, B: int, N: int) -> torch.Tensor:
        """B disjoint copies of the graph (node b*N + i is node i of copy b)."""
        off = (torch.arange(B, device=edge_index.device) * N).repeat_interleave(edge_index.shape[1])
        return edge_index.repeat(1, B) + off

    def forward(self, x: torch.Tensor, tau: torch.Tensor, g: dict, xh: torch.Tensor | None = None) -> torch.Tensor:
        """x, xh: (B, N, 2) normalized positions; tau: (B,); g: BridgeGraph.tensors() (optionally augmented)."""
        B, N, _ = x.shape
        cfg = self.cfg
        feats = [g["static"].unsqueeze(0).expand(B, N, -1), x, pos_encoding(x, cfg.pe_freqs)]
        if cfg.use_source:
            src = x if xh is None else xh
            feats += [src, pos_encoding(src, cfg.pe_freqs)]
        h = self.enc(torch.cat(feats, dim=-1))
        temb = self.t_mlp(sinusoidal(tau, cfg.t_dim))                        # (B, W)
        ga = g["graph_attr"]
        cond = temb + self.g_mlp(ga if ga.dim() == 2 else ga.unsqueeze(0))   # (G,) shared or (B, G) per sample
        h = (h + temb.unsqueeze(1)).reshape(B * N, -1)
        E = g["edge_index"].shape[1]
        ei = self._batched_edges(g["edge_index"], B, N)
        ea = self.edge_enc(g["edge_attr"]).repeat(B, 1) if E else g["edge_attr"].new_zeros((0, cfg.edge_dim))
        for blk in self.blocks:
            h = blk(h, ei, ea, cond, g["attn"], B, N)
        v = self.dec(self.n_out(h)).view(B, N, 2)
        return v * g["movable"].view(1, N, 1)

    def export_config(self) -> dict:
        return asdict(self.cfg)
