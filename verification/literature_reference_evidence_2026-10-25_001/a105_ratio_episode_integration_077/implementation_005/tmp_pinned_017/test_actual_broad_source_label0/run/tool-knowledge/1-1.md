# Native BLAST database searches

## Selected work and ownership

Select one explicit HPC binding for psiblast, deltablast, rpsblast, rpstblastn,
blastn_vdb or tblastn_vdb. The scientific parent supplies the job, scope,
constraints and requested typed return. Launch and its HPC child retain their
existing choices. `child_tool_info` supplies the real operation information;
`evidence_axis` and `thought_pattern` remain independent construction slots.
This manual is not an episode implementation or an executable deployment.

The native database job has a closed software/input/database/options/output
contract. A supplied query sequence, CLUSTAL MSA or scoremat ASN text suffices;
no candidate annotation or public query identifier is required. The compiler
preserves selected options and emits one native command. Sequence databases,
profile databases and VDB datasets have different meanings and separate result
sheets. The supplied-pair BLAST path remains a distinct operation.

## Preparation and invocation

Use actual prepared file manifests and exact software identities from the
selected resource. No compiler or producer installs software, creates a
database/index, resolves an accession, downloads data or changes resources.
DELTA requires a protein target and a separate DELTA-prepared domain database.
RPS requires a prepared profile database. VDB requires prepared local datasets
and retained actual offline configuration, not an accession plus an assumed
network setting. Runtime library/search settings must be explicit.

The configured producer is invoked as
`python -B -m gene_annotation_episode.native_blast_database_driver PLAN`.
The existing PBS wrapper owns the allocation and submission. The plan retains
the exact logical request and pre-submission identity; the producer obtains its
actual execution identity from `PBS_JOBID`. A failed or unsealed attempt never
authorizes another invocation. An explicit retry remains a separate selected
resource action under the existing practical contract.

The producer manifest inventories every regular file in the deployed module
root, plus the selected canonical interpreter and explicitly supplied runtime
files. The driver checks the complete file set, each size and SHA-256, and its
actual running module/interpreter locations. The manifest lives outside that
inventory. Matching files establishes prelaunch identity, not complete external
dependency closure or deployment on another node. Deployment/import/native-run
verification remains required.

PSSM input validation requires the selected deployment's scoremat parser and
its Biopython dependency. The parser must be a verified package entry and its
actual import location must match that entry. Missing dependencies return
`producer_input_parser_unavailable` with the retained input; they do not imply
malformed PSSM content or authorize another parser, installation or retry.

Aurora software, runtime, inputs, databases, logs, caches and runs stay under
`/lus/flare/projects/BioReason-Aurora-Test`; new jobs charge `EpiCalib`.
The local 20 GiB RAM and 4 GiB scratch allowance permits synthetic engineering
checks, with no wall cap. It does not authorize local database BLAST.

## Query and output selection

PSI accepts protein FASTA, CLUSTAL or protein PSSM; DELTA and RPS accept protein
FASTA; translated RPS and blastn_vdb accept nucleotide FASTA; tblastn_vdb accepts
protein FASTA or PSSM containing its actual query Seq-entry. Preserve all FASTA
records. MSA master selection is explicit and zero-based. Null stays null;
`ignore_msa_master` does not establish an effective master. The producer checks
input framing without manufacturing a biological master identity.

Select complete stdout and stderr files and one JSON15 or tabular6/7 report.
Tables require exact ordered fields and delimiter. No format is guessed from a
filename, and no omitted field/default is inserted. Optional PSI/DELTA ASN and
ASCII checkpoint outputs use separate initially empty family directories. Every
regular file within each family is retained recursively. No checkpoint filename
supplies biological round, stage, membership or convergence.

Metadata descriptor validation and scientific metadata interpretation are
separate. Unknown schema strings are valid custody declarations. Even declared
JSON metadata is retained without parsing by this producer. Preparation receipts,
input-manifest receipts, database metadata sidecars and offline configuration
carry opaque format labels unless an explicit later parser or extractor contract establishes
their format. Selected sidecar roles and exact file identities remain explicit.

## Monitoring and retained results

The native subprocess runs once with closed stdin, captured stdout/stderr and
explicit environment and attempt-local working/output/tmp/cache paths. File
identities are measured before launch; immutable shared database volumes are
not copied into every attempt. A sealed bundle records actual process exit,
native elapsed seconds and each complete retained artifact's size/SHA-256.
Native elapsed seconds cover the monotonic interval around the subprocess;
they are not queue wait, wrapper duration or total turnaround.

Existing resource monitoring supplies selected native status and log windows.
Liveness alone establishes no productive throughput, convergence or scientific
completion. No monitoring schedule or stopping policy is added here.

Nonzero native exits can preserve valid partial files. Returncode zero with a
missing required report is a producer failure, not a successful zero-hit search.
An absent optional checkpoint family is `not_emitted`. Complete byte custody
does not establish valid scientific syntax or a complete native document.

## Separate result parsers and integration limits

The result acquisition path must authenticate the original requested job, PBS attempt and
plan digest; acquire complete sealed artifacts; and independently verify every
file's length and digest. Its source-qualified parsers and metadata extractors supply the distinct
sequence-database, profile, iteration/PSSM and VDB sheets/calculators. Profile
masters are model representatives, not invented biological references. Unknown
rounds, effective MSA masters and sample/feature associations stay unavailable.

This producer creates no numerical annotation score or biological observation.
Result publication, immediate-child typed returns, credit, practical endpoint
completion and continuation remain separate existing responsibilities. The
producer implementation and synthetic checks alone establish neither a working
HPC binding nor the full episode/result/return path. The root-owned knowledge
index must explicitly register this manual when the corresponding binding is
integrated; this file does not grant execution permissions.
