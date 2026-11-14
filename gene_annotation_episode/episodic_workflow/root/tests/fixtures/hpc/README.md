These three JSON files retain selected fields from actual read-only Aurora
observations acquired on 2026-11-04 UTC: `qstat -f -F json`, `qstat -Qf -F json`,
and https://status.alcf.anl.gov/aurora/activity.json. They retain the three queued
debug jobs, debug queue rules, scheduling scores, and reservation quantities.
Names, user identities, arbitrary environment variables and paths are omitted.
They are historical parser inputs, not a simulated SSH service or live-job proof.

The full disposable acquisition is under `runs/hpc_design_20261104/observations/`.
Required parser fixtures live here so tests do not depend on that run directory.

`a107-genomic01-payload-context.json.gz` retains the original decision states,
instructions and transmitted inputs from sessions16 and19 of the autonomous
2026-11-08 A107 genomic-window run `a107-d0eab29f68b5495d9910f73012be7747`.
The provider rejected their1208077 and1675471 characters against its existing
1048576-character transport capacity. Frozen candidate and planned input text
was repeated in planning prompts. Both branches ended source_failed, despite
their original continuation decisions remaining stop=false. The workflow was
stopped before any Launch/native child or remote submission. These are actual
historical model inputs for presentation/custody checks, not a new investigation,
a remote-job result, or a newly configured runtime/research limit. Original
operands and frozen bytes remain in this required fixture.
# Genomic03 contrast plan history

`a107-genomic03-plan-history-context.json.gz` retains the actual supplied state
and rejected wire text for genomic03's contrast execution decision29, provider
session0085. The provider rejected1,435,822 characters. The planner already had
a complete current Launch assignment; subsequent plan reads/history retained
multiple copies of its frozen files. The workload was stopped and drained
before the presentation repair. The separate positive Aurora calculation and
its delivered scientific sheets remain valid. This fixture records a provider
interface, not a research stopping budget.

`a107-genomic04-native-transport-context.json.gz` retains the actual native
Launch state and transmitted input immediately before genomic04's command8.
The native child was told to use the configured transport but its resource
view omitted the original ssh_argv, and it searched the whole repository for
connection files. The workflow was stopped and fully drained before repair;
no PBS job was submitted. The fixture separately retains the original supplied
resource configuration for checking its delivery through the actual context
provider and renderer. No SSH connection or native calculation is executed by
that check. This fixture contains no credentials or evaluator answer.

`a107-genomic05-monitor-context.json.gz` retains the actual rejected monitor
input from genomic05/session0132, including its original frame and instructions.
The source failed at1,052,907 characters. Unrelated literature report-source
definitions contributed most of its available_report_facts catalog; the
monitor's actual task concerned PBS9052111 failure status and its original logs.
The whole workflow was stopped and drained before changing presentation.
The separate positive calculation remains valid. This fixture is an actual
historical input for provider/custody checks, not a new model or native execution.
