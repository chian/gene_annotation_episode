# Actual local practical operations

Only the current episode catalog grants callable operations. The following are
implemented by the opt-in practical local binding:

| Callable operation | Actual selected work |
| --- | --- |
| `practical.inspect` | Observe the assignment's declared path/hash predicates now. |
| `practical.inventory.refresh` | Read the chosen structured preparation catalog and reconcile the local mirror. |
| `practical.context.set` | Persist a validated absolute cwd and explicit environment. |
| `practical.directory.create` | Create a selected directory within the workspace. |
| `practical.file.write` | Publish the selected UTF-8 bytes within the workspace. |
| `practical.file.read` | Read a selected byte offset/count with original bytes and file size. |
| `practical.command.run` | Execute one preparation/diagnostic argv and environment, retaining native outcome and bounded logs. |
| `practical.job.start` | Start the original requested argv/environment using its durable native identity. |
| `practical.job.status` | Observe the original native job and stdout/stderr tails. |
| `practical.job.collect` | Observe the native outcome and validate requested outputs. |

`practical.command.run` waits for its one selected command; it does not run a
private episode or decide what to do after failure. `practical.job.start`
returns a durable handle for the fixed requested computation. The episode can
then decide its next useful action through the shared loop.

A subprocess's `cd` or `export` does not persist into the next action. Use
`practical.context.set` for that transition; its environment replaces the stored
context environment. Preparation-command arguments merge their environment
with that context. The requested job instead uses its original explicit job
environment, with the stored cwd. Supply required environment operands there;
do not assume setup-command exports alter the requested job.

New actions record their original operands, native outcome and closed validation
assessments. Replay reads the original receipt. A nonzero native return code
can be a completed own action with a failed native outcome and zero credit.
Malformed or unexecuted requests are feedback, not manufactured work. Choose
repairs using the actual failure and preserve valid partial contributions.
Source rows L2–L4.
