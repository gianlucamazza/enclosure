# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| Latest GitHub release | Yes |
| `main` | Yes |
| Older tags | No |

## Scope

Enclosure is a local research instrument. The lab stack (`docker/compose.yaml`) is for local research use only. It is not a production service and must not be published to an untrusted network.

The subject-facing world is a fixture. The `/inner/*` control plane is for the experimenter on the same machine.

## Unreleased VM boundary

In VM mode the subject runs as UID 1000 inside a per-sample QEMU/KVM guest.
The controller is a trusted Docker container with KVM/TUN devices and
NET_ADMIN in its own network namespace; it does not use host networking or
privileged-container mode. Host, Docker daemon, controller and hypervisor are
trusted infrastructure. Keep them patched; this is not a hypervisor escape test.

The guest receives neither controller code nor control credentials. Its TAP
firewall drops forwarding to other networks; DNS and fixture HTTP/HTTPS are
served at the boundary, and `/inner/` is denied by the proxy. TLS private keys
remain outside the guest. There is no shared guest workspace mount and no
fallback to controller execution if the VM fails.

Virtualization, the internal CA and synthetic DNS can still be observable.
Absence of known enclosure strings is not a guarantee of indistinguishability.
The legacy Docker subject has different boundaries and remains available only
through the explicit backend selection.

Raw Inspect logs can contain per-sample control tokens in metadata and account
information in provider errors. Guest isolation does not make logs safe to
publish. Review and sanitize exports; the automated export path is tracked in
[#38](https://github.com/gianlucamazza/enclosure/issues/38). Do not publish
private keys or raw auth-failure traces.

## Reporting a vulnerability

Use GitHub's **Report a vulnerability** form on this repository (Security tab → private advisory).

If that form is not available, open an issue asking for a private contact. Do not include vulnerability details in the issue or in a public pull request.

## Response

A private report will be acknowledged, assessed, and if confirmed, fixed on `main` and described in a GitHub security advisory. This is a research project; there is no SLA.
