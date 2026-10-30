# GeneTree pure-provider evidence

This workload implements the accepted three public functions in staging:
`extract_gene_tree_sheet`, `validate_gene_tree_sheet`, and
`calculate_gene_tree`. Extraction uses the actual shared provider, saved
validation uses the actual shared validator, and calculation calls the actual
shared dispatcher and calculators. No placeholder establishes this path.

The provider retains exactly one primary analysis per pure call, every supplied
associated document, original reader outcomes and explicit loci/member joins.
The two modes are `gene_tree` and `concatenated_sequence_loci`. A missing
alignment can coexist with a usable tree. Every full original parameter object
is retained with calculation output. The implementation does no acquisition,
file reading, process execution, model call or resource selection.

## Scientific behavior checked

The synthetic hand matrix is `A-CX`, `ATCX`, `ATGX`, `AT-X`. It has 4 rows and
4 columns: 16 cells, 2 gaps, gap fraction 2/16 = 0.125, 10 canonical protein
symbols and 4 ambiguous `X` symbols. Column 2 has canonical proportions 2/3 and
1/3, giving entropy 0.9182958340544896 bits. Rows 0 and 1 have 2 identical
positions among 2 canonical comparable positions, giving identity 1. The native
signed tree lengths sum to 1, including an explicit zero and a negative length.

A separate supplied correspondence maps 3 retained residues to an original
5-residue member. Original coverage is 3/5 = 0.6; final matrix occupancy is
3/4 = 0.75. Unknown original correspondence remains unavailable. The calculator
does not substitute final alignment length for the original denominator.

Checks cover duplicate native headers with distinct qualified input members;
individual and concatenated loci; selected segments; J-to-X substitution;
end trimming; explicit missing-locus gap filling; header tokenization and
duplicate suffixes; exact before/after digests; wrong references; incomplete
independent alignment data; and saved-sheet tampering. An all-gap final row
remains a final row. It does not establish removal by an earlier gap filter.
Unobserved alignment/filter stages remain unknown. Locus order and trim scope
come from supplied relationships, without basename or sequence-symbol inference.

Requested recipe does not become an observed engine, support method, or branch
unit. Requested alphabet likewise does not establish scientific metadata.
Complete evidenced members or applicable observed context can establish it;
unavailable/conflicting evidence preserves literal counts and gaps while
canonical quantities stay missing. Original requested parameters stay saved.

## Retained native examples

The two XML files are retained official repository examples, not newly executed
BV-BRC jobs or authenticated original-task output. Their complete source bytes,
parsed documents, annotations/properties, native branch/support observations,
and resulting components are preserved in exported examples.

| Native filename | SHA256 | Checked facts |
| --- | --- | --- |
| `Buchnera_acpS_fg_dna_raxml_hky85.xml` | `2a4eb93c64d2b9639139ea9b3a4b2aa9ee6a8bbad1ee640f63cdd3dde5008d88` | 17 tips, 15 internal nodes, 32 annotation records, 14 generic support values |
| `Buchnera_acpS_fg_dna_raxml_hky85_RAxML_tree_rell.xml` | `f37bab7cd3edcc632c5aac213f5cda199cd2d080a34276cde1d0eead5cfa2dc0` | 17 tips, 15 internal nodes, 32 annotation records, 14 generic support values |

Both native branch sums are 0.22376544591028014 in unknown native units.
Generic XML support retains an unknown method/scale; no normalized support is
invented from a filename. The known converter's inserted-zero and lost-zero-
support limitations remain qualifications. A separate synthetic XML check
distinguishes an explicit zero from an absent length and preserves root support
without inventing a parent edge. When the caller requires unavailable raw-tree
branch evidence, native XML observations and topology survive, while branch
length sums and distances remain unavailable.

## Receipts and replay

`TEST_RUN_*` contains actual captured test output. `FAILURE_HISTORY_001.md`
preserves earlier failures and explicitly labels the two shared-worker runs for
which only the actual tool transcript/message survives. Tests assert that all
provider/shared module imports come from staging. Tests use the absolute
repository `.venv/bin/python`, staging cwd, and staging `PYTHONPATH`.

`export_examples.py` creates a new `examples_NNN` directory per run. It saves
complete supplied operands, extraction results, calculation parameters and
components; an invalid complete-locus fixture; exact raw input bytes and their
artifact associations; metric summaries; and hashes of the actual code and
controlling documents. Export receipts identify the version. Earlier examples
remain unchanged when shared implementation changes.

After JSON serialization/reloading, validation and recalculation run with
ordinary file-read interfaces, sockets, URL opening and subprocess execution
disabled. Every output must equal its pre-serialization output. The test suite
also executes extraction under these guards. Recalculation uses saved supplied
objects without parsing native bytes again or fetching current metadata.

`SOURCE_AND_CONTRACT_HASHES_001.json` pins the examined original producer and
XML-converter files, two native examples, complete relevant boundary/implementation
contracts, and the reused BLAST design paths. Source findings are evidence of
the producer's behavior; they do not override the immutable user goal.

## Scope of the result

This is actual pure provider/shared-calculator integration with synthetic and
retained native data. It does not verify live GeneTree submission/execution,
deployed engine/source version, authenticated Store custody, C4 dispatch,
multiple-analysis wrapper assembly, results-library binding, or episode
communication. Those remain the root's production-integration work. The pure
provider never claims to authenticate the external content identifiers supplied
by a caller. No annotation-confidence score, W05 aggregation, prompt, episode
policy, registry, production file or goal/checklist change is included here.
