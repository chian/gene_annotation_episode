# hmmpress — proposed contract, preparation only

`hmmpress [-f] <hmmfile>` has one indexing operation, with explicit overwrite
policy. The exact bundled HMMER 3.4 executable is present. Full `src/hmmpress.c`
was read; `native/help_hmmpress` retains native help. This is an index preparation
operation, not a search or an annotation measurement.

Input role `models` is one complete, ordinary seekable, non-gzipped HMM database
file, containing one alphabet across records and a name for every model. Retain
all model occurrences and complete probability bodies. Native stdin is forbidden.
Output roles are `binary_models` (.h3m, HMMER3 binary core models), `ssi_index`
(.h3i, SSI offsets/name/accession index), `msv_profiles` (.h3f, optimized MSV
profiles), and `remaining_profiles` (.h3p, remaining optimized profiles), plus
complete stdout/stderr and execution receipt. The four files are one bundle
associated with the exact source occurrence, source checksum and original attempt.
Their suffixes alone do not establish this association.

Preserve native summary `model_count`, `primary_name_count`, `accession_count`
(integer records/keys, entire input database population), paths as native strings,
and actual file sizes in bytes. A summary without an accession clause means zero
accession keys in this known native grammar, not an unknown population. Retain
binary magic/version/byte order where independently decoded; an unsupported
binary payload has unknown decoded record count. It must not become zero records.
Source configures optimized profiles for local alignment and target length 400;
those are preparation parameters, not observed sequence lengths or search results.

Proposed pure reader:
`extract_hmmpress(*, input_models, stdout, outputs, operation, receipt) -> sheet`
with full common occurrence envelope and input model rows, native summary,
bundle members, decoding status and exact source-to-bundle relation.
`calculate_hmmpress(sheet, *, binary_format_contract, tolerances) -> calculations`
compares complete input occurrence count/name/accession populations to reported
counts, checks required member presence/nonempty/version compatibility, validates
decoded binary model identity/body equivalence where supported and SSI offsets
against the bound .h3m records. It reports check outcomes and bundle byte total.
It does not score confidence or infer search readiness solely from filenames.
Without a supported .h3f/.h3p decoder, their internal profile compatibility remains
unknown despite native process success; preserve their bytes for later validation.

Failures distinguish missing/invalid/mixed-alphabet source, duplicate primary
names/accessions, existing outputs, write failure, malformed binary, missing
bundle member, source mismatch and partial/failed execution. Native cleanup may
remove partial output. Native `open_dbfiles` error cleanup can remove existing
.h3m/.h3f/.h3p files even when overwrite was refused. Production must stage into
an isolated attempt directory, keeping caller inputs/previous bundles immutable;
`-f` applies only to explicitly selected attempt-local destinations.

Local prerequisites and handoff follow COMMON.md: exact executable, a private
staged ordinary input file, permitted output directory and caller-owned resource
allocation. A future preparation driver retains/seals all four outputs; the
preparation result worker populates this sheet and typed requested bundle facts.
No search-result observation publisher is involved. No live production binding,
pure binary reader, calculator or episode return is claimed here.

Native checkable example: `native/hmmpress_success` input is the 6,670-byte
`tiny_protein`/`TINY001` model from the retained hmmbuild example. Exit 0 reports
1 HMM, 1 primary name, 1 accession. Retained .h3m=2,725 bytes,
.h3i=165 bytes, .h3f=9,918 bytes, .h3p=3,216 bytes; total=16,024 bytes.
Its .h3m prefix is `baedede8` (little-endian HMMER3/f binary magic).
`native/hmmpress_duplicate` supplies the identical source record twice, retaining
two explicit input occurrences: exit 1 reports nonunique primary keys and no
successful bundle. Duplicate bytes must not collapse that failure into one model.
All executions used the retained local_jobs policy, 20GiB RAM/4GiB scratch/no wall
limit. Full outputs and receipt paths are inside each native example directory.
