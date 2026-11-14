Execution planning and shared memory

State the desired result, acceptance rule, input sizes, algorithm/options,
software/database fingerprints, CPU/memory/scratch needs and turnaround preferences before
selecting a resource. Use process.execution to retrieve this tool's recipe,
fresh resource observations and compatible measured timing history. Unknown
requirements or availability remain unknown. Reuse successful setup and prior
measurements; retain failed and censored attempts too. Resource observations
expire quickly; algorithm timings decay more slowly. Refresh only missing or
stale information that can change the decision. A cached queue read does not
renew its capture time. Current reservations still require atomic admission.

Prefer local execution when available and sufficient for the work.
Compare observed host capacity and actual configured resource contracts with
the requested worker plus coordinator headroom. Otherwise consider Aurora:
queue, staging/setup, execution, collection,
uncertainty, useful result value and node-hours all matter. Local resource
conditions do not limit an Aurora allocation. Choose a useful allocation portfolio, including
remaining useful units, instead of repeatedly paying queue/setup costs.

Launch a long calculation through the assigned detached execution binding.
Return the durable original handoff to the parent. The parent may do another
useful bounded action while the native worker runs. Track each physical attempt,
its resource reservation, result owner, forecast and next observation time.
Monitor and parse with one tool call when their contracts are known; commission
an iterative child only for unresolved investigation. A changed queue, elapsed
time without completion, progress or resource pressure updates the conditional
forecast. Repeated polls are not independent training examples.

Compare marginal expected yield of ready actions with their real cost. If no
ready action has positive expected net value and a valuable job is pending,
schedule a monitor wake rather than grind or finish prematurely. Preserve the
pending job's value; waiting and polling earn no credit. Use the existing HPC
cron controller for HPC waits. Keep a local worker's owning workflow alive:
its systemd service is tied to that workflow and is not a durable cron survivor.

This recipe applies to the selected real contract. It does not turn local-only
APIs into remote calls. Carry the exact selected contract, operands, output
schema and result reader into an HPC commission. If preparation needs new code,
the execution episode must establish and validate that adapter before submitting.
Return original outputs through the owning result reader and receipt custody.
Operational completion/timing credit is separate from A101 scientific credit.

Machine capacity constraints protect CPU, RAM and process concurrency. Do not
add elapsed-time limits, timeout wrappers, token/turn/action-count budgets or
cumulative usage stops. Runtime predictions and monitor schedules inform the
episode's credit decision; exceeding an estimate must not kill a calculation.
