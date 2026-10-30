# Workload 222: one selected native Infernal attempt

Implemented the producer and local lifecycle bridge in the assigned new files.
The producer stages exactly the selected operands and invokes exactly one native
command. It records the original request separately from realized staged paths,
retains complete selected outputs and partial files, and seals a bundle. Saved
attempts validate their original bytes without another process. Unsealed work
remains uncertain; conflicting ownership and corrupted saved bytes reject.

The bridge prepares an existing `NativeJobHandle` without starting it. It checks
the original operation, resource, run/episode directory identity, policy, selected
invocation record, driver command and actual lifecycle request/hash. Starting,
waiting and process limits remain with `native_lifecycle` and `local_jobs`.

## Observed native executions

Each row below is one real native invocation using the installed Infernal 1.1.5
executables and copies of original tutorial inputs. `--cpu 1` was explicit in all
four selections. The actual resource boundary verified memory.max = 21474836480,
memory.swap.max = 0 and RuntimeMaxUSec = infinity. Scratch limit = 4294967296.
No local wall-time cap, new index construction, retry or option substitution was
introduced. Before/after hashes establish that tutorial inputs were unchanged.

| Selected operation | Native outcome | Retained native numerical example |
| --- | --- | --- |
| cmsearch, format 3, three models, ten sequences, included MSA | exit 0; 10 table hits | mrum-tRNA.1 / tRNA5: 71.4 bits, E-value 3.6e-22, model positions 1–72, sequence positions 1–72, both lengths 72 |
| cmscan, format 2, the same three models and all four supplied pressed companions | exit 0; 10 table hits | tRNA5 / mrum-tRNA.1: 71.4 bits, E-value 1e-22; native overlap marker `*`; all four companions retain the staged models.cm prefix |
| cmalign, one model, ten sequences, Stockholm/sfile/ifile/elfile/tfile | exit 0; 10 score rows | first row: length 72, CM positions 1–72, 60.03 bits, native average posterior 1.000. mrum-tRNA.9 has 40 EL residues after consensus position 37, beginning at unaligned sequence position 36 |
| cmalign, explicitly selected `--cpu 1 --sample --seed 42` | exit 1; no alignment tables | complete 414-byte stdout includes `ERROR: --sample requires --cpu 0`; original CPU selection and failure remain unchanged |

These values are native artifact examples, not gene-annotation scores. Declared
software version remains explicitly declared in each bundle; native stdout/table
version text is retained separately. Three success bundles contain 4, 3 and 7
output artifacts respectively. The failure bundle retains both diagnostic streams
and specific missing-output facts.

Native source inspection established CM framing as an `INFERNAL1/a` block ending
in `//`, followed by its `HMMER3/a` through `HMMER3/f` filter block ending in `//`.
The producer counts CM/filter pairs; search operands can contain several, while
cmalign requires exactly one. Native scientific parsing stays with Infernal and
the separately owned deterministic graders.

## Verification and frozen evidence

Command executed:

```text
.venv/bin/python -m pytest -q tests/test_native_infernal_execution.py --junitxml=verification/tool_graders_infernal_native_execution_2026-10-26_222/tests_001.xml
```

Result: **43 passed in 8.43 seconds**, exit 0. Native examples were acquired once;
tests reuse their sealed artifacts with subprocess creation and network sockets
disabled. Other tests use explicitly synthetic framing/process fixtures.

Verified cases include exact input copies and operand bindings; original versus
realized commands; cmscan prefix preservation; multiple search models; cmalign
single-model rejection; missing, changed, malformed and nonregular inputs; empty
pressed inputs; wrong/missing/nonexecutable software; partial input capture with
the actual partial byte hash; scratch preflight failure; real and synthetic
nonzero native exits; missing output roles; unsealed and unowned attempts;
conflicting identities; changed saved inputs and outputs; symlink/path escape;
manifest byte-format changes; complete retained-copy validation; prepare without
start; changed driver command, environment, request hash, policy, resource,
invocation and attempt ownership.

The exact command arrays, environments and Python driver invocations are in
[COMMANDS_001.json](COMMANDS_001.json). [COMMANDS_001.sh.txt](COMMANDS_001.sh.txt)
renders the native argv/environment as shell text; native stdout/stderr were
redirected by the producer to the selected bundle paths. It is a command record,
not a request to repeat the native jobs.

[runs/index.json](runs/index.json) locates the four original action directories.
Every directory contains the immutable `infernal-plan.json`, original
`assignment.json`, `native.json`, full `infernal-attempt/bundle.json`, retained
inputs/outputs, source-before/source-after checks and the actual verified
lifecycle receipt. Complete bundle hashes:

| Case | SHA-256 |
| --- | --- |
| cmsearch | 837c5526f26bb1e29859f4cfd794890cdd0d4d58a8dd7270c63f27aaf1afacb3 |
| cmscan | b06b92e5219f296788f572450a2ac30ae9d4a84249aefd33171be10fa79f27ae |
| cmalign | b67c8aab3ade0ce3035ce1d7511d14669e0d3c8d40cfe4e535de1b20b6ff4fae |
| native failure | ba3d950b89b80ebbec40fe62f6486bec0663f5be5ff62eb582489a3dea715819 |

[NUMERICAL_ARTIFACT_EXAMPLES_001.json](NUMERICAL_ARTIFACT_EXAMPLES_001.json)
retains exact row examples, artifact sizes and resource receipts. Its measured
durations are systemd service wall seconds; they include producer work and are
not relabeled as native algorithm runtime or queue wait.

[TEST_RECEIPT_001.json](TEST_RECEIPT_001.json) and [tests_001.xml](tests_001.xml)
record the actual test result. [SOURCE_RESET_001.json](SOURCE_RESET_001.json)
records inspected source identities; [SOURCE_RESET_002.json](SOURCE_RESET_002.json)
records verbatim objective/all-16-principle rereads after native/source examination
and between native tools, plus workload-contract rereads.

Final producer SHA-256:
`a899575cc976d37fbdcf434654acc51adcb05f14d48054c70e462d96c9725d67`.
Final bridge SHA-256:
`e5251ff627b07869bdb356a6f41b4662affa96f2827f5ff94d92c863150cf037`.
Contract hashes used match root's frozen 221 handoff; all source hashes are in
the test receipt. No existing shared file, grader, prompt, credit implementation
or inventory was edited by workload 222.

## Integration boundary

This establishes real native execution, retention, original attempt qualification
and offline replay through the producer/lifecycle bridge. Shared production
launch/results wiring, deterministic grader consumption, final typed parent and
grandparent communication, and episode credit/continuation remain root-owned
verification. They are not proved by these module tests or native jobs.

The native lifecycle retains its existing enforcement semantics: cgroup process
limits, hard per-file size limit, and visible allocated scratch monitoring with
possible overshoot. It is not a filesystem sandbox. No API or HPC Infernal
deployment is claimed by this local verification.
