Aurora execution

Use the hpc parent template, its prediction sister, and launch -> launch_hpc.
Read shared queue/software observations before discovery. Use qstat and the
status page only when stale/missing information warrants it; distinguish PBS
Priority from scheduler score. Transform queue size, comparable jobs ahead,
requested resources, reservations and walltimes into dated model features.

The established account is BioReason-Aurora-Test. All software, databases,
environments and outputs belong under /lus/flare/projects/BioReason-Aurora-Test;
disposable execution files belong under its chian/runs/ directory. Reuse the
existing authenticated bastion master via tools/aurora_ssh.sh. Loss of that
transport requires attention, never a new authentication loop.

The episode owns remote discovery, setup and executable portfolio design.
Freeze the original forecast before launch. Keep the exact PBS job identity;
an uncertain submit must be recovered rather than repeated. Attach the explicit
monitor cron controller. Each observation updates conditional queue/runtime and
remaining value. Collect original per-unit results, verify acceptance, then
export one terminal timing record per physical allocation. Choose allocations
large enough to amortize waiting while using their useful reserved lifetime.
