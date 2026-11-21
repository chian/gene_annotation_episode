# A102 structure measurement: the parser, the grader and sheet, the naming, the measurements reader, the credit copy

Status: library built and checked directly, 2026-11-21 (no real run, no head yet). LIB = `gene_annotation_episode/episodic_workflow/episode_support`.
Design: `a102_tree.md` ("The search and its measurement"). Check scripts and data: `runs/a102_measure_check/` (not versioned).

## Step zero (SOP Step 12): what exists and is called, what is new and why

| Function written | The existing function it calls | Why new |
| --- | --- | --- |
| `readers/protein_structure/foldseek_result.parse_foldseek_result` | none | no reader of the Foldseek server result existed (`a102_inventory.md` section 2 lists structure FILE readers only) |
| `grading/structural_homology_evidence/structure_search_sheet.grade_structure_search`, `measure_hits`, `measure_hit` | `calculations.protein_structure_calculations.fit_ca_transform` (the superposition), `scoring.geometry` (B), unchanged | the sheet of a search; `_fit` is only the call adapter: `fit_ca_transform` takes the protein-structure sheet's contract records (`CoordinatePair`, `ResolvedPairSelection`) and the numerical tolerances (`NUMERICAL`, it has no defaults), so `_fit` builds them for the aligned pairs (one explicit selection of all, every C-alpha present) and applies the returned `y @ R + t` to get the distances |
| `tools/structure_search/structural_homology_evidence/uniprot_hit_names.name_hits`, `lookup`, `product_name` | `acquisition.structural_homology_evidence.acquisition.PublicClients.uniprot_search` (the installed UniProt client, a `SourceSnapshot` with request, transport and bytes); the A102 `differential_credit` for the settling picture | the naming of structure hits (mirror of A101 `bvbrc_hit_metadata.name_hits`) |
| `grading/structural_homology_evidence/differential_credit.py` | none (A102's own copy of A101's axis-neutral arithmetic: `differential_credit`, `standing`, `lead_pair`, `test_ceiling`, `site_test_ceiling`, `bound_partner_test_ceiling`, `sheet_weight`) | A101's module names A101's families; left out: msa, MetaCATS, cluster, dataset rule, evidence weights, `CLUSTER_PSEUDO_COUNT` (no A102 counterpart in round 1) |
| `grading/structural_homology_evidence/candidate_measurements.py`: `held_sources`, `candidate_measurements`, `candidate_standing`, `candidate_table`, `held_searches`, `test_name`, `search_rows` | `tool_grading_artifacts.source_tool_grading_entries` of THIS folder (same function and record shape as A101's), the custody reader's `refs`, `get`, `validate_scope` | A102's reader of A102's sheet |

Not in the A102 `tool_grading_artifacts.py`: `record_grading_product` (A101's labels a retained grading as a `tool_grading_sheet` data product, in `LIB/records/data_products.py` terms). The A102 file has `retain_tool_grading` and `source_tool_grading_entries` only, and imports `records.structural_homology_evidence.domain`. The caller that labels the grading needs that function (it is not axis-specific: it reads `grading['sheet']['schema']` only).

## The rule

One test is one graded source: `structure_search:foldseek:tmalign:<database>@<source reference>`. A candidate is `product:<UniProt recommended protein name>`. A hit's value is B = `scoring.geometry(distances, target_length, dbLen)` = [2n/(L_target + L_reference)] / [1 + (RMSD/2 A)^2]: n and the distances from the server's aligned pairs after a least-squares superposition of the hit's C-alpha on the model's; L_target is the supplied target sequence's length (the target stays the denominator), L_reference the hit's `dbLen`. A candidate's value in the test is the mean B of its hits (replicates). A hit with fewer than 3 usable pairs, or a non-unique superposition, has no value (recorded with its reason), never zero. The grader holds no threshold; the model's facts (origin, accession, mean pLDDT, residues covered, file hash) weigh nothing. `geometry` takes only `distances`, `target_length`, `reference_length` and computes n and the RMSD itself; nothing else is passed. The sheet `a102_structure_search_sheet_v1` is described in the docstrings of `structure_search_sheet.py`.

Naming rule (A101's `name_hits`, same batch logic): hits in rank order, batches of 100, after each batch the candidate picture of the hits named so far (one test, mean B, admitted when above 0); stop when a batch admits no new product and moves no candidate by more than 0.01 (`settled`), or when all are named (`all_named`); never-asked hits are `not_asked`. Credit: the owner's differential credit (`differential_credit.py`).

The request: `PublicClients.uniprot_search('accession:A OR accession:B OR ...', size=n)` = `GET https://rest.uniprot.org/uniprotkb/search?query=accession%3AP0A9X9+OR+accession%3AP0A9Y1+OR+accession%3AP36995&size=3&format=json` (verified live 2026-11-21: HTTP 200, `x-total-results: 3`, 45,679 bytes, whole entries; the client takes no `fields`). The sibling `GET https://rest.uniprot.org/uniprotkb/accessions?accessions=P0A9X9,P0A9Y1,P36995&fields=accession,protein_name,ec,go_id,annotation_score,reviewed&format=tsv` also answered (200, 0.5 s) but its `Protein names` column joins recommended, short and alternative names in one string (`Cold shock protein CspA (CSP-A) (7.4 kDa cold shock protein) (CS7.4)`), so it was not used. The installed client sets its own headers (no name, email or key); the "browser-like User-Agent" was not applied because the client takes none (UniProt does not need one; the AlphaFold DB file download did).

## The Foldseek README statement (verified)

Fetched 2026-11-21 from `https://raw.githubusercontent.com/steineggerlab/foldseek/master/README.md` (saved `runs/a102_measure_check/foldseek_README.md`, line 177): "If alignment type is set to tmalign (`--alignment-type 1`), the results will be sorted by the TMscore normalized by query length. The TMscore is used for reporting two fields: the e-value=(qTMscore+tTMscore)/2 and the score=(qTMscore*100). All output fields (e.g., pident, fident, and alnlen) are calculated based on the TMalign alignment." Kept as `score_as_reported`, `eval_as_reported`. Not recomputed (UNVERIFIED by recomputation; the self hit gives score 100, eval 1, consistent).

## The `tCa` finding (direct check of the stored results)

`tCa` covers the WHOLE target chain, not only `dbStartPos..dbEndPos`: in all 976 hits of the afdb-swissprot search of the CspA model and in all 548 hits of the stored pdb100 result, `len(tCa)/3 == len(tSeq) == dbLen`, including the 863 and 530 hits with `dbStartPos > 1` or `dbEndPos < dbLen`. Examples: `AF-P36995-F1-model_v6` (`tCa` 71 residues, `dbLen` 71, aligned 1 to 70, 70 aligned residues); `AF-P72366-F1-model_v6` (68, 68, aligned 1 to 67); pdb100 `3i2z-assembly3.cif.gz_A` (71, 71, aligned 2 to 71); `6ktc-assembly1.cif.gz_A` (74, 74, aligned 3 to 73, 71 residues). So aligned target residue `i` takes `tCa[3(i-1):3i]`. The parser also checks the aligned letters against the query sequence and `tSeq` (all 976 and 548 pass), and that the target string of an AlphaFold hit is `AF-<accession>[-<isoform>]-F<n>-model_v<n>`: 32 of the 976 are isoforms (`AF-Q41188-2-F1-model_v6`), whose entry accession is the base one.

## Direct-check numbers (not a real run)

Data: CspA AlphaFold model `AF-P0A9X9-F1-model_v6.pdb` (70 residues, mean pLDDT 88.44; one Foldseek ticket, `afdb-swissprot`, `tmalign`, 976 hits; `runs/a102_measure_check/foldseek/`), `check_all.py`, output `check_all_output.txt`. `measure_hits` over 976 hits: 42 s (the schema checks of `fit_ca_transform` per pair dominate). No aligned pair was dropped (the model covers all 70 residues); all 976 hits have a value (minimum B 0.0255, median 0.190).

Top 10 hits (server order; product names only for the two accessions held in the stored UniProt reply, see the limit below):

| rank | accession | product | aligned pairs | RMSD (A) | B | score / eval as reported | seqId |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | P0A9X9 (self) | Cold shock protein CspA | 70 | 0.0001 | 1.0000 | 100 / 1 | 100 |
| 2 | P0A9Y1 | Cold shock protein CspA | 70 | 0.1508 | 0.9943 | 99 / 0.9974 | 100 |
| 3 | P0A9Y0 | not asked here | 70 | 0.1677 | 0.9930 | 99 / 0.9968 | 100 |
| 4 | P0A9Y2 | not asked here | 70 | 0.2995 | 0.9781 | 99 / 0.9902 | 100 |
| 5 | P0A9Y4 | not asked here | 70 | 0.3109 | 0.9764 | 98 / 0.9894 | 100 |
| 6 | Q46664 | not asked here | 70 | 0.3130 | 0.9761 | 98 / 0.9890 | 100 |
| 7 | P0A9Y5 | not asked here | 70 | 0.3179 | 0.9754 | 98 / 0.9888 | 100 |
| 8 | P0A9Y3 | not asked here | 70 | 0.3304 | 0.9734 | 98 / 0.9879 | 100 |
| 9 | P0A981 | not asked here | 70 | 0.3645 | 0.9679 | 98 / 0.9861 | 72.8 |
| 10 | P0A979 | not asked here | 70 | 0.3848 | 0.9643 | 98 / 0.9847 | 72.8 |

Self hit: RMSD 0.00012 A (the coordinates are given to 0.001 A), B 0.999999996 = 2 x 70 / (70 + 70) x 1/(1 + 0). The self hit is the target's own model in the database: it enters like any hit as a CspA candidate (B 1.0); `scoring.grade_comparison` rejects self copies as ineligible, and the head must decide whether this axis does the same (not decided here).

One hit recomputed by hand (numpy Kabsch, independent of `fit_ca_transform`; `check_all.py`): ranks 1, 2, 5 and 500 equal the sheet (RMSD and B), largest difference 2.8e-17; rank 500 (`Q7VJY4`: 62 pairs, RMSD 2.5487 A, B 0.18388).

Reader over a stored custody (a fake in-memory store holding the retained grading made by A102's `retain_tool_grading`): `candidate_measurements` gives one measurement per named hit and the test `structure_search:foldseek:tmalign:afdb-swissprot@source_1`; the reader's score of every candidate equals the sheet's `mean_B`; `held_searches` gives `('afdb-swissprot', <model sha256>)`.

### What the live naming did and did not show (LIMIT)

The check allowed 6 UniProt requests; two went to verifying the request forms. The naming of the real 976 hits then asked 4 batches of 100 (400 hits) and had NOT settled after the fourth (the picture kept changing: new products and moved means in every batch), so a real run asks all 10 batches of 100 for this search (about 40 s with the 3 s spacing), and the budget ended with it. The check script saved the four replies only after the loop, so they were lost when it stopped at the budget: no live product table for the 976 hits exists. The rest of the numbers above use a REPLAY of the one stored real reply (`runs/a102_measure_check/uniprot/probe1.json`: P0A9X9, P0A9Y1, P36995): 3 hits named (2 recommended names: "Cold shock protein CspA" for P0A9X9 and P0A9Y1, "Cold shock-like protein CspB" for P36995), the naming record `{'named': 200, 'not_asked': 776, 'batches': 2, 'stopped': 'settled'}` is that of the replay and means nothing for a live run.

Candidate table of the replay (2 candidates in all): `Cold shock protein CspA` 2 hits, mean B 0.9972; `Cold shock-like protein CspB` 1 hit, mean B 0.9045. Credit of that one test (entries only): 1.9017 = 0.9972 + 0.9045 (SHEET_WEIGHT 1); its `test_ceiling` from an empty list: 2.0 (two candidates, weight 1). The credit does not exceed the ceiling.
