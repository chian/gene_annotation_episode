# Aurora access and authentication

These are launch instructions, not an execution binding or a complete episode.
The caller supplies the actual SSH command, remote Python and workspace. A
library entry does not establish that authentication currently works.

The project's established access procedure is an authenticated bastion session
for user `chian` at `bastion.alcf.anl.gov`, followed by SSH running on the bastion
to Aurora using host-based authentication. Preserve this two-hop procedure in
the caller's explicit `ssh_argv`; a guessed ProxyJump is not a substitute.
MobilePASS codes change and must be supplied with the user at authentication
time. Never save codes, passwords or private keys in instructions, assignments,
inventory, prompts or receipts. Ask the user for help when authentication is
actually needed; do not cycle through guessed hosts or credentials.

Local configuration recorded on 2026-10-22 has alias `alcf-bastion`, user
`chian`, strict host-key checking and the reusable master socket
`/home/chia/.ssh/alcf-control/bastion.sock`. These are machine-specific facts;
check the caller's configuration rather than assuming another machine has them.
The existing user unit `gene-annotation-alcf-keepalive.service` runs the local
`alcf-access/keepalive.py` helper. It checks the original master and sends
`/bin/pwd` every 300 seconds, then exits if that transport is unavailable. It
cannot perform authentication or replace the master. This transport heartbeat
is separate from episode-selected monitoring and waiting; it gives no job
progress or scientific credit. Merely finding its unit/socket does not prove it
is running or authenticated now.

[ALCF token instructions](https://docs.alcf.anl.gov/account-project-management/accounts-and-access/logging-in-with-tokens/)
describe human token authentication. The specific bastion chain above comes
from this project's recorded access procedure, not a claim that the public
guide requires that chain for every user. Provenance: source table rows A1–A2
in `docs/LAUNCH_INSTRUCTION_SOURCES_2026-10-22_001.md`.
