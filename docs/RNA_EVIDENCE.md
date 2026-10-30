# Native RNA evidence, not an RNA annotation pipeline

The owning Episode can select `public.rfam.model` to acquire one Rfam accession,
then select `rna.cmsearch` with a registered sequence and that actual model.
These are ordinary tools, reusable in any investigation. They introduce no
compulsory RNA stage, family selection, child Episode, biological acceptance
rule, or stopping condition. Reasoning still owns whether a match supports a
specific interpretation, whether its model/scope is appropriate, competing
explanations, and useful next work. A source family label is not an annotation
of the submitted sequence. More searches or reported hits earn no credit by
themselves.

## Model acquisition

`public.rfam.model {"accession":"RF00005"}` acquires the selected ASCII CM at
`https://rfam.org/family/RF00005/cm` and its JSON metadata at
`https://rfam.org/family/RF00005?content-type=application/json` through the public
Rfam API. Both HTTP bodies, requests, response metadata, retrieval times and
content hashes are retained. The resulting `model_ref` names a source-bound
family reference. Its biological `sequence_ref`, `molecule` and `length` are
null: CM `CLEN` is a number of model consensus positions, not the length of a
physical reference molecule. Header build/version, consensus length, accession,
model cutoffs and metadata remain available with their actual meanings.

A metadata transport failure preserves the already acquired usable model and
returns partial execution with its model reference and the specific failure.
Malformed optional metadata likewise preserves the model/source/family, with
`rfam_metadata_invalid_json` and the usable model reference in structured detail.
The adapter never adopts Rfam's metadata `search_command` or GA cutoff as a
target-annotation policy. Rfam model selection remains the Episode's decision.

## Selected native search

`rna.cmsearch` requires `subject_ref` and `model_ref`; the optional `parameters`
object exposes a bounded, documented subset of native options:

- `report_evalue` / `report_bitscore`: `-E` / `-T`.
- `inclusion_evalue` / `inclusion_bitscore`: `--incE` / `--incT`.
- `model_cutoff`: `ga`, `tc` or `nc`, selecting the corresponding native
  `--cut_*` option for both reporting and inclusion. It cannot be combined with
  separate thresholds because those are mutually exclusive native controls.
- `search_space_mb`: native `-Z`, measured in megabases. Omitted means native
  target-database search space, with both strands considered by default.
- `alignment_mode`: local (native default) or glocal (`-g`).
- `strand`: both (native default), top or bottom.
- `truncation`: default native terminal truncation handling, none
  (`--notrunc`), or any (`--anytrunc`).
- `acceleration`: default, max, nohmm, mid, rfam or hmmonly. Default is native
  database-size-dependent filtering, not an adapter-selected sensitivity rule.
- `force_cm`, `cyk`, `matrix_mb`, `sequence_matrix_mb`, `alignment_output`:
  native `--nohmmonly`, `--cyk`, `--mxsize`, `--smxsize`, and whether to omit
  alignment display with `--noali`.

Effective omitted threshold defaults are native reporting E=10 and inclusion
E=.01; both are explicitly passed. Default matrix limits are native 128 MB,
also explicitly passed. CPU is caller-owned, explicitly passed with `--cpu` so
`INFERNAL_NCPU` cannot silently replace it. Exact settings, command, executable
path/SHA256, native version/help, adapter version, model bytes/hash, submitted
FASTA/hash, full stdout, table and stderr are retained. Full native alignments
are retained by default, available through `source.read` on the result's source.
Raw output artifacts can also be exported with the ordinary artifact CLI.
There is no adapter work timeout or scientific retry.

The operand can be an actual registered input, feature, product, external
DNA/RNA reference or an external derivative. A declared protein operand is
incompatible with this nucleotide operation; unspecified input is processed
under the explicitly selected RNA CM without mutating its caller declaration
or creating a molecule classification. For an unspecified negative-strand
feature, RNA is the recorded orientation processing model. Known DNA and RNA
retain their respective reverse-complement semantics. Input-scope ownership
still applies; the adapter does not silently crop a whole operand to child
scope. An Episode can explicitly select a mapped sequence view when useful.

Native search runs in a worker outside a Store transaction. Immutable bytes and
settings cross that boundary. Publication, references and the ordinary durable
operation result are committed on the owner thread. Replaying an already
committed operation key returns that original result without another search or
publication. Cancellation before publication may leave an uncommitted local
calculation; recovery can repeat that calculation, never a committed operation.

## Coordinate and result meanings

Native `cmsearch` uses **query=model, target=sequence**. The optional closed
`observation.native_cmsearch` object retains those exact identities, all native
fmt3 fields, algorithm (`cm`/`hmm`), native model/sequence lengths, score/bias,
E-value, pass, GC, strand, truncation and inclusion marker. Only the native tool
publisher can supply this object; it is absent from model-authored observation
commit schemas. Actual native observations remain visible to scientific reasoning.

Native one-based inclusive sequence coordinates become one zero-based half-open
physical target interval: `[min(from,to)-1,max(from,to))`. Minus-strand native
coordinates and their direction are also retained. This interval is the only
physical operand interval; model consensus positions have their own explicitly
named `model_consensus_interval` and never become physical reference residues.
The existing framework operand role `query` means the investigated sequence;
the source explicitly records that this is the **native cmsearch target**.
The acquired model is `source_subject_refs`, not an assayed target molecule.

All reported rows survive, including native `?` (reported but not included)
rows. `!` is native inclusion metadata, not scientific approval. A malformed
later output row preserves already published valid rows and acquired source,
with typed partial-execution feedback. Native execution failures retain full
raw diagnostics plus exit code and bounded stdout/stderr diagnostic tails;
they create no fabricated successful observation.

A completed zero-hit search means **no reported match in this operand under
these recorded model/settings**, not whole-organism absence. Filter sensitivity,
model coverage, fragment ends, truncation and incomplete input remain scientific
considerations. Default matrix overflows can affect sensitivity; complete native
statistics are retained instead of inventing an absence conclusion.

## Caller resource configuration

The canonical defaults define `[local_tools] cmsearch_cpu=1`. No executable is
assumed. A caller can supply a TOML file containing:

```toml
[local_tools]
cmsearch_executable = "/caller/installation/bin/cmsearch"
cmsearch_cpu = 1
```

Use `--config file.toml` with the CLI, or pass `cmsearch_executable` and
`cmsearch_cpu` to `ToolRegistry`. The actual resource binding is shown in the
tool catalog; its initial value is persisted in the run manifest/SQLite settings.
Every native measurement retains its actual invocation resource identity. A
caller can select different resources for later work, including after resume;
this does not rescore, invalidate or rerun earlier committed work. Replaying an
existing operation returns its original result and resource provenance. Missing
installation is actionable operational feedback. No workstation path or
environment executable override is used.

## Observed native limitation and evidence limits

Infernal 1.1.5's `cm_pli_TargetIncludable` uses reporting `by_E` rather than
`inc_by_E` (`src/cm_pipeline.c:868–869`). Actual calibration with `-E10
--incT10000` marked the 68.8-bit tutorial match `!`, despite its displayed
inclusion setting. The adapter preserves that native result and reports the
fixed limitation code
`infernal_1_1_5_inclusion_uses_reporting_threshold_mode` when these modes differ;
it neither rewrites the flag nor blocks the requested scientific work. Using
matched bitscore reporting/inclusion modes in the reported-only calibration
produces `?` as expected. Native `--anytrunc` E-values have the native calibration
qualification, and max/nohmm modes disable truncation detection; these are
likewise recorded limitations, not acceptance rules.

Tests use the already acquired actual RF00001/RF00005 HTTP bodies (verified
against their acquisition hashes), native Infernal 1.1.5 binary (verified against
the build manifest), and a known sequence from `tutorial/mrum-tRNAs10.fa`.
Forward, reverse and cropped tutorial searches calibrate representation and
adapter behavior. Synthetic parser/error fixtures are labeled. They establish
no unknown-target annotation accuracy, biological benchmark, or model-driven
Episode effectiveness. No new public model download is needed for these saved
protocol checks; the live acquisition client remains separately identified.

Sources read: [Rfam API, family description and covariance-model endpoints](https://docs.rfam.org/en/latest/api.html),
Infernal 1.1.5 `documentation/man/cmsearch.man.in` (full),
`documentation/userguide/tabular.tex` (full), and the native inclusion function
above. Original native source/build and Rfam HTTP provenance remain in the
repository's `resources/software` and `validation/providers/rfam-native`.
