# Root review: standard native database BLAST plan 327

The proposed contract is [PROPOSED_PLAN_001.md](PROPOSED_PLAN_001.md).
It covers exactly A-L069-blastn-database, A-L069-blastp-database,
A-L069-blastx-database, A-L069-tblastn-database and A-L069-tblastx-database,
for their native HPC bindings. The existing API route obligations remain;
327 does not add API implementation work or change accounting.

Deliverables are field definitions, deterministic functions that populate fields
from retained outputs and explicit metadata, and separate calculators. Filled
sheets are runtime/test artifacts. This directory contains a plan only; root
approval and concrete ownership assignments precede implementation.

## Proposed decision

Approve a distinct operation/version family, native_blast_standard_database,
with five tools named native.<program>.database. Keep native6 v1, paired tools
and legacy API schemas, forms, calculations and histories unchanged.

The code does not support adding five enum values safely. Native6 lacks a
nucleotide sequence database kind, misclassifies three query molecules,
dispatches non-PSI/non-RPS population to VDB, and exposes sequence results only
inside an iteration wrapper. Standard5 needs direct top-level sequence results.

Reuse the public scientific functions unchanged:

- populate_blast_sequence_database_sheet supplies the scientific sheet from
  a source-qualified collection search and explicit operand/metadata bindings.
- calculate_blast_sequence_database_components calculates native measurements,
  correct full/selected coordinate geometry, hit/group/function populations,
  taxonomy, source quality and the existing conditional reference kernel.
- M317's public supplied-byte validator and registered query_identity and
  sequence_database metadata schemas can be reused without a native6 job shim.
- Existing native collection, FASTA/PSSM readers, PSSM calculator and the public
  native6 search-fact populator can receive their actual supported inputs.

## Four exclusive implementation boundaries

The main plan gives exact file paths, signatures, wire fields and consumers.
All files below are proposed future ownership, not edits made by 327.

| Owner | New paths under gene_annotation_episode/ | Concrete output consumed next |
| --- | --- | --- |
| N | native_blast_standard_database_contracts.py, _driver.py, _tool_info.py | Validated job/run plan/prepared-DB/bundle contracts; correct program/query/DB geometry; one selected native command; five real tool descriptions and callable contracts. |
| M | native_blast_standard_database_metadata.py | Pure supplied-byte preparation, exact search/query/reference metadata joins, full-sequence proofs and direct sequence-database sheets. No catalog I/O inside preparation/population. |
| R | native_blast_standard_database_calculators.py, _result_views.py, _result_worker.py | Closed field definitions/selectors; unchanged public scientific calculations in top-level sequence[]; original HSP addressing; immutable complete rows and small projections. Only worker entrypoint performs I/O. |
| E | native_blast_standard_database_acquisition.py, _result_publication.py, _results.py, _returns.py plus the explicitly listed shared host consumers | Original-attempt capture, frozen worker generation, exact biological query publication, actual child-owned results operation and immediate-parent typed returns. One owner makes additive shared-file changes after E321's accepted snapshot. |

The producer accepts prepared protein/nucleotide sequence databases and actual
FASTA inputs; tblastn also admits an explicitly supplied supported ASN text PSSM.
Reports are JSON15 or declared-field tabular6/7. The initial closed native option
matrix is explicit, including program incompatibilities. Database filtering,
extra input files, remote/native subject options, implicit database preparation
and arbitrary argv are not admitted by this proposed version.

## The geometry boundary that must survive publication

| Program | Query units | Reference units | Alignment units |
| --- | --- | --- | --- |
| blastn | nt | nt | nt |
| blastp | aa | aa | aa |
| blastx | nt | aa | aa |
| tblastn | aa | nt | aa |
| tblastx | nt | nt | aa |

A retained actual paired BLASTX JSON15 range example reports query_len=186
but has coordinates reaching 215 on the full 244-nt input. Its 62 paired aa
columns cover 186 nt; full-query coverage is 186/244. These bytes prove native
coordinate behavior, not database execution.

Preserve raw reported-axis HSP cells. For standard scientific publication,
resolve the existing sequence calculator's full-axis HSP component using its
original row_keys/component_index, including malformed preceding slots.
Expose separate qualified paired-unit counts and full-axis coverage fields.
Publish intervals and aligned-position counts from that same frozen qualified
component. Never relabel reported-axis coverage or use compact zip order.

Only actual HSP correspondence with an exact full-query or PSSM-master mapping
creates a biological observation. Native database hits do not automatically
create biological reference subjects. Function/taxonomy/census rows remain
numerical source facts; missing biological mapping yields source_only rows.

The return owner follows accepted 314/009 for the new standard row sources:
one row per (calculation_id,record_key), copying only authenticated received
cells; equal repeated cells deduplicate, conflicts fail specifically, and old
forms remain unchanged. No full-row lookup fills unreceived fields.

## Required interfaces from other work

M317 and R324 require **no new standard-mode work**. The plan names their exact
public reusable ports and excludes their private native6 dispatch/calculation
helpers. Workload325 convergence extraction is not a dependency.

Before E owns shared files, root supplies E321's accepted final publication
validator, immediate-child return authority, 314/009 received-cell semantics,
consumer-validation evidence and exact shared-file change list. E321 need not
add standard modes. The plan identifies every proposed shared consumer branch.

Later live execution additionally requires actual selected executable/version/
hash, producer package identity, complete prepared database inventory and
preparation provenance, resource paths and caller allocation. None is invented
from a catalog. Aurora storage remains BioReason-Aurora-Test; PBS charging is
EpiCalib; only the existing tracking file may be in Aurora home.

## Verification and limits

The main plan defines N1–N6, M1–M8, R1–R10 and E1–E10, with numerical oracles,
partial/missing/error cases, complete synthetic child-return flow and relevant
native6/paired/API compatibility checks. Later tests use .venv/bin/python through
local_jobs with 20 GiB RAM, 4 GiB scratch and no wall cap. No real database BLAST
is permitted locally, including tiny fixtures.

Two scientific limitations are explicit. Existing303 requires equality between
the report's database name and the supplied census identity; a native path versus
semantic-name difference can leave representation adjustment unavailable. The
plan does not rewrite either source or change the saved scientific schema; an
alias-aware scientific version needs separate root review if required. A CDS
function cannot be assigned to an entire genomic hit without an explicit
feature-level relationship outside the current whole-sequence calculation.

All five current rows and routes are copied, unchanged, into
[SCOPE_ROWS_SNAPSHOT.json](SCOPE_ROWS_SNAPSHOT.json). Inspection coverage and
the distinction between complete reads and mapped consumers are recorded in
[INSPECTION.json](INSPECTION.json).

No tests, scientific requests, native searches, HPC access/submissions, installs,
database downloads, production-code edits or accounting edits were performed.
