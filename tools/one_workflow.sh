#!/usr/bin/env bash
# One owned workflow per window, inside machine resource bounds.
set -euo pipefail
task_repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
if [[ $# -lt 3 || $2 != -- ]]; then
    echo 'Usage: bash tools/one_workflow.sh runs/<unique-run> -- command arguments...' >&2
    exit 64
fi
task_run=$(realpath -m -- "$1")
shift 2
case "$task_run" in "$task_repo/runs/"*) ;; *) echo 'Output must be under repository runs/.' >&2; exit 64 ;; esac
mkdir -p -- "$task_repo/runs"
task_window=${CODEX_THREAD_ID-}
if [[ ! $task_window =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
    echo 'A stable CODEX_THREAD_ID is required for this window; do not invent one per run.' >&2
    exit 64
fi
task_key=${task_window//-/}
task_service="gene-episode-workflow-$task_key.service"
# No hyphens: this must not inherit the old globally capped workflow slice.
task_slice="geneepisodewindow$task_key.slice"
task_slot="$task_repo/runs/workflow-windows/$task_window"
mkdir -p -- "$task_slot"
exec 9>"$task_slot/workflow.lock"
if ! flock -n 9; then echo 'This Codex window already owns a running workflow.' >&2; exit 75; fi
task_state=$(systemctl --user show "$task_service" --property=ActiveState --value)
case "$task_state" in active|activating|deactivating|reloading) echo 'The prior workflow is still active.' >&2; exit 75 ;; esac
task_group=$(systemctl --user show "$task_slice" --property=ControlGroup --value)
if [[ -n $task_group && -d /sys/fs/cgroup$task_group ]]; then
    task_members=$(find "/sys/fs/cgroup$task_group" -name cgroup.procs -exec cat {} +)
    if [[ -n $task_members ]]; then echo 'The prior workflow still has processes.' >&2; exit 75; fi
fi
# A failed transient child can retain its inactive parent unit by dependency.
# Reset only our quiescent slice's units; never stop somebody's running work.
while read -r task_unit task_rest; do
    [[ -n $task_unit ]] || continue
    task_unit_slice=$(systemctl --user show "$task_unit" --property=Slice --value)
    if [[ $task_unit_slice == "$task_slice" ]]; then
        if ! systemctl --user reset-failed "$task_unit" 2>/dev/null; then
            task_loaded=$(systemctl --user show "$task_unit" --property=LoadState --value)
            if [[ $task_loaded != not-found ]]; then echo 'Cannot clear the prior stopped worker.' >&2; exit 76; fi
        fi
    fi
done < <(systemctl --user list-units --all --type=service --plain --no-legend --no-pager 'gene-local-job-*.service')
systemctl --user reset-failed "$task_service" 2>/dev/null || true
mkdir -p -- "$(dirname -- "$task_run")"
if ! mkdir -- "$task_run"; then echo 'A fresh run directory is required.' >&2; exit 64; fi
# The ownership supervisor uses only the standard library. Never borrow a
# scientific run's environment to supervise unrelated work.
task_python=$(command -v python3)
task_status=0
# On normal driver exit the supervisor remains active until all owned workers
# finish. systemd-run --wait therefore keeps this window's lock for the whole
# workload, including children whose parent episode has already yielded.
systemd-run --user --quiet --wait --pipe --collect --service-type=exec --expand-environment=no \
    --unit="$task_service" --slice="$task_slice" \
    --property=CPUQuota=100% --property=MemoryMax=5368709120 \
    --property=MemorySwapMax=0 --property=TasksMax=infinity \
    --property=KillMode=control-group --working-directory="$task_repo" \
    --setenv="PYTHONPATH=$task_repo" --setenv=PYTHONDONTWRITEBYTECODE=1 \
    --setenv="CODEX_THREAD_ID=$task_window" \
    --property="ExecStopPost=$task_python -m gene_annotation_episode.workflow_budget cleanup" \
    "$task_python" -m gene_annotation_episode.workflow_budget "$task_run" -- "$@" \
    >"$task_run/stdout.log" 2>"$task_run/stderr.log" || task_status=$?
if [[ -f "$task_run/workflow-budget.json" ]]; then
    task_group=$(systemctl --user show "$task_slice" --property=ControlGroup --value)
    if [[ -n $task_group && -d /sys/fs/cgroup$task_group ]]; then
        task_members=$(find "/sys/fs/cgroup$task_group" -name cgroup.procs -exec cat {} +)
        if [[ -n $task_members ]]; then echo 'Workflow processes remain; completion is unconfirmed.' >&2; exit 76; fi
    fi
fi
cat -- "$task_run/stdout.log"
cat -- "$task_run/stderr.log" >&2
exit "$task_status"
