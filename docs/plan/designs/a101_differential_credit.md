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
| `HEAD/yield_estimator.yield_controller` | `checked_yield_declaration`, `open_yield_controller('accumulation', ...)` |
| `HEAD/messages/internal_summary` (`candidates`, `tests`, `differentials`, `unlabelled_hit_count`, per target `axis_findings`) | `held_candidate_table`; `A101SequenceCredit.read_details` and `axis_features` stay: the residue-similarity index is a reported feature of the target, no longer the credit |
| `HEAD/messages/final_to_parent` (target rows gain `candidates`, `candidate_count`, `unlabelled_hit_count`, `differentials`) | the same table; `RecordForm`, `ChoiceField` of `method_loop` |

Decisions of reading.

- Arrival order: the order of `reader.refs()`, the custody's receipt order (the journal's receipts, by row id, each recorded once): the records the parent passed in, in the order given, then the head's own units in their order (and what a child returned, at the unit that returned it). The summary's `held_record_refs` is the same order (`records.refs()`). It is the same on each recomputation and on resume.
- A candidate is (vocabulary, identifier or else name). A Pfam family, a BV-BRC product and a reference sequence are three vocabularies and different candidates; nothing merges them yet (no mapping between a family and a product exists in the head).
- A database search is read by the content of its sheet (a `blast_database_sheet` with `reference_metadata`), not by provider: a hit's function is `reference_metadata[association.metadata_index].functions[...].function` (for BV-BRC the `product`; never the feature's `annotation`). A hit with no function is unlabelled and enters no measurement. The same function on several hits: replicates (the function takes their mean).
- The measurements of different targets are never compared: the credit is the sum over the targets of the credit of each target.
- `tests` shows, for each test, the number of admitted candidates it measured.
- Cutoff of the accumulation controller: 0.1, in the credit's units (an admitted candidate earns up to 1; a differential earns the size of a gap). The episode continues while a unit is expected to earn more than 0.1, the move the owner's example calls small ("S_B only moves +0.1"). The continuation key stays `A101:a101_native_sequence_correspondence` (the key `read_from_parent` gives a commission that names no `a101_task`; the declaration is checked against the new definition record, not against the key).
- `HEAD/goal.py` also stated the old credit and was reworded.
- Credit definition record: kind `a101_differential_credit`, version `a101_differential_credit_v1`. `A101SequenceCredit` (the index reader) keeps its own record (it is stamped in the index sheet's policy).

## Check against the lead's trial (a direct call on stored records of run D1, workspace `runs/bvbrc_a101_ws_D`; not a real run; launcher `runs/trial_D1`)

`candidate_measurements` (300 measurements) + `differential_credit`: five product candidates; scores and hit counts equal the lead's: "... => CspA (naming convention as in E.coli)" 0.9593 (55 hits), "... => CspB/CspG/CspI ..." 0.8212 (156), "Cold shock protein of CSP family" 0.8113 (53), "hypothetical protein" 0.8082 (2), "... => CspC ..." 0.8046 (34); no differentials; credit 4.204514. Unlabelled hits 0. The same module on the stored hmmscan of `runs/a101_hmmer_ws_1/store` (direct call): four `profile_family` candidates (ubiquitin PF00240.30 0.5046, Rad60-SLD 0.4000, Ribosomal_L40e 0.3489, Ubiquitin_2 0.1194), credit 1.3728 (the value of each is `compile_native_sheet` over its domains). The return form admits the candidate fields (a direct call of `RETURN_FORM.admit` with the D1 table).

## Run H1: prediction (written before the run)

Target: E. coli K-12 CspA (UniProt P0A9X9, 70 residues; the same sequence as run D1's), fresh workspace `runs/a101_diff_ws_H1`, run `runs/a101_diff_run_H1` (run id `a101_diff_H1`), local and BV-BRC resources bound, Pfam configured, the global estimate ledger. Continuation: accumulation, cutoff 0.1.

- The model chooses among `hmmer_profile_scan`, `bvbrc_blast` and `reason`. I expect a profile scan and a BV-BRC search (one `Homology` submission), in either order; no pairwise comparison (no second held sequence).
- The scan: one Pfam family (the cold-shock domain, CSD) with a value near 0.9; the credit rises by that family's score at that unit.
- The BV-BRC search (as D1's, same sequence, same database): five `product` candidates admitted by the extract unit, with the scores of D1 (0.959, 0.821, 0.811, 0.808, 0.805), so the credit rises by about 4.2045 at the extract unit (the launch and wait units earn 0).
- Credit at the end near 4.2 + the family's score (about 5.1). No differential (no two listed candidates undergo a later common test: the family undergoes only the scan, the products only the search).
- The return: the leading candidate is the CspA product (0.959) unless the family scores higher (then the family leads and the CspA product is second); candidate_count 6; unlabelled 0.
- After the last gain the estimator stops the head after about 3 to 6 further units that earn nothing (the forecast must fall to 0.1; I cannot predict the number better).
