# Shared regressions after barcode removal

Implementation evidence only; no goal or scope change.

The existing dedicated-source removal manifest and shared-file diff record the
removal. This check verifies affected shared behavior after that removal; it does
not run, reinstall or restore the removed barcode workflow.

The bounded `check001` completed with return code 0: **50 passed in 157.12s**.
The unit was `gene-local-job-3d9917c2d57646fa8a5e87f3279601b4.service` and its original
handle was collected only after terminal/quiescent status. The selected suites
were `test_communication.py`, `test_practical_execution_state.py`,
`test_expression_nmf_execution_integration.py` and `test_execution_progress.py`.
Helper modules were copied for imports and were not independently selected as
additional test suites.

These checks cover closed typed forms, practical receipts and terminal
completion, the remaining NMF resource/catalog/input-inheritance/result schemas,
and monitoring target/log/credit behavior. PBS transport in these tests uses a
local fixture, not a live HPC service. The NMF integration suite checks bindings
and custody without another NMF fit; full scientific-parent NMF execution has
its separate 490 receipts.

Application, dependency, interpreter and standard-library pins were unchanged.
The native-library audit found unchanged pins, no outside Python modules and no
unbound native mappings. Limits were 20 GiB RAM, 4 GiB monitored scratch and zero
swap, with no wall-time limit.

Evidence: `check001/receipt.json`, `check001/execution_audit.json`,
`check001/junit.xml`, `check001/stdout.txt`, and the frozen selected-test and source
pin manifests. Concurrent R1 scoring repairs have their own verification; this
receipt does not establish those repairs or unrelated resource capabilities.
