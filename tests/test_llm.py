"""T0.6: LLM client key fallback, ledger and budget stop against a local mock server (no network)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from heurbridge.evolve import llm

STATE = {"calls": [], "fail_429": 0}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(200, {"data": [{"id": "deepseek-chat"}, {"id": "deepseek-reasoner"}]})

    def do_POST(self):
        key = self.headers.get("Authorization", "")[7:]
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        STATE["calls"].append(key)
        if key == "bad-key":
            return self._send(401, {"error": "unauthorized"})
        if STATE["fail_429"] > 0:
            STATE["fail_429"] -= 1
            return self._send(429, {"error": "rate"})
        self._send(200, {"model": req["model"], "choices": [{"message": {"content": "ready", "reasoning_content": "hm"}}],
                         "usage": {"prompt_tokens": 7, "completion_tokens": 3,
                                   "completion_tokens_details": {"reasoning_tokens": 1}}})


@pytest.fixture(scope="module")
def server():
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield "http://127.0.0.1:%d" % srv.server_address[1]
    srv.shutdown()


def test_load_keys_strips_commas():
    env = {"DEEPSEEK_LAB_API_KEY": " k1, ", "DEEPSEEK_API_KEY": "k2,k1,", "DEEPSEEK_API_KEY_2": "k3"}
    assert llm.load_keys(env) == ["k1", "k2", "k3"]
    assert llm.load_keys({}) == []


def test_fallback_ledger_budget(server, tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_LAB_API_KEY", "bad-key,")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "good-key")
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    c = llm.LLMClient(ledger_path=tmp_path / "ledger.jsonl", base_url=server, budgets={"M/test": 2})
    STATE["fail_429"] = 1
    r = c.chat([{"role": "user", "content": "hi"}], purpose="unit", program_id="p1", budget_scope="M/test")
    assert r.text == "ready" and r.reasoning == "hm" and r.tokens_in == 7 and r.reasoning_tokens == 1
    assert STATE["calls"][:1] == ["bad-key"] and STATE["calls"][-1] == "good-key"
    ledger = (tmp_path / "ledger.jsonl").read_text()
    assert "good-key" not in ledger and "bad-key" not in ledger          # never log keys
    recs = [json.loads(x) for x in ledger.splitlines()]
    assert recs[-1]["status"] == "ok" and recs[-1]["key_index"] == 1 and recs[-1]["program_id"] == "p1"
    assert {"http_401", "http_429"} <= {x["status"] for x in recs}
    c.chat([{"role": "user", "content": "hi"}], budget_scope="M/test")   # 2 used; cap = int(2*1.1) = 2
    with pytest.raises(llm.BudgetExceeded):
        c.chat([{"role": "user", "content": "hi"}], budget_scope="M/test")
    assert c.list_models() == ["deepseek-chat", "deepseek-reasoner"]


def test_no_key(monkeypatch, tmp_path):
    for v in llm.KEY_VARS:
        monkeypatch.delenv(v, raising=False)
    c = llm.LLMClient(ledger_path=tmp_path / "l.jsonl")
    with pytest.raises(llm.NoAPIKey):
        c.chat([{"role": "user", "content": "x"}])


def test_load_keys_from_file(tmp_path):
    """The lab key file (API_KEY=...) is read by the client; nothing needs to be exported."""
    f = tmp_path / "api.env"
    f.write_text("# lab key\nexport API_KEY='sk-file-1'\nOTHER=x\n")
    assert llm.load_keys({"DEEPSEEK_API_KEY_FILE": str(f)}) == ["sk-file-1"]
    assert llm.load_keys({"DEEPSEEK_API_KEY_FILE": str(f), "DEEPSEEK_LAB_API_KEY": "sk-env"}) == ["sk-env", "sk-file-1"]
    assert llm.load_keys({"DEEPSEEK_API_KEY_FILE": str(tmp_path / "missing.env")}) == []
