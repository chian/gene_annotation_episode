# Alignment-site fields, functions and existing episode paths

The reusable numerical fields, extraction functions, calculators and requested
typed returns are implemented for reference-position selection and received
NCBI BLAST HSP column selection. This report records the verified implementation
before the separate workload 300 extension for newly retained native paired
BLAST observations. Filled sheets below are verification examples.

The fixed scope rows remain A-L064-native-pairwise, A-L064-blast-hsp and
A-L064-mapping-correspondence. This report does not claim every producer or
resource route is complete. In particular, the new `native_blast_pairwise`
producer requires an additional retained-source binding to `result.blast.hsp`.
The fixed progress tally remains unchanged here pending that work.

## Implemented responsibilities

- `alignment_site_inputs.py` defines and fills reference-position sheets from
  supplied Biopython alignments, phmmer alignments and minimap2 PAF records.
- `alignment_site_mapping.py` maps selected local intervals through actual
  original operand ancestry, retaining strand, repeated positions and split
  codons. Missing ancestry is explicitly unavailable.
- `blast_hsp_site_inputs.py` defines and fills selected alignment-column sheets
  from received NCBI HSPs. It retains full supplied HSP data separately from the
  selected window and uses the actual BLAST JSON coordinate convention.
- The two calculator modules compute counts and ratios from saved sheets.
  Coverage and identity retain their numerical numerator and denominator.
  Full native alignment scores are not apportioned to selected positions.
- `alignment_site_native.py` binds original records, source artifacts, operand
  identities, processing units and native versions to those pure functions.
- `alignment_site_action_records.py` binds requested returns to an actual
  completed own operation and original received information. Equal sequence
  length alone does not prove source identity.
- `alignment_site_returns.py` projects only fields requested by the parent.
  Frozen closure checks compare saved facts without recalculating a score.
- Existing scientific-child tool, service and return paths consume these
  interfaces. No new episode type, root execution tool, annotation formula,
  literature grader, model loop or stopping rule is introduced.

`sequence.sites` retains its existing comparison result. `result.blast.hsp`
remains a view of an explicitly received HSP; it creates no new scientific
observation. Sheet construction and return formatting add no completed action.

## Verification

Every listed test run used `.venv/bin/python` through the existing local job
binding with 20 GiB RAM, 4 GiB scratch and no wall-time cap. These runs overlap;
their counts must not be added together.

| Evidence group | Passing checks | What it establishes |
| --- | ---: | --- |
| 285 run_004 | 71 | Pure reference-position extraction/calculation; retained PAF cases from all six presets. |
| 286 attempt_004 | 258 | Selected BLAST columns and existing BLAST regressions. |
| 287 run_005 | 103 | Exact requested projection, closed schemas, missingness and frozen returns. |
| 288 run_004 | 65 | Source/operand identity, original producer operations and publication custody. |
| 289 check003 | 12 | Scientific-child selection, own action, requested parent return and replay, including retained native BLAST bytes. |
| 291 check005 | 15 | Actual phmmer acquisition/publication and selected-site paths; one source file changed during this run. |
| 291 check006 | 9 | Subsequent focused phmmer checks on unchanged tracked sources. |
| Root 284 check006 | 95 | Current selected-site publication, own-action and Workflow regressions plus frozen closing-form and phmmer metadata checks; no tracked source changes. |

The 291 check005 source change is retained in its receipt; it is not presented
as a frozen-source run. Later checks are identified separately. The baseline
manifest records the exact before/after hashes of the 95-check root run.

## Checkable numerical examples

| Example | Extracted fields and calculated values |
| --- | --- |
| Actual Biopython DNA alignment, requested positions [2,0,2] | Three returned requests, two unique positions, one duplicate, two paired and identical positions; identity 2/2; query coverage 2/8. |
| Actual Biopython no-alignment result | Four requested positions outside alignment, zero paired positions; identity unavailable with denominator zero; query coverage 0/4. |
| Retained NCBI BLAST HSP | 86 columns, 71 pairs, 31 identities, 40 substitutions, four query gaps and eleven reference gaps; paired identity 31/71; query coverage 71/253. |
| Retained minimap2 forward mapping | Requested positions map to query positions [1999,2003,null]; two pairs, one query gap, one three-base insertion; selected alignment identity 2/6. |
| Retained phmmer ANGEL2 window [197,203) | Six pairs, two identities and four substitutions; identity 2/6; query coverage 6/253; reference coverage 6/544. |

The NCBI Workflow example is an offline API-protocol fixture using retained
native numerical output. It adapts the query title to the actual test input;
it does not establish a new live NCBI RID or authentication. All native HSPs
and their original numerical values remain retained.

The phmmer Workflow includes one actual small native execution and its original
retained result. Its tested launch route is the existing flat homology route;
it does not prove the newer resource-specific branch or detached execution.
The native engine version is taken from the original HMMER operation metadata,
not the parser version. Unknown quality encoding preserves characters and
leaves numerical quality unavailable.

Saved-sheet recalculation, same-length wrong operands, missing strings,
malformed geometry, empty windows, repeated requests, original-source ancestry,
received-before-action authorization and frozen-return tampering are covered
by the listed focused checks. Scripted episode decisions are not claims about
configured-model scientific benefit or final annotation correctness.

## Remaining integration

Workload 300 connects the new 297/298 native paired-BLAST result records to the
existing selected-column operation. It must preserve actual JSON versus
tabular coordinate conventions and source identities and verify the existing
scientific-child return. This is a producer connection, not a new sheet formula.

API/HPC deployment claims, other unfinished fixed inventory rows, generic
TASK/STEERING gaps, W05 and literature grading remain outside this verification.
No scope row, historical receipt, original observation or immutable goal is
changed by this report.
