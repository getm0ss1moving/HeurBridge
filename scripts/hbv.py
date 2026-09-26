#!/usr/bin/env python3
"""Encrypted workspace on the shared lab account (hbv = HeurBridge vault).

The lab login is shared by several people, so nothing of ours stays readable on the server at rest:

* The server holds ciphertext only: <root>/vault/{code,data,runs}/*.tgz.enc (tar.gz, AES-256-CBC with a
  PBKDF2-SHA256 key; identical format on the Mac's OpenSSL 3 and the server's OpenSSL 1.1.1).
* The key (~/.config/heurbridge/vault.key: 32 random bytes as hex, mode 0600) never leaves the Mac except
  through the stdin of the SSH session that starts a job.  On the server it is never written to a file, a
  command line (readable by every user through `ps`) or an environment variable (/proc/<pid>/environ); it is
  passed between processes through pipes only.  With kernel.yama.ptrace_scope=1 (checked on 224 and 227)
  other logins of the same account cannot read a running job's memory.
* A job decrypts its inputs into a private workspace (default /dev/shm: RAM, gone at reboot), runs
  detached, and on exit -- or every --snapshot seconds -- encrypts the files it created or changed back
  into the vault; the workspace is then wiped.  Plaintext exists only while the job runs.
* Only files tracked by git (or untracked and not ignored) are shipped as code: unpublished documents
  (ignored by .gitignore) never reach the server.
* Public third-party material (benchmark downloads, OpenROAD, Python environments) is not ours to hide and
  stays in plaintext outside the vault.

  hbv.py keygen
  hbv.py push-code --port 224
  hbv.py push-data --port 224 --name NAME --src LOCAL_DIR
  hbv.py run       --port 224 --run RUN [--code latest] [--after RUN0 ...] [--resume] [--data NAME:DEST ...]
                   [--gpu 1] [--workroot /dev/shm] [--snapshot 1800] [--exclude REGEX] -- COMMAND ...
  hbv.py status    --port 224 [--run RUN] [--tail 30]
  hbv.py fetch     --port 224 --run RUN [--partial]        # decrypted on the Mac into runs/remote/RUN/
  hbv.py stop      --port 224 --run RUN                    # our own job only (process group recorded at launch)
  hbv.py ls        --port 224
"""

from __future__ import annotations

import argparse
import io
import os
import shlex
import stat
import subprocess
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYFILE = Path.home() / ".config" / "heurbridge" / "vault.key"
CIPHER = "-aes-256-cbc -md sha256 -pbkdf2 -iter 20000"
DEFAULT_ROOT = "/data/dzy/heura_repr/hb"           # 224: /data is a local disk we can write
TRANSIENT_ROOT = "/tmp/.hbv"                       # hosts without a writable /data (e.g. 227): fetch results promptly,
                                                   # /tmp is cleared on reboot and by systemd-tmpfiles
SSH = str(ROOT / "scripts" / "ssh_run.sh")

# The detached job (stage 2).  Passed to `bash -c` as a command-line argument, so it must never contain a
# secret: the key arrives on stdin through a pipe and is read into a shell variable.
STAGE2 = r'''set -uo pipefail
umask 077
WD="$1"; RUN="$2"; ROOT="$3"; SNAP="$4"; CMD="$5"; EXCL="$6"
IFS= read -r K
exec 0</dev/null
P='__CIPHER__'
encout() {
  local out="$ROOT/vault/runs/$RUN.$1.tgz.enc"
  ( cd "$WD/repo" && find . -type f -newer "$WD/.marker" -print0 \
      | { if [ -n "$EXCL" ]; then grep -z -v -E "$EXCL" || true; else cat; fi; } > "$WD/.list" ) || return 1
  ( cd "$WD/repo" && tar --null -T "$WD/.list" -czf - 2>/dev/null ) \
    | openssl enc $P -salt -pass fd:3 -out "$out.tmp" 3< <(printf '%s' "$K") && mv -f "$out.tmp" "$out"
}
finish() {
  local rc=$?
  [ -n "${SNAPPID:-}" ] && kill "$SNAPPID" 2>/dev/null
  printf '%s\n' "${JOBRC:-$rc}" > "$WD/repo/logs/hbv_$RUN.rc"
  encout final && rm -f "$ROOT/vault/runs/$RUN.partial.tgz.enc"
  rm -rf "$WD"
  rm -f "$ROOT/state/$RUN.pid" "$ROOT/state/$RUN.wd"
}
trap finish EXIT
trap 'exit 143' TERM INT HUP
echo "$$" > "$ROOT/state/$RUN.pid"
if [ "$SNAP" -gt 0 ]; then ( while sleep "$SNAP"; do encout partial; done ) & SNAPPID=$!; fi
cd "$WD/repo"
bash -c "$CMD" > "$WD/repo/logs/hbv_$RUN.log" 2>&1
JOBRC=$?
exit "$JOBRC"
'''.replace("__CIPHER__", CIPHER)


def key() -> str:
    if not KEYFILE.exists():
        sys.exit("no vault key: run `hbv.py keygen` first")
    if stat.S_IMODE(KEYFILE.stat().st_mode) & 0o077:
        sys.exit("%s must be mode 0600" % KEYFILE)
    k = KEYFILE.read_text().strip()
    if len(k) != 64 or any(c not in "0123456789abcdef" for c in k):
        sys.exit("malformed vault key")
    return k


def ssh(port: int, command: str, stdin: bytes | None = None, capture: bool = True) -> subprocess.CompletedProcess:
    """Run a remote command.  ``command`` becomes part of a command line on the server: never put a secret in it."""
    return subprocess.run([SSH, str(port), command], input=stdin, capture_output=capture)


def remote_script(port: int, script: str) -> subprocess.CompletedProcess:
    """Run a bash script fed through stdin (may contain the key: stdin is not visible to other users)."""
    return subprocess.run([SSH, str(port), "bash -s"], input=script.encode(), capture_output=True)


def encrypt_bytes(data: bytes) -> bytes:
    return subprocess.run(["openssl", "enc", *CIPHER.split(), "-salt", "-pass", "file:%s" % KEYFILE],
                          input=data, capture_output=True, check=True).stdout


def decrypt_bytes(data: bytes) -> bytes:
    return subprocess.run(["openssl", "enc", "-d", *CIPHER.split(), "-pass", "file:%s" % KEYFILE],
                          input=data, capture_output=True, check=True).stdout


def tgz(root: Path, files: list) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.PAX_FORMAT) as t:
        for f in files:
            p = root / f
            if p.is_file():
                t.add(str(p), arcname=str(f))
    return buf.getvalue()


def upload(port: int, rroot: str, rel: str, blob: bytes):
    q = shlex.quote("%s/%s" % (rroot, rel))
    r = ssh(port, "umask 077; mkdir -p \"$(dirname %s)\" && cat > %s.tmp && mv -f %s.tmp %s" % (q, q, q, q), stdin=blob)
    if r.returncode:
        sys.exit("upload failed: %s" % r.stderr.decode()[-400:])


def cmd_keygen(a):
    if KEYFILE.exists():
        print("vault key exists: %s" % KEYFILE)
        return
    KEYFILE.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(KEYFILE.parent, 0o700)
    k = subprocess.run(["openssl", "rand", "-hex", "32"], capture_output=True, check=True).stdout.decode().strip()
    fd = os.open(KEYFILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(k + "\n")
    print("created %s (0600); back it up: without it the vault cannot be decrypted" % KEYFILE)


def code_files() -> list:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                         capture_output=True, check=True).stdout.decode()
    return sorted({f for f in out.split("\0") if f and (ROOT / f).is_file()})


def cmd_push_code(a):
    key()
    files = code_files()
    sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True,
                         text=True).stdout.strip() or "nogit"
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    name = "%s%s-%s" % (sha, "-dirty" if dirty else "", time.strftime("%Y%m%d%H%M%S"))
    blob = encrypt_bytes(tgz(ROOT, files))
    upload(a.port, a.root, "vault/code/%s.tgz.enc" % name, blob)
    upload(a.port, a.root, "vault/code/latest", (name + "\n").encode())       # a name, not content
    print("CODE_PUSHED %s files=%d bytes=%d" % (name, len(files), len(blob)))


def cmd_push_data(a):
    key()
    src = Path(a.src).resolve()
    files = sorted(str(p.relative_to(src)) for p in src.rglob("*") if p.is_file())
    blob = encrypt_bytes(tgz(src, files))
    upload(a.port, a.root, "vault/data/%s.tgz.enc" % a.name, blob)
    print("DATA_PUSHED %s files=%d bytes=%d" % (a.name, len(files), len(blob)))


def cmd_run(a):
    k = key()
    command = " ".join(a.command[1:] if a.command[:1] == ["--"] else a.command)
    if not command:
        sys.exit("no command")
    # The account's $HOME is on a NAS whose per-user quota is exhausted (EDQUOT): tool caches go to a local disk.
    # They hold public packages only (conda/pip downloads, font and kernel caches), never our data.
    cache = a.cache_dir or ("/data/dzy/heura_repr/cache" if a.port == 224 else "/tmp/.hbcache")
    env = ["export PYTHONUNBUFFERED=1", "mkdir -p %s" % shlex.quote(cache)]
    for var, sub in (("XDG_CACHE_HOME", "xdg"), ("PIP_CACHE_DIR", "pip"), ("CONDA_PKGS_DIRS", "conda_pkgs"),
                     ("MPLCONFIGDIR", "mpl"), ("TORCH_HOME", "torch")):
        env.append("export %s=%s" % (var, shlex.quote("%s/%s" % (cache, sub))))
    if a.gpu is not None:
        env.append("export CUDA_VISIBLE_DEVICES=%s" % shlex.quote(a.gpu))
    if a.api_key_file:                      # the LLM client reads the key from the file; it never enters environ
        env.append("export DEEPSEEK_API_KEY_FILE=%s" % shlex.quote(a.api_key_file))
    full = "; ".join(env + [command])
    q = shlex.quote
    code = "$(cat %s)" % q(a.root + "/vault/code/latest") if a.code == "latest" else q(a.code)
    lines = [
        "set -euo pipefail", "umask 077",
        "K=%s" % q(k),
        "P=%s" % q(CIPHER),
        "ROOT=%s; RUN=%s; WR=%s" % (q(a.root), q(a.run), q(a.workroot)),
        'mkdir -p "$ROOT/vault/code" "$ROOT/vault/data" "$ROOT/vault/runs" "$ROOT/state"; chmod 700 "$ROOT"',
        'if [ -e "$ROOT/state/$RUN.pid" ] && kill -0 "$(cat "$ROOT/state/$RUN.pid")" 2>/dev/null; then '
        'echo "HBV_ERROR $RUN is running"; exit 3; fi',
        'WD=$(mktemp -d "$WR/hbw.XXXXXXXX"); mkdir -p "$WD/repo/logs"',
        'trap \'[ -e "$WD/.launched" ] || rm -rf "$WD"\' EXIT',
        'dec() { openssl enc -d $P -pass fd:3 -in "$1" 3< <(printf "%s" "$K") | tar -xzf - -C "$2"; }',
        'dec "$ROOT/vault/code/%s.tgz.enc" "$WD/repo"' % code,
    ]
    for r in a.after:
        lines.append('dec "$ROOT/vault/runs/%s.final.tgz.enc" "$WD/repo"' % r)
    if a.resume:
        lines.append('[ -e "$ROOT/vault/runs/$RUN.partial.tgz.enc" ] && dec "$ROOT/vault/runs/$RUN.partial.tgz.enc" "$WD/repo"')
    for d in a.data:
        name, _, dest = d.partition(":")
        lines += ['mkdir -p "$WD/repo/%s"' % (dest or "."), 'dec "$ROOT/vault/data/%s.tgz.enc" "$WD/repo/%s"' % (name, dest or ".")]
    lines += [
        'touch "$WD/.marker"; sleep 1',
        'printf "%s\\n" "$WD" > "$ROOT/state/$RUN.wd"',
        "STAGE2=%s" % q(STAGE2),
        'printf "%%s\\n" "$K" | setsid nohup bash -c "$STAGE2" hbv "$WD" "$RUN" "$ROOT" %d %s %s > /dev/null 2>&1 &'
        % (a.snapshot, q(full), q(a.exclude or "")),
        'touch "$WD/.launched"',
        'echo "HBV_STARTED run=$RUN pid=$! wd=$WD"',
    ]
    r = remote_script(a.port, "\n".join(lines) + "\n")
    sys.stdout.write(r.stdout.decode())
    if r.returncode:
        sys.exit("run failed: %s" % r.stderr.decode()[-600:])


def cmd_status(a):
    q = shlex.quote
    script = """ROOT=%s
for f in "$ROOT"/state/*.pid; do [ -e "$f" ] || continue; r=$(basename "$f" .pid); pid=$(cat "$f")
  if kill -0 "$pid" 2>/dev/null; then s=running; else s=stale; fi
  echo "RUN $r pid=$pid $s wd=$(cat "$ROOT/state/$r.wd" 2>/dev/null)"; done
ls -la "$ROOT/vault/runs" 2>/dev/null | tail -n +2
""" % q(a.root)
    if a.run:
        script += ('wd=$(cat "$ROOT/state/%s.wd" 2>/dev/null) && [ -n "$wd" ] && echo "--- log tail" && '
                   'tail -n %d "$wd/repo/logs/hbv_%s.log"\n') % (a.run, a.tail, a.run)
    sys.stdout.write(remote_script(a.port, script).stdout.decode())


def cmd_fetch(a):
    key()
    kind = "partial" if a.partial else "final"
    r = ssh(a.port, "cat %s" % shlex.quote("%s/vault/runs/%s.%s.tgz.enc" % (a.root, a.run, kind)))
    if r.returncode or not r.stdout:
        sys.exit("fetch failed: %s" % r.stderr.decode()[-300:])
    plain = decrypt_bytes(r.stdout)
    dest = ROOT / "runs" / "remote" / a.run
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(plain), mode="r:gz") as t:
        members = [m for m in t.getmembers() if not (m.name.startswith("/") or ".." in Path(m.name).parts)]
        t.extractall(dest, members=members)
    rc = (dest / "logs" / ("hbv_%s.rc" % a.run))
    print("FETCHED %s -> %s files=%d rc=%s" % (a.run, dest.relative_to(ROOT), len(members),
                                                  rc.read_text().strip() if rc.exists() else "n/a"))


def cmd_stop(a):
    script = ('ROOT=%s; f="$ROOT/state/%s.pid"; [ -e "$f" ] || { echo "no such run"; exit 1; }; pid=$(cat "$f"); '
              'pg=$(ps -o pgid= -p "$pid" | tr -d " "); [ "$pg" = "$pid" ] || { echo "pid $pid is not our job"; exit 1; }; '
              'kill -TERM -- "-$pid" && echo "HBV_STOPPED %s"\n') % (shlex.quote(a.root), a.run, a.run)
    sys.stdout.write(remote_script(a.port, script).stdout.decode())


def cmd_ls(a):
    script = 'ROOT=%s; for d in code data runs; do echo "== $d"; ls -la "$ROOT/vault/$d" 2>/dev/null | tail -n +2; done\n' % shlex.quote(a.root)
    sys.stdout.write(remote_script(a.port, script).stdout.decode())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn):
        p = sub.add_parser(name)
        p.set_defaults(fn=fn)
        if name != "keygen":
            p.add_argument("--port", type=int, default=224)
            p.add_argument("--root", default=None)
        return p
    add("keygen", cmd_keygen)
    add("push-code", cmd_push_code)
    p = add("push-data", cmd_push_data)
    p.add_argument("--name", required=True)
    p.add_argument("--src", required=True)
    p = add("run", cmd_run)
    p.add_argument("--run", required=True)
    p.add_argument("--code", default="latest")
    p.add_argument("--after", nargs="*", default=[])
    p.add_argument("--resume", action="store_true")
    p.add_argument("--data", nargs="*", default=[])
    p.add_argument("--gpu", default=None)
    p.add_argument("--workroot", default="/dev/shm")
    p.add_argument("--snapshot", type=int, default=1800)
    p.add_argument("--exclude", default="", help="regex of repo-relative paths not to archive (e.g. '\\.odb$')")
    p.add_argument("--api-key-file", default="", help="server path of the LLM key file, read by the client itself")
    p.add_argument("--cache-dir", default="", help="tool caches (default /data/dzy/heura_repr/cache on 224, else /tmp/.hbcache)")
    p.add_argument("command", nargs=argparse.REMAINDER)
    p = add("status", cmd_status)
    p.add_argument("--run", default="")
    p.add_argument("--tail", type=int, default=30)
    p = add("fetch", cmd_fetch)
    p.add_argument("--run", required=True)
    p.add_argument("--partial", action="store_true")
    p = add("stop", cmd_stop)
    p.add_argument("--run", required=True)
    add("ls", cmd_ls)
    a = ap.parse_args()
    if hasattr(a, "port") and a.root is None:
        a.root = DEFAULT_ROOT if a.port == 224 else TRANSIENT_ROOT
    a.fn(a)


if __name__ == "__main__":
    main()
