# Aurora access and authentication

The practical HPC binding requires explicit `kind=pbs_ssh`, `ssh_argv`,
`python_executable`, `workspace` and `account` configuration. It appends the
selected remote Python worker command to `ssh_argv` and retains the resulting
transport outcome. The recorded user requirements below inform that explicit
configuration; they do not establish that authentication currently works.

The established route is user `chian` through `bastion.alcf.anl.gov`, followed
by SSH running on the bastion to Aurora using host-based authentication. Preserve
this two-hop route in `ssh_argv`; a guessed ProxyJump is not a substitute.

The local alias is `alcf-bastion`, with strict host-key checking and master socket
`/home/chia/.ssh/alcf-control/bastion.sock`. Its configuration enables
`ControlPersist yes`, `ServerAliveInterval 60` and `ServerAliveCountMax 3`.
These are machine-specific settings, checked locally on 2026-11-03.

The user will authenticate once when ready. Reuse that original authenticated
master for all subsequent operations. Do not repeatedly request MobilePASS,
reconnect automatically, try guessed credentials, or fall back to a new login.
Reuse-only clients must specify `ControlMaster=no`, `ControlPersist=no`,
`BatchMode=yes`, `StrictHostKeyChecking=yes` and `ProxyCommand=/bin/false` with
the explicit socket. The false proxy prevents a new transport even if the master
disappears between a socket check and the operation. The bare alias uses
`ControlMaster auto` and is not a reuse-only operation. Preserve stdin for the
remote worker's request. Loss of the session is an operational stop, not
authorization for another authentication attempt. The local caller adapter
`tools/aurora_ssh.sh` implements this reuse-only path and preserves stdin; the
explicit example binding is `examples/aurora_execution_resources.json`.

The existing user unit `gene-annotation-alcf-keepalive.service` runs
`/home/chia/.local/state/gene-annotation-episode/alcf-access/keepalive.py`.
It checks the original master and sends `/bin/pwd` every 300 seconds with
fail-closed transport options. It exits if that transport is unavailable;
it cannot authenticate or replace the master. The unit was inactive when checked
on 2026-11-03. Do not start a second heartbeat loop or bypass the local execution
policy to start this Python helper. The SSH master's configured keepalives
maintain the transport without a separate Python workflow. Neither a socket nor
a unit's existence proves a live authenticated session, and no keepalive
guarantees survival of network failure or site-imposed expiration.

Use the configured transport literally. Configuration does not establish that
authentication currently works. A failed transport or invalid remote reply
remains an operational failure; it does not establish that a requested native
job failed or authorize replacement of an uncertain submission. Credentials
are not result data and do not belong in assignments, inventory or receipts.

[ALCF token instructions](https://docs.alcf.anl.gov/account-project-management/accounts-and-access/logging-in-with-tokens/)
describe the site's human authentication mechanism. They do not select an
account, connection route or execution resource for this binding. The specific
route and socket above are this project's recorded procedure. The original
2026-10-22 instruction referenced source rows A1–A2 in
`docs/LAUNCH_INSTRUCTION_SOURCES_2026-10-22_001.md`; that index was unavailable
during recovery. The original instructions remain recoverable from Git.
