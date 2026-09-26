"""DeepSeek client with key fallback and a JSONL budget ledger (task T0.6).

Keys come only from the environment (red line A.2): DEEPSEEK_LAB_API_KEY first,
then DEEPSEEK_API_KEY, DEEPSEEK_API_KEY_2, ...  A variable may hold several
comma-separated keys; whitespace and trailing commas are stripped.  Keys are
never logged: the ledger records the key's index only.

DEEPSEEK_API_KEY_FILE names a KEY=VALUE file (the lab's key file, mode 0600) that the client reads
itself, so the key never enters a process environment (/proc/<pid>/environ is readable by every login of
the shared lab account); API_KEY and the variable names above are accepted there.

Ledger (logs/llm_ledger.jsonl), one line per call:
  time, model, tokens_in, tokens_out, reasoning_tokens, purpose, program_id,
  budget_scope, key_index, latency_s, status
Budget: calls are counted per ``budget_scope`` (e.g. "M/ibm+ispd05"); a call that
would exceed 110% of the scope's budget raises BudgetExceeded before any request.
"""

from __future__ import annotations

import fcntl
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from ..paths import logs_dir

DEFAULT_BASE = "https://api.deepseek.com"
MODELS = {"reasoning": "deepseek-reasoner", "chat": "deepseek-chat"}
KEY_VARS = ("DEEPSEEK_LAB_API_KEY", "DEEPSEEK_API_KEY") + tuple("DEEPSEEK_API_KEY_%d" % i for i in range(2, 6))


class BudgetExceeded(RuntimeError):
    pass


class NoAPIKey(RuntimeError):
    pass


def _key_file_vars(path: str) -> dict:
    """KEY=VALUE pairs of a key file (``export`` prefixes and quotes allowed); values are never logged."""
    out = {}
    try:
        text = Path(path).read_text()
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = (line[7:] if line.startswith("export ") else line).partition("=")
        out[name.strip()] = value.strip().strip("'\"")
    return out


def load_keys(env=None) -> list:
    env = os.environ if env is None else env
    sources = [env]
    if env.get("DEEPSEEK_API_KEY_FILE"):
        fv = _key_file_vars(env["DEEPSEEK_API_KEY_FILE"])
        sources.append({**fv, "DEEPSEEK_LAB_API_KEY": fv.get("DEEPSEEK_LAB_API_KEY") or fv.get("API_KEY", "")})
    keys = []
    for src in sources:
        for var in KEY_VARS:
            raw = src.get(var)
            if not raw:
                continue
            for k in raw.split(","):
                k = k.strip().rstrip(",").strip()
                if k and k not in keys:
                    keys.append(k)
    return keys


@dataclass
class Reply:
    text: str
    reasoning: str
    model: str
    tokens_in: int
    tokens_out: int
    reasoning_tokens: int
    latency_s: float


class LLMClient:
    def __init__(self, ledger_path: str | Path | None = None, base_url: str | None = None,
                 budgets: dict | None = None, hard_stop: float = 1.10, timeout_s: float = 600.0):
        self.keys = load_keys()
        self.base = (base_url or os.environ.get("DEEPSEEK_BASE_URL") or DEFAULT_BASE).rstrip("/")
        self.ledger = Path(ledger_path) if ledger_path else logs_dir() / "llm_ledger.jsonl"
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.budgets = budgets or {}
        self.hard_stop = hard_stop
        self.timeout = timeout_s
        self._key_i = 0

    # ------------------------------------------------------------------ ledger
    def _log(self, rec: dict) -> None:
        with open(self.ledger, "a") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            fh.write(json.dumps(rec) + "\n")
            fcntl.flock(fh, fcntl.LOCK_UN)

    def calls_used(self, scope: str) -> int:
        if not self.ledger.exists():
            return 0
        n = 0
        with open(self.ledger) as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    if r.get("budget_scope") == scope and r.get("status") == "ok":
                        n += 1
        return n

    def _check_budget(self, scope: str | None) -> None:
        if not scope or scope not in self.budgets:
            return
        cap = int(self.budgets[scope] * self.hard_stop)
        used = self.calls_used(scope)
        if used + 1 > cap:
            raise BudgetExceeded("scope %s: %d calls used, hard stop %d" % (scope, used, cap))

    # ------------------------------------------------------------------ requests
    def _post(self, path: str, payload: dict, key: str) -> dict:
        req = urllib.request.Request(self.base + path, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read().decode())

    def _get(self, path: str, key: str) -> dict:
        req = urllib.request.Request(self.base + path, headers={"Authorization": "Bearer " + key})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())

    def chat(self, messages: list, model: str = MODELS["reasoning"], max_tokens: int = 8192,
             temperature: float | None = None, purpose: str = "", program_id: str = "",
             budget_scope: str | None = None, retries: int = 4) -> Reply:
        if not self.keys:
            raise NoAPIKey("no DeepSeek key in %s" % ", ".join(KEY_VARS[:2]))
        self._check_budget(budget_scope)
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "stream": False}
        if temperature is not None and "reasoner" not in model:
            payload["temperature"] = temperature
        last = None
        for attempt in range(retries * len(self.keys)):
            ki = self._key_i % len(self.keys)
            t0 = time.time()
            try:
                out = self._post("/chat/completions", payload, self.keys[ki])
                msg = out["choices"][0]["message"]
                use = out.get("usage", {})
                det = use.get("completion_tokens_details") or {}
                rep = Reply(text=msg.get("content") or "", reasoning=msg.get("reasoning_content") or "",
                            model=out.get("model", model), tokens_in=int(use.get("prompt_tokens", 0)),
                            tokens_out=int(use.get("completion_tokens", 0)),
                            reasoning_tokens=int(det.get("reasoning_tokens", 0)), latency_s=time.time() - t0)
                self._log({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": rep.model, "tokens_in": rep.tokens_in,
                           "tokens_out": rep.tokens_out, "reasoning_tokens": rep.reasoning_tokens, "purpose": purpose,
                           "program_id": program_id, "budget_scope": budget_scope, "key_index": ki,
                           "latency_s": round(rep.latency_s, 3), "status": "ok"})
                return rep
            except urllib.error.HTTPError as e:
                code = e.code
                last = "HTTP %d" % code
                self._log({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model, "purpose": purpose,
                           "program_id": program_id, "budget_scope": budget_scope, "key_index": ki,
                           "latency_s": round(time.time() - t0, 3), "status": "http_%d" % code})
                if code in (401, 402, 403):          # bad / exhausted key: next key
                    self._key_i += 1
                    continue
                time.sleep(min(60, 2 ** (attempt % retries) * 2))
                if code not in (429, 500, 502, 503, 504):
                    self._key_i += 1
            except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError, KeyError) as e:
                last = type(e).__name__
                self._log({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model, "purpose": purpose,
                           "program_id": program_id, "budget_scope": budget_scope, "key_index": ki,
                           "latency_s": round(time.time() - t0, 3), "status": "error_" + last})
                time.sleep(min(60, 2 ** (attempt % retries) * 2))
        raise RuntimeError("LLM call failed after retries: %s" % last)

    def list_models(self) -> list:
        if not self.keys:
            raise NoAPIKey("no DeepSeek key")
        return [m["id"] for m in self._get("/models", self.keys[0]).get("data", [])]

    def self_test(self) -> dict:
        """16-token self-test of reasoning and chat models (T0.6)."""
        out = {"base": self.base, "n_keys": len(self.keys)}
        try:
            out["models"] = self.list_models()
        except Exception as e:
            out["models_error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
        for kind, model in MODELS.items():
            try:
                r = self.chat([{"role": "user", "content": "Reply with the single word: ready"}], model=model,
                              max_tokens=16 if kind == "chat" else 64, purpose="self_test")
                out[kind] = {"ok": True, "model": r.model, "text": r.text.strip()[:40], "tokens_in": r.tokens_in,
                             "tokens_out": r.tokens_out, "latency_s": round(r.latency_s, 2)}
            except Exception as e:
                out[kind] = {"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:200])}
        return out


if __name__ == "__main__":
    print(json.dumps(LLMClient().self_test(), indent=1))
