# Repaired Homology isolated-wheel verification

This is a new verification receipt for the repaired C4 Homology adapter. The
earlier wheel and its evidence were not overwritten. No production source,
repository tests, checklist, goal or prior receipt was edited by this workload.

All scientific examples are explicitly synthetic. This run verifies the
installed package, pure adapter/calculator behavior and library construction.
It does not verify a full installed Workflow, live BV-BRC/AppService/Workspace
authentication or deployment, HPC execution, BLAST execution, model calls, or
episode communication. Separate workers own the Workflow checks.

## Actual run

The driver was invoked with the repository venv Python from `/tmp`:

```text
/home/chia/repos/gene_annotation_episode/.venv/bin/python -I -B /home/chia/repos/gene_annotation_episode/verification/tool_graders_bvbrc_homology_packaging_2026-10-24_002/run_verification.py
```

The driver built a fresh no-dependency wheel from temporary copies of the
current package directories and packaging files. Pip used its isolated build
environment because the venv does not contain setuptools. The wheel was
extracted into a separate temporary directory. The calculation process used
`-I -B`, ran outside the checkout, added only that extraction to `sys.path`,
and verified that every imported application/module path came from it. The
venv still supplies the declared third-party dependencies.

Build exit status: **0**, elapsed **1.9918821279425174 seconds**.
Isolated verification exit status: **0**, elapsed **0.5537043060176075 seconds**.
These are script checks, not a pytest test count.

Wheel: `wheels/gene_annotation_episode-0.2.0-py3-none-any.whl`

```text
wheel SHA256:
f7dad77a8a8104d7fd7a45427a4478625936ba76259de3aa013de08c41fb7278

computed scientific adapter implementation SHA256:
6431e9b48d6015056915c610f125653a9bbb886e0195bd1a24a1fc531896a809
```

## Passed checks

* All **313** packaged application/module/resource files match current source
  bytes. Every current package Python and JSON source is present in the wheel.
  The checked digest dependencies include the new
  `bvbrc_homology_subject_binding.py` and packaged C4 JSON schema.
* The static registry accepts the computed exact pin and rejects a conflicting
  pin. Both real library modes construct their commission contracts:
  `bvbrc.homology.database_identification` and
  `bvbrc.homology.pairwise_correspondence`. Three Homology return fact-source
  definitions are available. This construction check does not execute those
  contracts through an episode.
* The retained database example has five exact native-shaped artifact byte
  objects. The newly calculated full result equals the earlier full
  `SYNTHETIC_RESULT.json`, including all sheet, component, diagnostic and
  provenance content. Requested values are **3 hits**, **0.60** query paired
  coverage, **0.75** reference paired coverage, conditional function weights
  **2/3** and **1/3**, and an explicit native no-hit query count of **0**.
* Recalculating its disk-saved sheet at temperature **1** gives **0.8** and
  **0.2** exactly, equals the earlier full saved-sheet recalculation, and leaves
  the loaded sheet unchanged.
* The corrected pure C4 `blastx` fixture includes the complete original
  synthetic single-sequence reference FASTA, actual member sequence and digest,
  membership source, and scientific-input source. Their exact JSON source bytes
  are retained and checked against their ContentBindings. The repository test
  module constructs inputs only; the installed calculation process imports no
  repository tests.
* The installed pairwise result is **3 distinct amino-acid pairs**, with
  **9/15 = 0.60** original query nucleotide coverage,
  **3/5 = 0.60** reference amino-acid coverage, and **identity 1**. The actual
  original query intervals are `[0,3)`, `[3,6)`, `[6,9)` and the corresponding
  reference intervals are `[0,1)`, `[1,2)`, `[2,3)`.
* A second fixture changes only the asserted subject SHA256 to 64 zeroes and
  coherently rebinds the enclosing scientific-input source digest and length.
  The adapter returns **partial** with null pair count, paired coverages and
  pairwise identity. Diagnostics and acquisition requirements explicitly retain
  `homology_subject_sequence_identity_conflict`. Native hit count, lengths and
  E-value remain available, the complete normalized/native artifact data are
  unchanged, and the conflicting assertion remains in saved supplied values.
* Changing only the native E-value from **0** to **1,000,000** changes the native
  E-value projection while leaving the entire pairwise union correspondence
  unchanged. E-value is not paired relevance.
* Recalculating the disk-saved valid pairwise sheet exactly reproduces its
  components and leaves the sheet unchanged. During both saved-sheet checks,
  the adapter, parsers, metadata binders, subject validator and sheet builder
  are disabled. During all pure calculations, file I/O is denied by audit and
  sockets/native subprocess entry points are disabled. No denied operation was
  attempted.

## Retained evidence

* `run_verification.py`, `serialize_fixtures.py`, `verify_isolated.py`: actual
  build, fixture-serialization and installed-check scripts.
* `*-result.json`, `*.stdout`, `*.stderr`: commands, working directories, exit
  statuses, elapsed times and output. The temporary build/extraction directory
  was removed after the run; the wheel is retained here.
* `WHEEL.json`, `PACKAGE_SOURCE_SHA256.json`, `FIXTURE_PROVENANCE.json`: wheel,
  packaged-file, original fixture and exact supplied-source identities.
* `INSTALLED_TOOL_CONTRACTS.json`: both constructed library mode contracts.
* `retained_database/`: copied original input/native bytes and explicitly named
  `EXPECTED_*` comparison files, plus freshly produced `INSTALLED_*` results
  and `SAVED_SHEET.json`. No earlier output is reused as the new result.
* `pairwise_valid/`, `pairwise_conflicting_subject_sha256/`,
  `pairwise_evalue_only/`: complete serialized C4 inputs, exact native bytes,
  original source bytes and freshly calculated results. The valid case also
  retains its saved sheet and fresh recalculation.
* `verification.json`: complete machine-readable passed-check report.

No production issue was found by these bounded checks. The synthetic records do
not establish authenticated live service custody, arbitrary remote reference
membership, or general query-normalization proof.
