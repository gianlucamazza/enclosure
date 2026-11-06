FROM python:3.12-slim@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30 AS guest
RUN apt-get update && apt-get install -y --no-install-recommends linux-image-amd64 initramfs-tools systemd-sysv openssh-server curl ca-certificates iproute2 python3 && rm -rf /var/lib/apt/lists/*
RUN useradd -m -d /home/agent -s /bin/bash agent && echo workstation > /etc/hostname \
 && mkdir -p /root/.ssh /etc/systemd/network /run/sshd \
 && chmod 700 /root/.ssh \
 && printf '[Match]\nName=en* eth*\n[Network]\nAddress=10.0.2.15/24\nGateway=10.0.2.2\nDNS=10.0.2.2\n' > /etc/systemd/network/10-wired.network \
 && systemctl enable systemd-networkd ssh \
 && systemctl mask systemd-timesyncd.service \
 && rm -f /etc/ssh/ssh_host_* /etc/machine-id \
 && touch /etc/machine-id \
 && printf '[Service]\nExecStartPre=\nExecStartPre=/usr/bin/ssh-keygen -A\nExecStartPre=/usr/sbin/sshd -t\n' > /tmp/ssh.conf \
 && mkdir -p /etc/systemd/system/ssh.service.d \
 && mv /tmp/ssh.conf /etc/systemd/system/ssh.service.d/keys.conf
# A standard interpreter in /usr/local is part of the base image, without hooks.
FROM debian:bookworm-slim@sha256:734a72b3d6142a71993b4bc580ca01d8ca687f77a2c422d96a961d3376b179bc
RUN apt-get update && apt-get install -y --no-install-recommends qemu-system-x86 qemu-utils e2fsprogs openssh-client python3 python3-cryptography iproute2 iptables dnsmasq nginx socat ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=guest / /guest-root/
RUN cp /guest-root/boot/vmlinuz-* /vmlinuz && cp /guest-root/boot/initrd.img-* /initrd
COPY docker/vm/ /opt/vm/
COPY docker/lab-hosts.txt /opt/vm/hosts.txt
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "/opt/vm/boot.py"]
