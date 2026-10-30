# FBA local binding metadata and native observations705

Implemented contract022 in two new modules. The binding module exports one
closed row schema, detached list validation and exact operation/mode/software/
model-format matching. It uses the existing common FBAJob/FBASoftware contracts
and native software validator. Metadata acceptance establishes no installation,
received input authority or new scoring implementation.

The observation module reads only the original eight declared native files and
lifecycle stdout/stderr. Selected stdout,stderr,native_log tails retain caller
order, actual offsets, observed lengths and raw base64 bytes. It neither parses
scientific output nor polls a process. Writer closure requires both terminal and
quiescent true. Missing and empty files remain distinct; available siblings are
preserved when a manifest is absent. Availability means a declared file was
observed, not successful science, productive execution or new credit.

The bounded read port allows only those original output paths. Original model
inputs, software paths, owner/start/environment/input-binding controls, arbitrary
siblings and alternate attempts are rejected. Existing anchored/no-follow FBA
storage rejects symlinks and nonregular files. No file or directory is created
by an observation/read operation.

## Verification

Original `check161_bindings705` passed **68/68** cases in6.57 seconds and was
fully collected with return code0, terminal/quiescent true. Source, dependency,
standard-library and interpreter before/after pins agree. Native audit is clean:
no outside modules, no unbound mappings, unchanged native libraries and unchanged
original retained fixtures. Current owned sources equal their frozen tested
copies exactly. There were no failed attempts or reruns in this scope.

Two cases read authentic retained688 files at their original declared absolute
paths, while the runner pins both those originals and copied support fixtures:

| Original format | Declared native files | Total bytes | Native-log bytes | 31-byte tail offset |
| --- | ---: | ---: | ---: | ---: |
| SBML |8 |5,533,618 |5,566 |5,535 |
| Cobra JSON |8 |5,495,431 |2,126 |2,095 |

Each also verifies an exact17-byte CSV window at offset3. These are opaque byte
observations on prior native results, not additional scientific measurements.
Other cases use explicitly synthetic compact plans/software and test files for
binding/schema mismatches, strict closure booleans, missing/empty files, partial
siblings, selected log order, exact allowed paths, bounded integer windows,
symlinks/FIFOs/directories and no-I/O/no-execution/no-scientific-parser guards.

The existing529 launcher used the explicit retained155e Python3.12 interpreter
and134c dependencies. Enforcement remained20GiB RAM,zero swap,4GiB monitored
scratch plus the existing per-file rlimit,and no wall cap. Observed scratch was
789,626,880 bytes; memory peak is unknown. Scratch monitoring can overshoot and
does not provide a filesystem sandbox. No solver, acquisition, installation,
source grant, receipt grant or Store-record publication was performed.

SOURCE_PINS_001.json, VERIFICATION_001.json and OWNED_ADDITIONS_001.patch retain
the exact contract, owned additions, original receipt/audits and evidence pins.
Shared numerical sheets, calculators, readers, producers, prompts, inventories
and progress records were not changed by705.

## Remaining integration

Root/706 own actual operation/progress/resource registration and the original
input-provider/start binding. Result-host publication, requested scientific-parent
returns, saved-sheet admission, closed episode replay/credit and configured/live
episode verification remain separate. These helper checks establish no whole-tool
completion and add no completed inventory row or operation link.
