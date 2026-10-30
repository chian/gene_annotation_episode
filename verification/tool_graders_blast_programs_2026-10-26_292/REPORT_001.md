# Five local paired-BLAST graders: implementation and verification

The numerical scoring-sheet fields and the functions that populate and
calculate them are implemented for local two-sequence blastn, blastp, blastx,
tblastn and tblastx. The actual tool information, execution/capture binding,
retained results and requested numerical returns are connected to the existing
episode structure. Filled sheets and forms are verification examples.

The five fixed rows are A-L069-blastn-pairwise, A-L069-blastp-pairwise,
A-L069-blastx-pairwise, A-L069-tblastn-pairwise and
A-L069-tblastx-pairwise. Database identification rows and other native programs
remain separate unfinished work. This report does not claim every tool or
resource in the goal is complete.

## Fields and functions

The complete sheet retains the selected original search, native report data,
original hit/HSP ordinals and actual query/reference descriptors. The
descriptors contain complete sequence lengths and explicit selected intervals.
The separate calculator computes per-HSP and union components, keeping native
measurements intact. Its fields include paired/identical/substituted positions,
gaps, native scores, correspondence, full and selected coverage numerators and
denominators, duplicate mappings and conflicting mappings. E-value is preserved
as a native quantity and is not a paired-relevance factor. A conflicting union
identity is unavailable; overlapping HSP scores are not summed.

`parse_blast_report_collection` handles the declared native JSON/table/archive
format and retains all original supported searches. It performs no I/O or
selection. `populate_blast_pairwise_sheet` accepts that search and explicit
operand descriptors. `calculate_blast_pairwise_components` consumes the saved
sheet without acquiring data or running BLAST. Shared geometry distinguishes
actual JSON translated-frame conventions from directional table endpoints.

The native driver executes one selected supplied pair and retains the actual
inputs, software identity, options, native output, logs and receipt. The local
binding preserves the original handoff and caller allocation. The result
operation captures that attempt and calls the separate deterministic functions
within its existing completed action. Complete numerical data is stored;
only requested rows and measurements cross each episode boundary.

Publication retains one stable comparison observation per actual HSP. Union
views create no additional scientific observation. Another metric selection
does not create a new source, HSP or evidence gain. Original return forms and
action receipts are validated against saved facts without recalculation.
Validated practical completion sets future expected gain to zero immediately
while preserving the final actual gain and original observation history.

The actual library index contains all five names and substantive instructions.
Root's separate frozen-retrieval check recovered the complete 9,505-byte
instruction section across six requested pages. This is library retrieval
evidence; it is not substituted for execution or numerical verification.

## Verification boundaries

All native jobs, deterministic workers and tests use `.venv/bin/python`
through the existing local binding, with 20 GiB RAM, 4 GiB scratch and no wall
cap. No local database BLAST, installation, API or HPC job was performed.

| Evidence | Result | Scope |
| --- | ---: | --- |
| 293 check003 | 173 passed | Full original report collection, native ordinals, identity, malformed siblings and format handling. |
| 294 checks_004 | 139 passed | Producer contracts and numerical sheet/calculator, using 20 actual retained native jobs across all five programs. |
| 295 checks_004 | 506 passed | Shared geometry and existing BLAST/BV-BRC numerical regressions. |
| 295 checks_005 | 68 passed | Additional native coordinate/reconciliation checks. This overlaps the 506 checks. |
| 296 final_checks | 117 passed | Local selected launch, handoff, actual five-program capture, failure and replay behavior. |
| 297 check002 | 75 passed | Retained numerical storage, requested projections, exact sequence/source identity and stable HSP observations. |
| 297 check003 / check004 | 1 / 23 passed | Added malformed-sibling case and final native/union completeness checks; overlapping runs. |
| 298 final_checks | 97 passed | Complete reverse-BLASTX Workflow, all five binding schemas, requested returns, forwarding, replay, practical endpoint and shared regressions. |
| 299 checks_003 | 34 passed | Existing API/result regression fixtures repaired against current ownership/scoring contracts; separate from the five new graders. |

The complete Workflow example is BLASTX. The other four programs have actual
native producer/capture and numerical checks plus shared binding/return-path
verification; this is not a claim of a separate complete Workflow run for
every program. No configured-model scientific investigation was performed.

The 298 source snapshot covers production Python, method_loop and selected
tests. Its original knowledge-directory path was wrong. That fact remains in
its report; root's separate retained library check and a supplemental actual
index/instruction hash record supply the library evidence. No original
verification manifest was silently rewritten.

The original broader 295 regression run remains 226 passed, 15 failed and five
errors. The 15 obsolete test expectations were repaired and passed in 299.
The five errors were a source-provenance assertion after concurrent edits;
301 is repeating only that module in an isolated source snapshot. These are
not presented as an all-suite pass.

## Numerical verification examples

| Actual native example | Numerical answer |
| --- | --- |
| Gapped BLASTP | 253 columns; 243 pairs; 238 identities; five substitutions; ten reference gaps; query coverage 243/253; reference coverage 243/243; paired identity 238/243; native bit score 486.878. |
| BLASTN selected forward interval | 180 paired nt; full query length 240 gives 180/240; selected length 180 gives 180/180. |
| Reverse BLASTX | 80 amino-acid pairs correspond to 240/244 query nt and 80/80 reference aa. |
| Reverse TBLASTN | 80 amino-acid pairs correspond to 80/80 query aa and 240/243 reference nt. |
| TBLASTX | All ten HSPs retained; first HSP has 80 pairs and 240/243 nt coverage on both operands. Competing mappings leave aggregate identity unavailable. |
| Full selected reverse-BLASTX Workflow | 62 amino-acid pairs, 186 aligned query nt, full coverage 186/244, selected coverage 186/186, native bit score 132.494. |

The full Workflow has exactly 13 selected actions and 13 local observations.
Three requested result selections share one source and one HSP observation.
Later selections gain no new scientific credit. Only requested numerical
fields reach the receiving parent; full measurements remain stored.

## Remaining work

Workload 300 is connecting the newly retained native HSP observations to the
existing selected-column inspection operation. The three alignment-site scope
rows remain outside the progress tally until that connection is verified.
The new paired-BLAST graders do not themselves claim that inspection path.

Database BLAST metadata/identification, PSI/DELTA/RPS/VDB semantics, API/HPC
deployment, other required tool families and existing generic communication
gaps remain required. Literature graders, evidence-axis scoring and W05 are
unchanged. Permanent requirements and the 308-row scope remain unchanged.
