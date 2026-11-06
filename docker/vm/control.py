"""Controller-only SSH transport and workspace synchronization."""

import base64
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path

SSH = [
    "ssh",
    "-T",
    "-p",
    "22",
    "-i",
    "/run/id",
    "-o",
    "BatchMode=yes",
    "-o",
    "StrictHostKeyChecking=no",
    "-o",
    "UserKnownHostsFile=/run/known_hosts",
    "-o",
    "ConnectTimeout=2",
    "-o",
    "LogLevel=ERROR",
    "root@10.0.2.15",
]
# Root executes only this fixed launcher; subject argv, environment and stdin are data.
LAUNCH = r"""
import base64,json,os,subprocess,sys
p=json.loads(base64.b64decode(sys.argv[1]))
os.setgroups([]); os.setgid(1000); os.setuid(1000)
os.environ.clear(); os.environ.update(HOME='/home/agent', USER='agent', LOGNAME='agent', PATH='/usr/local/bin:/usr/bin:/bin', LANG='C.UTF-8')
os.environ.update(p.get('env') or {})
os.chdir(p.get('cwd') or '/home/agent')
try:
 r=subprocess.run(p['cmd'], input=base64.b64decode(p.get('input','')), capture_output=True, timeout=p.get('timeout',30))
 print(json.dumps({'returncode':r.returncode,'stdout':base64.b64encode(r.stdout).decode(),'stderr':base64.b64encode(r.stderr).decode()}))
except FileNotFoundError as e:
 print(json.dumps({'returncode':127,'stdout':'','stderr':base64.b64encode(str(e).encode()).decode()}))
except subprocess.TimeoutExpired:
 print(json.dumps({'timeout':True}))
"""
WRITE = "import pathlib,sys,base64; p=pathlib.Path(sys.argv[1]); p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(base64.b64decode(sys.argv[2]))"


def execute(payload):
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    command = shlex.join(["/usr/bin/python3", "-c", LAUNCH, encoded])
    result = subprocess.run(
        [*SSH, command], input=b"", capture_output=True, timeout=payload.get("timeout", 30) + 10
    )
    if result.returncode:
        raise RuntimeError("VM transport unavailable: " + result.stderr.decode(errors="replace"))
    return json.loads(result.stdout)


def sync():
    state = Path("/run/workspace-state.json")
    old = json.loads(state.read_text()) if state.exists() else {}
    current = {}
    for path in Path("/export").rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to("/export").as_posix()
        body = path.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        current[relative] = digest
        if old.get(relative) != digest:
            result = execute(
                {
                    "cmd": [
                        "python3",
                        "-c",
                        WRITE,
                        "/home/agent/" + relative,
                        base64.b64encode(body).decode(),
                    ]
                }
            )
            if result["returncode"]:
                raise RuntimeError("workspace synchronization failed")
    for relative in old.keys() - current.keys():
        result = execute({"cmd": ["rm", "-f", "--", "/home/agent/" + relative]})
        if result["returncode"]:
            raise RuntimeError("workspace removal failed")
    state.write_text(json.dumps(current))


def main():
    if sys.argv[1] == "ping":
        result = subprocess.run([*SSH, "/bin/true"], capture_output=True, timeout=5)
        raise SystemExit(result.returncode)
    payload = json.loads(sys.stdin.read())
    sync()
    print(json.dumps(execute(payload)))


if __name__ == "__main__":
    main()
