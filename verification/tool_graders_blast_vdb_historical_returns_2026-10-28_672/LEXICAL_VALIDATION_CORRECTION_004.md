# Qualified retained-input validation

Root reviewed the exact call chain documented in VERIFICATION_003 and corrected
the implementation test's blanket prohibition on lexical validation. The original
user goal prohibits rerunning the original analysis and requires faithful retained
validation. Validating original supplied preparation-list bytes against the
already-selected token mapping does not run native analysis, choose work, create a
result, or add an observation. This corrects a test restriction; it does not amend
the user goal or replace earlier evidence.

No production parser, custody validation or historical data was changed. In the
qualified672 test adapter, the real `parse_blast_preparation_list` is called only
when its direct caller is `realize_selected_list` and that caller's parent is
`_validate_saved_realizations`. Grammar, complete occurrence identity, raw byte
size and SHA256 must match an original saved request. The original selected
materialization receipt is recorded, as is the returned validated-document hash.
The spy records every allowed call and returns the real parser's actual document.
It supplies no replacement parser result and weakens no runtime validation.

All other known preparation/native-result parsers, worker parse/project entrypoints,
native processes, acquisition, observation and artifact-publication entrypoints
remain denied. Original native input/workspace/executable paths remain denied.
The exact-existing-byte `_immutable` adapter and read-only original Store remain
the sole constructor/write adaptations. The already-closed canonical654 tree is
used, preserving its failed volume action and separate repair.

`CHECK130E_COMMAND.sh` selects only the actual654 return/replay check under a new
bounded529 handle,20GiB/4GiB/zero swap/no wall limit, with explicit check005 deps.
It uses its own working directory so preserved113b attempts do not exceed the
allocation; all scientific state and requests still use their authentic original
absolute paths. This is not a replacement annotation tree or Store.

Stopped130b and preflight-refused130c remain retained. No claim of zero parser
calls is valid for the qualified654 replay: original-input lexical validations
are explicitly permitted and observed, while native-result parsing and scientific
recalculation are prohibited. Completion and observed counts belong in the later
verification result, not this pre-run correction record.
