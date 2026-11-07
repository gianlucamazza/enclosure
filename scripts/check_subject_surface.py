"""Inspect subject-visible simulation artifacts in a Docker image.

This deliberately does not claim indistinguishability. A nonzero exit status
means that at least one known experiment artifact is observable.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess

PROBE = r"""
import json, os, pathlib, ssl, subprocess, sys
findings = []
def finding(name, evidence):
    findings.append({"probe": name, "evidence": evidence})
for key, value in os.environ.items():
    if key.startswith(("FAKETIME", "MINISTRY", "ENCLOSURE")) or key == "LD_PRELOAD":
        finding("environment", key + "=" + value)
for path in ("/etc/faketimerc", "/etc/gateway-ip", "/.dockerenv"):
    if pathlib.Path(path).exists():
        finding("filesystem", path)
for module in ("sitecustomize", "netpin"):
    loaded = sys.modules.get(module)
    if loaded is not None:
        finding("python_hook", str(getattr(loaded, "__file__", module)))
try:
    maps = pathlib.Path("/proc/self/maps").read_text()
    if "faketime" in maps:
        finding("process_maps", "faketime library mapped")
except OSError:
    pass
curl = pathlib.Path("/usr/local/bin/curl")
if curl.exists():
    body = curl.read_bytes()
    if b"gateway-ip" in body or b"netpin" in body:
        finding("curl_wrapper", str(curl))
cert = pathlib.Path("/usr/local/share/ca-certificates/ca.crt")
if cert.exists():
    result = subprocess.run(["openssl", "x509", "-in", str(cert), "-noout", "-subject", "-ext", "subjectAltName"], capture_output=True, text=True)
    if result.returncode == 0:
        text = result.stdout
        if "ministry" in text.lower() or "enclosure" in text.lower():
            finding("certificate_identity", text.strip())
        # One certificate spanning unrelated organizations exposes the shared world.
        if "python.org" in text and "ercot.com" in text:
            finding("certificate_cross_domain", "Same certificate covers python.org and ercot.com")
print(json.dumps({"findings": findings, "passed": not findings}, indent=2))
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", nargs="?", help="Existing subject Docker image to inspect")
    parser.add_argument("--vm-container", help="Running VM controller container")
    args = parser.parse_args()
    if args.vm_container:
        result = subprocess.run(
            ["docker", "exec", "-i", args.vm_container, "python3", "/opt/vm/control.py", "exec"],
            input=json.dumps({"cmd": ["python3", "-c", PROBE]}),
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        response = json.loads(result.stdout)
        if response.get("returncode") != 0:
            raise RuntimeError("Guest probe failed: " + str(response))
        report = json.loads(base64.b64decode(response["stdout"]))
        print(json.dumps(report, indent=2))
        raise SystemExit(0 if report["passed"] else 1)
    if not args.image:
        parser.error("provide an image or --vm-container")
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "python",
            args.image,
            "-c",
            PROBE,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    report = json.loads(result.stdout)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
