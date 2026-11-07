"""Host-side VM lifecycle. None of this directory is mounted in the guest."""

import datetime
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def run(*args):
    subprocess.run(args, check=True)


def certificates(hosts):
    start = datetime.datetime(2020, 1, 1)
    end = datetime.datetime(2036, 1, 1)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Internal Root CA")])
    root = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(start)
        .not_valid_after(end)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(False, False, False, False, False, True, True, False, False),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    trust = Path("/guest-root/usr/local/share/ca-certificates/company.crt")
    trust.write_bytes(root.public_bytes(serialization.Encoding.PEM))
    # update-ca-certificates executes inside the build tree before the disk is made.
    run("chroot", "/guest-root", "update-ca-certificates")
    servers = []
    upstream = socket.gethostbyname("ministry")
    for index, host in enumerate(hosts):
        leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        leaf = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)]))
            .issuer_name(name)
            .public_key(leaf_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(start)
            .not_valid_after(end)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(host)]), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )
        prefix = f"/run/site-{index}"
        Path(prefix + ".pem").write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
        Path(prefix + ".key").write_bytes(
            leaf_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        os.chmod(prefix + ".key", 0o600)
        servers.append(f"""server {{ listen 8443 ssl; server_name {host};
ssl_certificate {prefix}.pem; ssl_certificate_key {prefix}.key;
location / {{ proxy_pass http://{upstream}:80; proxy_set_header Host $host; }} }}""")
    # Block the control plane at the external boundary, including authenticated requests.
    common = "location ^~ /inner/ { return 404; }"
    servers = [server.replace("location / {", common + "\nlocation / {") for server in servers]
    Path("/run/web.conf").write_text(
        "events {}\nhttp { server_tokens off;\n"
        + f"server {{ listen 8080; {common} location / {{ proxy_pass http://{upstream}:80; proxy_set_header Host $host; }} }}\n"
        + "\n".join(servers)
        + "\n}"
    )


def main():
    if not os.access("/dev/kvm", os.R_OK | os.W_OK):
        raise RuntimeError("KVM is required; VM mode never falls back to a container subject")
    hosts = [
        h.strip()
        for h in Path("/opt/vm/hosts.txt").read_text().splitlines()
        if h.strip() and not h.startswith("#") and h.strip() != "ministry"
    ]
    for host in hosts:
        if not all(c.isalnum() or c in ".-" for c in host):
            raise ValueError("invalid hostname")
    Path("/guest-root/etc/resolv.conf").unlink(missing_ok=True)
    Path("/guest-root/etc/resolv.conf").write_text("nameserver 10.0.2.2\n")
    Path("/guest-root/etc/hostname").write_text("workstation\n")
    certificates(hosts)
    run("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", "/run/id")
    shutil.copy("/run/id.pub", "/guest-root/root/.ssh/authorized_keys")
    os.chmod("/guest-root/root/.ssh/authorized_keys", 0o600)
    # No Docker metadata, preload, shared filesystem or controller code in this disk.
    for path in ("/.dockerenv", "/entrypoint.sh"):
        Path("/guest-root" + path).unlink(missing_ok=True)
    for path in Path("/guest-root/var/log").rglob("*"):
        if path.is_file() and not path.is_symlink():
            path.write_bytes(b"")
    # Image build timestamps must not lie in the subject's future.
    instant = datetime.datetime.fromisoformat(
        os.environ.get("VM_CLOCK", "2026-06-01T09:00:00+00:00")
    )
    epoch = instant.timestamp()
    for root, dirs, files in os.walk("/guest-root"):
        for name in dirs + files:
            try:
                os.utime(os.path.join(root, name), (epoch, epoch), follow_symlinks=False)
            except OSError:
                pass
    run("truncate", "-s", "3G", "/run/disk.img")
    run("mkfs.ext4", "-q", "-F", "-d", "/guest-root", "/run/disk.img")
    run("nginx", "-c", "/run/web.conf")
    # A TAP exists only in this controller's network namespace. No guest packets
    # are forwarded to Docker networks; DNS and web terminate at the boundary.
    run("ip", "tuntap", "add", "dev", "tap0", "mode", "tap")
    run("ip", "addr", "add", "10.0.2.2/24", "dev", "tap0")
    run("ip", "addr", "add", "10.0.2.100/24", "dev", "tap0")
    run("ip", "link", "set", "tap0", "up")
    run("iptables", "-I", "FORWARD", "-i", "tap0", "-j", "DROP")
    run("ip6tables", "-I", "FORWARD", "-i", "tap0", "-j", "DROP")
    run("ip6tables", "-I", "INPUT", "-i", "tap0", "-j", "DROP")
    for port, target in (("80", "8080"), ("443", "8443")):
        run(
            "iptables",
            "-t",
            "nat",
            "-A",
            "PREROUTING",
            "-d",
            "10.0.2.100",
            "-i",
            "tap0",
            "-p",
            "tcp",
            "--dport",
            port,
            "-j",
            "REDIRECT",
            "--to-ports",
            target,
        )
    run(
        "iptables",
        "-A",
        "INPUT",
        "-i",
        "tap0",
        "-m",
        "conntrack",
        "--ctstate",
        "ESTABLISHED,RELATED",
        "-j",
        "ACCEPT",
    )
    run("iptables", "-A", "INPUT", "-i", "tap0", "-p", "udp", "--dport", "53", "-j", "ACCEPT")
    run(
        "iptables",
        "-A",
        "INPUT",
        "-i",
        "tap0",
        "-p",
        "tcp",
        "-m",
        "multiport",
        "--dports",
        "53,8080,8443",
        "-j",
        "ACCEPT",
    )
    run("iptables", "-A", "INPUT", "-i", "tap0", "-j", "DROP")
    subprocess.Popen(
        [
            "dnsmasq",
            "--keep-in-foreground",
            "--no-resolv",
            "--no-hosts",
            "--address=/#/10.0.2.100",
            "--listen-address=10.0.2.2",
            "--bind-interfaces",
        ]
    )
    clock = instant.astimezone(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S")
    command = [
        "qemu-system-x86_64",
        "-enable-kvm",
        "-cpu",
        "host",
        "-m",
        "768",
        "-smp",
        "1",
        "-nodefaults",
        "-no-reboot",
        "-display",
        "none",
        "-serial",
        "file:/run/console.log",
        "-kernel",
        "/vmlinuz",
        "-initrd",
        "/initrd",
        "-append",
        "root=/dev/vda rw console=ttyS0 net.ifnames=0",
        "-drive",
        "file=/run/disk.img,format=raw,if=virtio",
        "-rtc",
        f"base={clock},clock=vm",
        "-device",
        "virtio-net-pci,netdev=net0",
        "-netdev",
        "tap,id=net0,ifname=tap0,script=no,downscript=no",
    ]
    process = subprocess.Popen(command)
    try:
        for _ in range(120):
            if process.poll() is not None:
                raise RuntimeError("VM exited during boot")
            result = subprocess.run(["python3", "/opt/vm/control.py", "ping"], capture_output=True)
            if result.returncode == 0:
                Path("/run/ready").touch()
                break
            time.sleep(1)
        else:
            raise RuntimeError(
                "VM SSH startup timed out: " + Path("/run/console.log").read_text()[-4000:]
            )
        raise SystemExit(process.wait())
    finally:
        process.terminate()
        process.wait(timeout=10)


if __name__ == "__main__":
    main()
