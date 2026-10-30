# Current FBA source preparation under contract029

The preparation helper and five bounded verification cases are implemented and
verified. The unchanged original688 runtime selection **failed** its actual byte
checks. No selectable software.json was emitted, and readiness remains false.
This packet does not establish a working current native producer or complete
FBA episode path.

`prepare_software.py` exposes exactly:

```
stage_flux_balance_current_software(*, selected_plan_path, source_root, destination)
```

All paths are explicit and absolute. The input must have the exact byte identity
of one original688 SBML/JSON selected-plan.json. A nonempty destination is
refused; no retry, discovery, runtime replacement or source substitution occurs.
The helper uses only standard-library metadata/file operations. It verifies
every reused original Python, runtime and solver-runtime pin and copies exactly
029's seven current files. It changes only module_root and implementation_files
in a successful detached software candidate. Its staging return always says
metadata is unvalidated; bounded application validation retains a separate record.
On the observed runtime failure it emits only source bytes and a failure receipt.

Actual preparation ran inside check179_current_software713, using its frozen
source_snapshot as source_root and its retained prepared-software directory as
destination. The selected original plan input was a byte-identical frozen copy
of the original Cobra JSON selected-plan; both original SBML/JSON plan identities
are retained in EVIDENCE_001.json. The seven copied files match their before/after
source pins and are read-only. Original688 source/runtime/receipts were preserved.

| Original reused pin population | Count | Actual result |
| --- | ---: | --- |
| Python | 1 | Matches original pin |
| Runtime files | 11,399 | All match original pins |
| Additional native library files | 23 | 14 changed; 9 missing |
| Total | 11,423 | 11,400 match; 23 fail |

All failures belong to the original solver_runtime_files selection. For example,
the selected libc.so.6 was 2,129,424 bytes with SHA256 3a15d668…; the observed
file is 2,190,608 bytes with SHA256 85e64f97…. Original libexpat.so.1.9.1,
libffi.so.8.1.4, liblzma.so.5.4.5, libncursesw.so.6.4, libpanelw.so.6.4,
libreadline.so.8.2, libstdc++.so.6.0.33, libtinfo.so.6.4 and libz.so.1.3
paths are missing. RUNTIME_FAILURES_001.json retains every exact selected and
observed pin. No observed pin replaced its selected value.

The same bounded attempt passed five tests: actual source/runtime preparation;
sole schema detachment and rejection; refusal to rebind a nonempty destination;
controlled missing/mismatched pin handling; and rejection of nonoriginal plan
metadata with a retained failure receipt. The current sole software validator
and v1/v2 plan validators were exercised from the **complete frozen application
source_snapshot**. On runtime failure their candidate existed only in memory for
diagnostic metadata checks; it was not emitted as a selectable descriptor.

The exact seven-file selection has a separate import-closure limitation:
execution_contracts.py imports communication and launch_instructions, which are
outside029's seven files. No staged-module import or native invocation was tried.
Current metadata validity therefore does not prove native importability. Root
owns any later explicitly revised runtime/full-source deployment under a separate
contract; this packet leaves029 and all original selections unchanged.

The original handle was collected once, successfully and quiescently:

```
verification/tool_graders_hmmer_map_verification_2026-10-28_529/
  check179_current_software713/handle.json
```

Unit: gene-local-job-c05a3a3a99424b52adbecf525bba3482.service. Result: five
tests passed, returncode0, source/dependency/stdlib/binary unchanged, no outside
imported modules or unbound mappings, and native audit bytes unchanged. The
enclosing service measured 67.894185778 seconds of service-wall time; this is
not native solver duration. Verified memory limit was 20GiB with zero swap and
no wall cap; scratch policy was4GiB, monitored with possible overshoot and a
matching per-file hard limit. Observed scratch was776,192,000 bytes; memory peak
was not reported. No filesystem sandbox is claimed.

The launcher explicitly selected retained155e Python3.12 and retained134c
dependencies, then copied them into check179's test runtime/dependencies. The
original selected producer Python remains check151c_producer688/runtime/bin/python;
it was checked as bytes, not executed. These different runtime paths are recorded
separately in bounded-validation.json and EVIDENCE_001.json.

No model load, scientific/native parser, optimize call, finite scientific worker,
acquisition, installation or network operation was performed by713. No production,
prompt, numerical, inventory or progress file was changed. Tool-information028
remains unapproved and untouched. The source helper, tests and evidence are
released for review; runtime readiness and actual new fullWorkflow verification
remain unfinished.
