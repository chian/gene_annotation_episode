# Infernal retained-result worker, workload 224

Implemented `gene_annotation_episode/native_infernal_result_worker.py`, its
dedicated tests, and byte-for-byte copies of workload 222's four saved producer
examples. No shared runtime, pure grader, inventory, prompt or goal file was
edited by this workload. Root separately repaired the search reader's handling
of selected `--oskip` after this worker's consumer test exposed the defect.

The entry points are `run(plan) -> manifest` and
`python -m gene_annotation_episode.native_infernal_result_worker PLAN_PATH`.
The plan and selected-row shapes follow WORKLOAD_001.md exactly. The worker reads
only the captured paths in the plan, calls the existing pure readers and
calculators, and writes `sheet.json`, `scores.json`, `selected-rows.ndjson`,
`diagnostics.json`, and `worker-result.json`. Complete numerical results stay in
separate sheet and score files. No Store, network, model, native scientific
execution or resource selection is introduced inside the worker.

`publication_inputs` contains exactly `supplied_metadata`, `parsed_records`
(a list), `operand_bindings`, and `captured_artifacts` without local paths.
Original supplied metadata is retained separately from the fields parsed from
actual FASTA, CM/filter pairs and optional training Stockholm. Wrong metadata
does not overwrite actual input lengths or sequences. CM consensus length is
CLEN; its HMM filter is never counted as an additional covariance model.
Sequence SHA-256 identifies the original uppercase sequence. Native T/U, X/N
and I/A normalization applies only when checking output correspondence.

Search associations come from the pure reader's validated metadata joins;
tblout query order is never converted to an original input ordinal. Alignment
associations check the original input order, native score index where supplied,
original sequence symbols and positions, and the reader's inherited-prefix
verification. Native warning-qualified duplicate-name restoration stays with
the pure reader. Compact bindings are copied from the original explicit binding
only when its ordinal and supplied name/accession validate. Related models are
family references, with no invented physical reference-residue intervals.

Selection preserves raw `hit_id`, `aggregate_id`, and `record_key` values and
the native collection order. Requested key order does not reorder native rows;
missing requested keys produce specific failures. Each selected row carries all
available family measurements in `observation_measurements`, independent of the
requested metric subset. Those observations contain no timing fields. Column and
pair rows retain typed numbers without inventing a single physical subject.

`numerical_complete` means that the requested extraction and projection
succeeded. Valid unknown/not-measured quantities and absent optional external
bindings are not failures. Diagnostics retain these qualifications with
`affects_completion=false`. Malformed required artifacts, contradictory original
associations and missing requested keys are incomplete outcomes, while their
independent useful values remain saved. The full diagnostic file preserves
reader/calculator details; manifest failures use the frozen compact shape.

The final focused command, executed through `local_jobs.run_local_job`, was:

```text
.venv/bin/python -m pytest -q /home/chia/repos/gene_annotation_episode/tests/test_native_infernal_result_worker.py --junitxml=/home/chia/repos/gene_annotation_episode/verification/tool_graders_infernal_worker_2026-10-26_224/tests_004.xml --basetemp=/home/chia/repos/gene_annotation_episode/verification/tool_graders_infernal_worker_2026-10-26_224/pytest_004
```

Result: **43 passed in 1.51 seconds**, exit 0. TEST_RECEIPT_004.json records the
exact command, source hashes and actual resource receipt. The verified limits
were memory.max 21474836480 bytes, memory.swap.max 0, scratch 4294967296 bytes,
and RuntimeMaxUSec infinity. The existing scratch enforcement remains monitored
visible allocation with possible overshoot plus the hard per-file limit.

Checks include all five families; both search programs; original options and
calculator populations; source-selected rows and order; no-hit output;
partial/malformed cells; missing/unreadable/truncated models; reverse and
out-of-range physical coordinates; incorrect metadata and bindings; duplicate
sequence names; accession-disambiguated model names; no-hit inputs preceding
returned queries; mapali same-name inherited/new collisions; global/submodel,
match-only, missing-PP and sampled alignment modes; original normalization
identities; full fixture hashes; and saved-sheet recalculation with I/O, parsers,
network and subprocess calls disabled. Another worker test prohibits opening
original/unselected data paths, constructing Store, networking or executing a
subprocess while the worker runs.

The initially failing `--oskip` consumer test removed only the table's Option
settings footer line. The original selected flag remained in operation.settings;
file capture was still complete. Before root's reader repair, union coverage
was incorrectly 1.0. The final test verifies that union coverage is unavailable
while actual captured-file completeness remains true. Original failing and
intermediate receipts remain under tests_001 through tests_003.

`save_examples.py` additionally executed seven actual worker CLI processes under
the same explicit limits. It used only retained native artifacts, with no
scientific tool reruns. Six requested projections completed; the native failure
case retained its specific incomplete result. Each directory under
`examples_001/` has the exact plan, command receipt, stdout/stderr and complete
worker outputs. `SELECTED_EXAMPLES_001.json` gathers the actual selected rows.

| Saved projection | Actual selected numerical values |
| --- | --- |
| cmsearch hit, mrum-tRNA.1 / tRNA5 | 71.4 bits; E-value 3.6e-22; sequence interval [0,72); model and sequence span fractions 1.0 |
| cmscan hit, same original operands | 71.4 bits; E-value 1e-22; sequence interval [0,72) |
| search sequence, mrum-tRNA.1, reported | hit count 1; union numerator 72; denominator 72; fraction 1.0 |
| alignment sequence, mrum-tRNA.1 | 60.03 bits; native avg PP 1.0; 72 model matches; 72 original nt; PP mean bounds .95–1.0 |
| alignment sequence, mrum-tRNA.9 | 47.5 bits; 68 model matches / 72 model positions; 40 EL nt; 2 ordinary insert nt; matched sequence coverage 68/110 |
| alignment column 0, all rows | occupancy numerator 10; denominator 10; fraction 1.0 |
| alignment pair [0,114], all rows | 10 canonical pairs / 10 unambiguous pairs; fraction 1.0; gap/missing/ambiguous/nonresidue/unavailable exclusions each 0 |
| retained native failure | original `--cpu 1 --sample --seed 42`; native exit 1; zero selected alignment rows; no fabricated scientific measurements |

The actual mapali-collision consumer example also verifies original name tRNA1
for distinct inherited and new operands: mapali ordinal 0 has 73 nt and no new
native score; sequences ordinal 0 has 72 nt, 40.84 bits and native avg PP .992.
The full sheet preserves printed names `0|tRNA1` and `5|tRNA1`, their mapping
provenance, and inherited/new population membership.

Final worker SHA-256:
`94d14d96d87e6f67b39d2c47db5496e3595e0bc97ef86136ddb1f7c7b5b80f41`.
Final dedicated test SHA-256:
`b699a122854ec74c6054156986912cd4a208da11febc31ff3296df934c63e1c0`.
The final receipt includes every consumed grader/view/contract source hash.
`tests/fixtures/native_infernal_result_worker/NATIVE_SHA256.json` preserves all
32 copied native-file hashes. The original bundle hashes are:

| Producer example | Original bundle SHA-256 |
| --- | --- |
| cmsearch | 837c5526f26bb1e29859f4cfd794890cdd0d4d58a8dd7270c63f27aaf1afacb3 |
| cmscan | b06b92e5219f296788f572450a2ac30ae9d4a84249aefd33171be10fa79f27ae |
| cmalign | b67c8aab3ade0ce3035ce1d7511d14669e0d3c8d40cfe4e535de1b20b6ff4fae |
| native failure | ba3d950b89b80ebbec40fe62f6486bec0663f5be5ff62eb582489a3dea715819 |

These checks establish retained-input numerical worker behavior and its real
bounded CLI. They do not establish complete episode-path publication, parent or
grandparent communication, or credit/continuation; those remain root/225-owned.
No API/HPC Infernal deployment is claimed. Optional traceback bytes and included
search MSA remain retained artifacts; this worker does not reinterpret them as
new traceback or residue-correspondence measurements. Local model gaps remain
rendered gaps, not proven deletions; native search spans remain spans. No new
annotation-score formula or independence claim is introduced.

The full immutable goal attachment was read before implementation. The original
objective and all 16 design principles were reread verbatim after substantial
native/source study and again before closure, followed by the exact worker
contract. SOURCE_RESET_001.json records the authority hash and inspected source
identities. The completed producer, both complete pure reader/calculator paths,
frozen views/contracts, and the publication consumer were inspected.
