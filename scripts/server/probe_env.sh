#!/usr/bin/env bash
# T0.2 read-only server probe.  Prints one JSON object (keys below) to stdout; changes nothing.
#   bash probe_env.sh > probe_<port>.json
set -u
j() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }   # JSON-escape stdin
section() { printf '"%s": %s,\n' "$1" "$(eval "$2" 2>&1 | head -c 20000 | j)"; }
echo "{"
section hostname "hostname"
section date "date -Is"
section os "cat /etc/os-release 2>/dev/null | head -4; uname -r"
section nproc "nproc"
section free_g "free -g"
section df "df -h /data / 2>/dev/null"
section nvidia_smi "nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu,driver_version --format=csv 2>/dev/null || echo none"
section nvidia_procs "nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory --format=csv 2>/dev/null || echo none"
section cuda_version "nvidia-smi 2>/dev/null | grep -o 'CUDA Version: [0-9.]*' || echo none"
section tmux "tmux ls 2>&1"
section load "uptime"
section top_cpu "ps -eo pid,user,pcpu,pmem,etime,comm --sort=-pcpu | head -15"
section openroad_procs "pgrep -x openroad -a 2>/dev/null | head -20 || true"
section which "for b in docker conda mamba micromamba magic klayout netgen yosys python3 python3.11 gcc g++ cmake git curl wget rsync tmux; do printf '%s=%s\n' \$b \"\$(command -v \$b || echo -)\"; done"
section python3_version "python3 --version"
section gcc_version "gcc --version | head -1"
section net "for u in https://github.com https://pypi.org https://download.pytorch.org https://conda.anaconda.org https://raw.githubusercontent.com https://api.deepseek.com; do printf '%s %s\n' \$u \"\$(curl -sS -o /dev/null -m 12 -w '%{http_code} %{time_total}' -I \$u 2>&1 | tail -1)\"; done"
section heura_repr "ls -la /data/dzy/heura_repr 2>&1 | head -40"
section eda_tools "ls /data/dzy/heura_repr/eda/tools 2>&1 | head; /data/dzy/heura_repr/eda/tools/openroad/bin/openroad -version 2>&1 | head -2"
section conda_envs "conda env list 2>/dev/null || echo none"
section deepseek_env "for v in DEEPSEEK_LAB_API_KEY DEEPSEEK_API_KEY; do if [ -n \"\${!v:-}\" ]; then echo \$v=set; else echo \$v=unset; fi; done"
printf '"_end": true\n}\n'
