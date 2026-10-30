Packet 440 establishes an actual usable h5py environment and two actual native
HDF5 Cooler-schema3 synthetic fixtures for the planned C1 reader and C3 producer.
It does not establish a working `analyze_chromatin_interactions` implementation.
Tool-count increment: **0**.

The existing selected interpreter is
`/home/chia/repos/gene_annotation_episode/reference/episode_tools/.venv/bin/python`,
resolving to `/usr/bin/python3.12`: CPython 3.12.3, 8,020,928 bytes, SHA-256
`e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f`.
Actual bounded imports and native read/write executions used NumPy 2.5.0,
h5py 3.16.0 and HDF5 2.0.0. Cooler was not available in that environment; no
Cooler reader or CLI ran. Nothing was installed, neither existing virtual
environment was changed, and no isolated software environment was needed.

[DEPENDENCIES.json](DEPENDENCIES.json) retains exact paths, resolved paths,
SHA-256 and sizes for the selected Python executable, its environment config,
all 106 h5py distribution files (17,228,411 bytes), all 932 NumPy distribution
files (57,016,488 bytes), package roots, versions, metadata and 53 loaded shared
library files. The generator rechecked 1,092 pin entries before writing; shared
library entries can also occur among distribution files. These are actual
existing dependency pins. A future C3 implementation must pin its own code once
that code exists; this packet supplies no invented implementation pins and
claims no immutable or hermetic production installation.

[FIXTURES.json](FIXTURES.json) contains both local file identities, explicit root
group `/`, every hand-declared expected array, all actual readback arrays and
native dtypes, attribute values/types, weights, reconstructed matrices and the
terminal verification receipts. These are local file facts, without Store
artifact authority. [EXPECTED_INPUTS.json](EXPECTED_INPUTS.json) records the
separate hand-worked synthetic expectations. The generator and verifier are
[generate_fixtures.py](generate_fixtures.py) and
[verify_fixtures.py](verify_fixtures.py); their exact executed copies are retained
as `selected_input.py` in the respective job directories.

| Actual native fixture, group `/` | Bytes | SHA-256 |
| --- | ---: | --- |
| [four-bin-raw-weighted.cool](fixture_generation/fixtures/four-bin-raw-weighted.cool) | 36,231 | `fb726490decc4e1e1d991d47a09e21d726d03e17b72c484d14b981fc87708aee` |
| [six-bin-all-full-windows.cool](fixture_generation/fixtures/six-bin-all-full-windows.cool) | 33,863 | `1f0b079a8c8a42e885e5c6cb9322f073870a9ba4b0c397276992341b005dfdfd` |

The four-bin file contains chrA, length 40 bp, bins of width 10 bp and exactly:

```text
4 2 6 0
2 4 2 2
6 2 4 2
0 2 2 4
```

Its supplied synthetic weight vector is `[1,2,1,2]`, with an explicit
multiplicative interpretation for future calculations. No balancing was run.
All ten upper cells are stored, including zero at `(0,3)`. There is no second
zero-valued upper cell available to omit without changing the requested matrix.
The six absent lower-triangle records are symmetric representations, not six
implicit zero measurements. Its `chrom_offset` is `[0,4]` and `bin1_offset` is
`[0,4,7,9,10]`.

The six-bin file contains chrA, length 60 bp, bins of width 10 bp, upper adjacent
contacts `[5,1,5,1,5]`, and all other mathematical contacts zero. It has no weight
column. It stores these six exact `(bin1,bin2,count)` rows:
`[(0,0,0),(0,1,5),(1,2,1),(2,3,5),(3,4,1),(4,5,5)]`.
The zero at `(0,0)` is explicit. Fifteen other upper cells, including `(0,2)`,
are omitted from the complete sparse representation: 15 unordered zero cells
or 25 directed zero cells. Its `chrom_offset` is `[0,6]` and `bin1_offset` is
`[0,2,3,4,5,6,6]`. These inputs support the planned all-full-window example;
no insulation, enrichment, boundary or annotation-score calculator ran here.

Both files have the required `format="HDF5::Cooler"`, integer
`format-version=3`, `bin-type="fixed"`, integer `bin-size=10`, and
`storage-mode="symmetric-upper"` root attributes. Additional attributes label
their synthetic origin. Scalar strings are variable-length UTF-8; chromosome
names are null-padded ASCII `|S4`; coordinates and counts are little-endian
int32; bin IDs and indexes are little-endian int64; the four-bin weights are
float64. `bins/chrom` is the native integer-backed enum `{"chrA":0}`. The
format choices follow the official [Cooler schema3 specification](https://cooler.readthedocs.io/en/latest/schema.html)
and [h5py string documentation](https://docs.h5py.org/en/stable/strings.html).
Exact retained primary-source and implementation-evidence identities are in
[SOURCES.json](SOURCES.json).

The independent readback job imported neither the generator nor a production
chromatin reader. It read every array in full and compared it with the separate
expected values. It verified attributes, dtypes, chromosome enum, coordinate
coverage, equal table lengths, ordered unique upper pixels, exact CSR index
relationships, terminal offsets, full matrix reconstruction, supplied weights
and the explicit-zero/sparse-omission distinction. It verified that the files
have no external links, virtual datasets or external raw storage. Both input
file hashes remained unchanged after readback. This verifies these two fixture
serializations, not a general production parser or failure-handling adapter.

All four selected jobs reached terminal, quiescent exit 0 through the existing
`local_jobs`/`native_lifecycle` path. Every job verified 21,474,836,480 bytes RAM,
zero swap and `RuntimeMaxUSec=infinity`, with a 4,294,967,296-byte scratch policy.
Scratch is monitored with possible overshoot and a per-file size limit; it is
not an aggregate filesystem quota. Actual durable handles, native receipts,
process IDs, stdout/stderr, source pins and selected requests remain on disk.
No job was restarted after an observation timeout. The packet-local runner
only calls the existing launch/status/wait functions and adds no scheduler.

| Job | Durable handle | Original systemd service | Observed scratch bytes |
| --- | --- | --- | ---: |
| Dependency probe | [handle](dependency_probe/handle.json) | `gene-local-job-c538025f2991466b8ec00380c1ede805.service` | 634,880 |
| HDF5 generation | [handle](fixture_generation/handle.json) | `gene-local-job-1d7b8d6f747c4793ac757a6424be23cb.service` | 126,976 |
| Independent readback | [handle](fixture_verification/handle.json) | `gene-local-job-d6068dd79266461a8b9dd062f1da2f69.service` | 77,824 |
| Handoff assembly | [handle](handoff_build/handle.json) | `gene-local-job-186d05b05778457f8ae47f1431e42b4d.service` | 700,416 |

Every job's pinned infrastructure, selected script and interpreter bytes matched
before and after execution. The top-level dependency, fixture and source
manifests are byte-for-byte copies of the terminal handoff-build outputs.
Repository-level Git status/diff checks could not run because this directory is
not a Git checkout; no Git validation is claimed.

HIC is still separate required format work and is not established here. Also
unverified here are Cooler-library agreement, schema2/multi-resolution/variable
bins, malformed or partial native inputs, production C1 parsing, C2
calculations, C3 producer integration, typed result communication and the full
episode path. No biological observations were generated or acquired. No
production/shared/literature/scoring/prompt/accounting files were edited.

The original supplied goal attachment was read in full first and its SHA-256
verified as `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
The objective and all sixteen design principles were reread verbatim after
substantial source examination and again after native verification, before
completion. AGENTS.md, packet439 SOURCES.md and CONTRACT sections 1–4 and 7
were read; those contract sections were reread after the final goal reset.
No repository GOAL.md was read, copied or used. Historical implementation
documents remain implementation evidence and do not redefine the goal.
