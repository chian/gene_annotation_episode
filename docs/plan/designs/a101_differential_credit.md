# A101 head: the differential credit and the annotation prototype

## The owner's words (verbatim; they govern)

- "(1) adding new possible annotations gets you a score (2) differentiating those scores (i.e., abs[S_A(t=i+1) - S_A(t=i)] vs abs[S_B(t=i+1) - S_B(t=1)] vs .... for all possibilities"
- "I mean that if S_A moves +0.5 and S_B only moves +0.1, then you have differentiated the lead candidates by 0.4"
- "i --> i+1 is related to the test in that turn, so they undergo the same test but credit differentiates, then that's added score. it encourages the same test to be applied clearly because that earns the differential credit and it encourages tests that differentiate results"
- "with only one candidate known there is no need to differentiate"
- "i resolved this by saying you need positive evidence to admit a possibility" and "so sometihgn random cannot be on the list at zero. i got rid of the possibity of zero basically"
- On a second candidate that entered earning the leader's score: "that's a little bit weird ... I think we shoudl fix that really ... adding a possiblity should be good in that we are searching and finding nsomething positive, but finding better possibilities is better, right?" (fixed in `differential_credit.py`: a candidate's entry earns its own score only; differentials count for tests after both candidates are on the list.)
- Credit and annotation score are different things: credit is what the head optimises (what was gained); the annotation score is a score per possible annotation.
- On BV-BRC's terms: "in bv-brc this is called product" and "in bv-brc annotation is the source of the name, and product is the name ... it is anti convention so you need to be careful".
- The order for this work: "wire it up into head and then run. this should be enough that it creates an annotation prototype".

## What was built

The head's credit (`HEAD/credit.py`) is `differential_credit` (the owner's formula, `LIB/grading/sequence_homology_evidence/differential_credit.py`, unchanged) over the candidate annotations that the graded sources the head holds give. The head's return carries those candidates with their scores, the leading one first: the annotation prototype.

HEAD = `gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence`; LIB = `gene_annotation_episode/episodic_workflow/episode_support`.

| function written | the existing function it calls |
| --- | --- |
| `candidate_measurements.held_sources(reader)` | the custody reader's `refs()` (receipt order) |
| `candidate_measurements._read` (the measurements, in the order of the sources) | `reader.validate_scope`, `source_tool_grading_entries` (the retained gradings of a source), `native_correspondence._regions` (the scope's regions of a target), `compile_native_sheet` (the value), `reader.subject_length` |
| `_database_search` (test, one `product` candidate per distinct function of a hit, unlabelled hits) | `route_native_grading` (the rows of each `hit_index`) |
| `_profile_scan` (test `profile_scan:<database>`, one `profile_family` per matched family) | `hmmer_comparisons` |
| `_pairwise` (test `pairwise:<program>`, the reference record as a `reference_sequence`) | `route_native_grading`, `reader.get` |
| `candidate_measurements.candidate_measurements(reader, scope, sources)` | `_read` |
| `candidate_measurements.candidate_table` (per target: candidates by score, tests, differentials, unlabelled hits, credit; the scope's credit) | `differential_credit` per target |
| `HEAD/credit.credit` | `candidate_table`, `held_sources` |
| `HEAD/credit.A101DifferentialCredit.as_record` (the definition record) | none (fixed fields) |
| `HEAD/yield_estimator.yield_controller` | `checked_yield_declaration`, `open_yield_controller` (kind `forecast`: `forecast_yield_controller.md`) |
| `HEAD/messages/internal_summary` (`candidates`, `tests`, `differentials`, `unlabelled_hit_count`, per target `axis_findings`) | `held_candidate_table`; `A101SequenceCredit.read_details` and `axis_features` stay: the head reports the residue-similarity index of the target as a feature (`axis_findings`) |
| `HEAD/messages/final_to_parent` (target rows gain `candidates`, `candidate_count`, `unlabelled_hit_count`, `differentials`) | the same table; `RecordForm`, `ChoiceField` of `method_loop` |

Decisions of reading.

- Arrival order: the order of `reader.refs()`, the custody's receipt order (the journal's receipts, by row id, each recorded once): the records the parent passed in, in the order given, then the head's own units in their order (and what a child returned, at the unit that returned it). The summary's `held_record_refs` is the same order (`records.refs()`). It is the same on each recomputation and on resume.
- A candidate is (vocabulary, identifier or else name). A Pfam family, a BV-BRC product and a reference sequence are three vocabularies and different candidates; nothing merges them yet (no mapping between a family and a product exists in the head).
- A database search is read by the content of its sheet (a `blast_database_sheet` with `reference_metadata`), not by provider: a hit's function is `reference_metadata[association.metadata_index].functions[...].function` (for BV-BRC the `product`; never the feature's `annotation`). A hit with no function is unlabelled and enters no measurement. The same function on several hits: replicates (the function takes their mean).
- The measurements of different targets are never compared: the credit is the sum over the targets of the credit of each target.
- `tests` shows, for each test, the number of admitted candidates it measured.
- The head's stopping is the forecast controller over the credit's ceilings (`forecast_yield_controller.md`). The continuation key is `A101:a101_native_sequence_correspondence` (the key `read_from_parent` gives a commission that names no `a101_task`; the declaration is checked against the credit definition record, not against the key).
- Credit definition record: kind `a101_differential_credit`, the version `A101DifferentialCredit.as_record()` gives (`a101_differential_credit_v3`, which carries the sheet weights). A run whose continuation settings carry another version's record fails with `scientific_yield_credit_definition_mismatch`. `A101SequenceCredit` (the index reader) keeps its own record (it is stamped in the index sheet's policy).

## Check against the lead's trial (a direct call on stored records of run D1, workspace `runs/bvbrc_a101_ws_D`; not a real run; launcher `runs/trial_D1`)

`candidate_measurements` (300 measurements) + `differential_credit`: five product candidates; scores and hit counts equal the lead's: "... => CspA (naming convention as in E.coli)" 0.9593 (55 hits), "... => CspB/CspG/CspI ..." 0.8212 (156), "Cold shock protein of CSP family" 0.8113 (53), "hypothetical protein" 0.8082 (2), "... => CspC ..." 0.8046 (34); no differentials; credit 4.204514. Unlabelled hits 0. The same module on the stored hmmscan of `runs/a101_hmmer_ws_1/store` (direct call): four `profile_family` candidates (ubiquitin PF00240.30 0.5046, Rad60-SLD 0.4000, Ribosomal_L40e 0.3489, Ubiquitin_2 0.1194), credit 1.3728 (the value of each is `compile_native_sheet` over its domains). The return form admits the candidate fields (a direct call of `RETURN_FORM.admit` with the D1 table).

## Run H1 (target and setting)

Target: E. coli K-12 CspA (UniProt P0A9X9, 70 residues; the same sequence as run D1's), fresh workspace `runs/a101_diff_ws_H1`, run `runs/a101_diff_run_H1` (run id `a101_diff_H1`), local and BV-BRC resources bound, Pfam configured, the global estimate ledger, the accumulation controller at cutoff 0.1 (the head's controller at that date).

## Run H1: observed (`runs/a101_diff_run_H1`, workspace `runs/a101_diff_ws_H1`, journal `journal_H1.sqlite3`, report `report_H1.json`; run id `a101_diff_H1`; 866 s; exit 0)

Actions the head's model chose, in order, with the credit after each unit (controller steps of the journal):

| unit | action | credit after | gain | estimator's upper bound of the next gain |
| --- | --- | --- | --- | --- |
| 0 | `hmmer_profile_scan` (pfam_a, the target, resource local) | 0.8198 | +0.8198 | 2.814 |
| 1 | child `bvbrc_blast` (blastp, bacteria-archaea, resource bvbrc, until extracted; one commission, the child waited and extracted) | 5.0243 | +4.2045 | 6.703 |
| 2 to 20 | 19 `reason` commits (assessments, interpretation accounts, a structural proposal) | 5.0243 | 0 each | 3.41, 3.04, 2.34, 1.90, 0.98, 1.37, 1.17, 0.48, 0.87, 0.73, 0.62, 0.54, 0.47, 0.40, 0.13, 0.11, 0.26, 0.20, 0.059 |

The estimator stopped the head (`ended_by yield_stop`, 21 units) when the upper bound fell to 0.059 (cost 0.1). 19 units followed the last gain. The model never chose a pairwise comparison; it chose no other search. One `Homology` submission was made (one job directory in `bvbrc_jobs`).

Credit rose by each new candidate's score: the scan admitted one family, CSD (PF00313.29), score 0.8198 (the credit rose 0.8198); the extract admitted five products with D1's scores and the credit rose 4.2045 (= 0.9593 + 0.8212 + 0.8113 + 0.8082 + 0.8046). No differential arose. The head's return (`stdout.log`): credit 5.0243; the target's finding carries `candidate_count` 6, `unlabelled_hit_count` 0, `differentials` [] and `candidates` (leading first): product "Cold shock protein of CSP family => CspA (naming convention as in E.coli)" 0.9593 (55 measurements); product "... => CspB/CspG/CspI ..." 0.8212 (156); profile_family CSD PF00313.29 0.8198 (1); product "Cold shock protein of CSP family" 0.8113 (53); "hypothetical protein" 0.8082 (2); "... => CspC ..." 0.8046 (34). The model's decision context from the second decision on showed `candidates` and `tests` (model call 2 and 26 of `model_calls_H1`).

19 units followed the last gain: the accumulation controller's bound fell slowly (and rose twice, at units 7, 10 and 18) because it was fitted to a first gain of 4.2 within a few units of real time. The forecast controller is the head's controller now.

## 2026-11-21: the credit is additive, weighted by the scoring sheet, and every episode supplies a ceiling

The owner's rule, verbatim: "the graders should additively add to the subscoring sheets and then the subscoring sheets additively add to the score".

What the code does (`LIB/grading/sequence_homology_evidence/differential_credit.py`):

- A candidate's value in one test is the mean of its replicates (the same function on several hits of that test), times the weight of the test's sheet family.
- A subscoring sheet is a test kind (the part of the test name before `@`). A candidate's sheet value is the SUM of its values over the tests of that kind.
- The candidate's score is the SUM of its sheet values.
- The scoring sheet weighs the sheets with stated weights, `SHEET_WEIGHT[family]`: one over the typical strong value of the family, so the typical strong result of each sheet counts about 1. The typical strong values are read from stored real runs of one target (E. coli CspA, 70 residues) and are to be re-derived as other targets accumulate.
- Entry (a candidate's own score, once, when it first has a value above zero) earns that score only. A differential is the difference of two candidates' values in one test, counted for tests after both candidates are on the list. Credit is the sum of the entries and the differentials; it never falls.
- One test is one graded source, `<kind>@<source reference>` (commit `f227c34a8`), so different jobs are never pooled as replicates.
- The alignment's measurement counts only new conserved distinguishing sites (`a101_conserved_sites.md`).
- Every episode's credit also supplies `ceiling` (commit `b755bea1a`; the runner checks it and journals the offered ceilings). `UNBOUNDED` is used where an action's gain truly has no limit. The owner's meaning: "UNBOUNDED filled in everywhere is bad; UNBOUNDED where truly unbounded is right".
