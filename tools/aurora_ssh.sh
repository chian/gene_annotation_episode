#!/usr/bin/env bash
# PBS transport: reuse the user's authenticated bastion master, never log in.
# The binding appends exactly one shell-quoted remote worker command; stdin is
# its JSON request and must pass through both SSH clients without alteration.
set -euo pipefail
if [[ $# != 1 || -z $1 ]]; then
    echo 'Usage: bash tools/aurora_ssh.sh "remote command"' >&2
    exit 64
fi

task_socket=/home/chia/.ssh/alcf-control/bastion.sock
task_directory=${task_socket%/*}
if [[ -L $task_directory || ! -d $task_directory ||
      $(stat -c '%u:%a' -- "$task_directory") != "$EUID:700" ||
      -L $task_socket || ! -S $task_socket || ! -O $task_socket ]]; then
    echo 'Original authenticated bastion socket unavailable; no login attempted.' >&2
    exit 69
fi

# Quote once for the bastion's shell. The inner SSH receives the exact command
# string already quoted by the PBS binding. Do not use eval or consume stdin.
task_command=${1//\'/\'\\\'\'}
task_inner="exec /usr/bin/ssh -T -o BatchMode=yes -o NumberOfPasswordPrompts=0"
task_inner+=" -o PreferredAuthentications=hostbased -o HostbasedAuthentication=yes"
task_inner+=" -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no"
task_inner+=" -o PubkeyAuthentication=no -o GSSAPIAuthentication=no"
task_inner+=" -o StrictHostKeyChecking=yes -o ConnectionAttempts=1 -o ConnectTimeout=20"
task_inner+=" -o ControlMaster=no -o ControlPath=none -o ControlPersist=no"
task_inner+=" chian@aurora.alcf.anl.gov '$task_command'"

# ControlMaster=no alone still permits a fresh connection. The false proxy
# closes that fallback, including a master disappearing after the check above.
# There is intentionally no retry, master creation, login prompt or cleanup of
# the shared master. Its own ServerAlive settings maintain the connection.
exec /usr/bin/ssh -F /home/chia/.ssh/config -S "$task_socket" -T \
    -o ControlMaster=no -o ControlPersist=no -o BatchMode=yes \
    -o ProxyCommand=/bin/false -o StrictHostKeyChecking=yes \
    -o ConnectionAttempts=1 -o ConnectTimeout=20 \
    -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no \
    -o PubkeyAuthentication=no -o HostbasedAuthentication=no \
    -o GSSAPIAuthentication=no -o NumberOfPasswordPrompts=0 \
    alcf-bastion "$task_inner"
