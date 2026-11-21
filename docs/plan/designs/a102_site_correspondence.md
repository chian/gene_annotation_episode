# A102 `site_correspondence` (row P2): the rule, the step zero, what was verified live, the direct-check numbers

Status: library built and checked directly, 2026-11-21 (no real run, no head wiring: the head's `task.py` calls it later). LIB =
`gene_annotation_episode/episodic_workflow/episode_support`. Design: `a102_tree.md` (row P2). Check scripts and data:
`runs/a102_site_check/` (not versioned).

Why: a matching fold with the catalytic residues present supports the candidate (TM0936); a matching fold that lacks the
candidate's zinc-coordinating residues does not (EnvC against LytM). The fold search cannot tell the members of a family apart;
this test can.

## The rule

Inputs: one held graded structure search of the target (its sheet `a102_structure_search_sheet_v1`, its raw Foldseek result with
the hits' alignments, `tSeq` and C-alpha `tCa`, and the model it used) and ONE site source: `annotated` or `catalytic`.

* Hits asked: not a control, with a product and a B (the hits that can enter a candidate's mean), in rank order.
* Site source `annotated`: UniProt `ACT_SITE`, `BINDING`, `SITE` features of the hit's accession; each position of a range is one
  required residue (a position covered by several features is one residue, its types listed). Region types are not requested.
* Site source `catalytic`: M-CSA catalytic residues of an accession that is an M-CSA reference entry (UniProt numbering); no
  homologue lists.
* Per required residue at hit position r with hit residue h = `tSeq[r]`: (a) r aligned to a target position q in the search's
  alignment? No: ABSENT, score 0, stays in the denominator. (b) class match 1 if target residue = h or the two share a role class
  (`CHEMICAL_ROLES`: DE, KR, FWY, STY, NQ, CM, AGS; S is in two classes), else 0. (c) distance d between the model C-alpha at q and
  the hit C-alpha at r after the search's superposition of ALL usable aligned pairs (`structure_search_sheet._fit`, the adapter
  `measure_hits` uses; never refit on site residues); kernel k = 1/(1+(d/1 A)^2). Residue score = class match x k.
* Residues dropped, with the reason on the sheet and out of the denominator: `position_beyond_hit_sequence`,
  `hit_numbering_is_an_isoform` (the hit is `AF-<acc>-<n>-F1`: sources number the canonical sequence), `residue_differs_from_source`
  (M-CSA states the residue letter), `target_position_has_no_coordinate`, `location_not_exact`.
* Hit F = mean residue score; hit E = B x F (B of the search sheet). Candidate value in the test = mean E of its hits with sites;
  a candidate none of whose hits has a site has NO measurement. The grader holds no threshold.
* Test name `site_correspondence:<site source>@<source reference>`; family `site_correspondence`, SHEET_WEIGHT 1.0 ("no real run
  yet: 1 until real runs give the family's typical strong value", SOP Step 6). Sheet `a102_site_correspondence_sheet_v1`.

## Step zero: what exists and is called, what is new and why

| Need | Called (existing) | New, and why |
| --- | --- | --- |
| superposition and distances | `structure_search_sheet._fit` (adapter of `calculations.protein_structure_calculations.fit_ca_transform`), the pair set of `measure_hit` | nothing: it is called on the same pairs; `_fit` is a private name, imported because no public one returns per-pair distances |
| residue role classes | `records/structural_homology_evidence/attachments.CHEMICAL_ROLES` (imported) | `class_match` (8 lines): the old `structure.reference_traits` code is bound to the old store and to a received alignment |
| kernel 1/(1+(d/1 A)^2) | `scoring.feature_sheet` holds it inline, with feature scale 1 A | `site_correspondence_sheet.kernel`; `feature_sheet` needs a comparison grade, witness records and the old store's transform hash and cannot be called for this; the check compares the two numerically (d = 0, 0.7, 2.5: equal to 12 places) |
| E = B F | the rule of `feature_sheet` (E = base x F) | applied with B read from the search sheet |
| parsed hits, model C-alpha, target sequence, graded-search rows, result/model products | `foldseek_result.parse_foldseek_result`, `foldseek_search.model_positions`, `target_sequence`, `graded_rows`, `RESULTS_KIND` | nothing |
| HTTP | `target_model_sources._request` (same helper and User-Agent), `uniprot_hit_names` constants `BATCH`, `SPACING_SECONDS`, `SEARCH_URL` | `tools/.../site_annotations.py`: the two site requests and their parsing |
| retention | `retain_tool_grading`, `record_grading_product`, `source_tool_grading_entries`, `record_product`, `structure_search_child._failed/_choose` | data product kind `functional_site_annotations` (EDAM data_1277 Protein features, format_3464 JSON; EDAM.tsv read 2026-11-21: data_1321 Protein features (sites) is obsolete) |
| measurement and credit | `candidate_measurements._read`, `differential_credit` | added: the site sheet branch, `site_test_name`, `site_rows`, `held_site_tests`; family `site_correspondence`; `site_test_ceiling` |

## Verified live (2026-11-21)

* UniProt: `GET https://rest.uniprot.org/uniprotkb/search?query=accession:A OR accession:B ...&size=n&format=json&fields=accession,ft_act_site,ft_binding,ft_site`: HTTP 200, 0.6 s, 8,162 bytes for P0A7G6, P00918, P0A9X9. Features carry `type` ("Active site", "Binding site", "Site"), `location.start/end.{value,modifier}`, optional `ligand.{name,id}` (`ChEBI:CHEBI:30616` for ATP; "substrate" has no id) and `evidences[].evidenceCode` (repeated codes: kept as a sorted distinct set). RecA: Binding site 67-74 ATP; CspA: none; P00918: Active site 64, Binding 94, 96, 119 (Zn, CHEBI:29105), 198-199 (substrate), Sites 7, 62, 67, 92.
* M-CSA: `GET https://www.ebi.ac.uk/thornton-srv/m-csa/api/residues/?format=json` (the request the code uses): HTTP 200, 5,248 residues, 5.9 MB, 4 s, one request for all accessions; `residue_sequences[]` = `{uniprot_id, code, resid, is_reference}` (4,969 with a UniProt id, 989 reference ids; codes include `Sec`). `resid` is the 1-based UniProt position: for P00918 (His64, His94, His96, Glu106, His119, Thr198) and P00720 (Glu11, Asp20) the letter at `resid` of the UniProt sequence equals `code` in all 8. The filter `entries/?entries.proteins.sequences.uniprot_ids=P00918` gives the same residues for one id (with `is_reference_uniprot_id` true), but with three ids in one request the entries came back without `residue_sequences` and `is_reference_uniprot_id` false, so the filter cannot be batched. The per-accession form was therefore not needed and not used; the check's "10 highest-B hits" limit did not apply: the one catalogue request covers every hit.
* Request counts spent: UniProt 18 of 30 (2 probes; per target 4 naming batches + 4 site batches), M-CSA 5 of 12 (3 probes + 1 per target), Foldseek 1 ticket of 2 (RecA).

## Direct-check numbers (not a real run)

Limit of the check: the hits were named in the first 4 batches (400 hits) only, not by `name_hits`' settling rule, to stay inside the UniProt budget: the other hits of each search are `not_asked` on the search sheet (CspA 571, RecA 600) and so are not asked for sites. A real run asks sites for every hit the search named, in rank order, in batches of 100, with no stopping rule of its own (stopping is the yield estimator's).

### CspA (stored result, 976 hits, model AF-P0A9X9)

`annotated`: 404 hits asked, 47 with sites, 9 of 69 candidates measured, 60 without any site. Only non-family hits have site features: lin-28 homologs (BINDING 8 residues each, absent in CspA: F 0), CcmE (2 BINDING residues, absent), EfpL (1 SITE, absent), Y-box-binding protein 1 (SITE residues in the cold shock domain: 3 residues, 1 aligned, F 0.27 to 0.93). No cold shock protein hit has a feature at all: they get no measurement (not a zero), as expected. 27 asked hits are isoform models and dropped their residues (`hit_numbering_is_an_isoform`); 4 hits had features but none usable. `catalytic`: 0 of 404 hits has an M-CSA reference residue; no candidate measured.

### RecA (new Foldseek ticket, 1000 hits, model AF-P0A7G6, `runs/a102_site_check/reca/`)

`annotated`: 399 hits asked (the self hit, rank 1, is the control and is not asked), 397 with sites, 3 candidates measured. `catalytic`: RecA is not an M-CSA reference entry: 0 hits with sites.

Top 10 hits with sites (ranks 2 to 11; every one has BINDING 67-74, ligand CHEBI:30616 ATP, 8 residues, none absent, none dropped):

| rank | accession | product | F | B | E |
| --- | --- | --- | --- | --- | --- |
| 2 | B7M9D6 | Protein RecA | 0.9880 | 0.9319 | 0.9206 |
| 3 | A7ZQC8 | Protein RecA | 0.9411 | 0.8525 | 0.8023 |
| 4 | B5Z2B0 | Protein RecA | 0.9725 | 0.8752 | 0.8512 |
| 5 | B7N6S9 | Protein RecA | 0.9892 | 0.8821 | 0.8726 |
| 6 | Q31X64 | Protein RecA | 0.9015 | 0.8052 | 0.7259 |
| 7 | Q32CM9 | Protein RecA | 0.9507 | 0.7895 | 0.7506 |
| 8 | B7UHB7 | Protein RecA | 0.8660 | 0.7781 | 0.6738 |
| 9 | B7LEB1 | Protein RecA | 0.8590 | 0.7049 | 0.6055 |
| 10 | B7MYJ9 | Protein RecA | 0.7942 | 0.6028 | 0.4787 |
| 11 | B7NSH9 | Protein RecA | 0.6775 | 0.5575 | 0.3777 |

One hit by hand (numpy Kabsch on all 353 aligned pairs, independent of `fit_ca_transform`, the parser and the grader; `hand_check.py`): B7NSH9: RMSD 1.781778 A, B 0.557512 (= sheet), residues 67 to 74 (G P E S S G K T) each aligned to the same target position with the same residue, class match 1, distances 0.5512, 0.6968, 0.7953, 0.8211, 0.6986, 0.6816, 0.6029, 0.6837 A, kernels 0.7670 ... 0.6814, F 0.67745, E 0.377687; the sheet gives the same, largest difference 3.3e-16. Also CspA P62961 (Y-box-binding protein 1): SITE 63, 217, 218 (217 and 218 absent in the target); sheet F 0.271578, E 0.053625 = hand.

Candidate table of this test, RecA (product, hits with sites / hits asked, mean E, search mean B):

| product | hits with sites | mean E | search mean B |
| --- | --- | --- | --- |
| Protein RecA | 395 / 397 | 0.603 | 0.663 |
| Protein RecA 1 | 1 / 1 | 0.452 | 0.549 |
| Protein RecA 2 | 1 / 1 | 0.596 | 0.615 |

CspA (9 measured; 60 candidates have no measurement): Y-box-binding protein 1 8/9 hits, mean E 0.101 (mean F 0.487); the eight others (lin-28 family four names, CcmE three names, EfpL) have mean E 0.0 (all their site residues are absent in the target).

### How the test separates candidates the fold search had close together

CspA: "Y-box-binding protein 1" (search mean B 0.203, 9 hits) and "Cytochrome c-type biogenesis protein CcmE" (0.206, 17 hits) differ by 0.003 in the search; in this test 0.101 against 0.0 (CcmE's two heme-binding residues are absent in CspA; Y-box's cold-shock-domain site residues are in place). "Elongation factor protein EfpL" (0.207) is also 0.0, so the site test does not separate CcmE from EfpL: both lack their machinery. RecA: "Protein RecA 2" (B 0.615) and "Protein RecA" (0.663) are 0.048 apart; sites 0.596 against 0.603 (0.007 apart): the site test narrows rather than widens this pair; "Protein RecA 1" (0.549) is 0.452, further below (0.151 from "Protein RecA").

### Credit and ceiling (A102 copies, source order = search then site test)

* RecA: search test credit 1.8258 (3 candidates); `site_test_ceiling` before the site test 2.0 (3 listed candidates, weight 1); the rise from the `annotated` test 0.3016 (credit 2.1274); below the ceiling.
* CspA: search test credit 36.6322 (69 candidates); ceiling before 1190.0 (69 listed: 69^2 // 4); rise 0.8113 (credit 37.4435). The ceiling is a bound over listed pairs (value 0 or w at each vertex), very loose here because only 9 of the 69 can have a value; it cannot know which candidates' hits carry sites before the request is made.
* `site_test_ceiling(standing, candidates)` is `w` once when at least two of the candidates are listed, else 0 (the differential of a test is the top two's only; the proof is in its docstring). The numbers of the two bullets above were computed under the pair sum (RecA 2.0 and CspA 1190.0 are the old ceilings; now 1.0 for both, since the rule changed on 2026-11-21; see `a102_head.md`, end). `vertex_maximum` and the closed form `w (u + k^2 // 4)` are deleted.
* The reader: `candidate_measurements` over the Store of the check gives 3 (RecA) and 9 (CspA) measurements for the site test; `held_site_tests` lists the (search source, site source) pairs; the request check returns `site_test_already_graded` with `choose_from` the other source, and `search_result_or_model_not_held` when the result or model is not held.
* Run time: the site grading repeats the superposition per hit that has site residues: RecA 102 s for 397 hits (353 residues), CspA 14 s (47 hits). `measure_hits` for the RecA search itself took 203 s (the existing path).

## Not verified, and what did not fit

* The AlphaFold model sequence equals the UniProt canonical sequence of the same entry (UniProt feature numbers assume it); nothing in the asked fields states a residue letter for UniProt features, so a changed sequence would not be caught. M-CSA features are checked against the hit letter.
* Isoform hits cannot be used (positions are canonical): their residues are dropped, and with them the hit's sites; no canonical-to-isoform mapping was built.
* UniProt site features of whole families can cover a different domain than the one that matched (lin-28 zinc knuckles against CspA): by the rule these residues are absent in the target, so they count against the candidate; the test does not separate "absent because another domain" from "absent because lost".
* No real run, no model-made request, no head wiring.

## Databases: only afdb-swissprot (2026-11-21, the lead's order)

Both site sources number the UniProt sequence. An AlphaFold DB hit is the canonical sequence, so its `tSeq` positions are UniProt
positions. A `pdb100` hit is numbered along the solved chain (`tSeq`, the resolved construct): UniProt positions would have to be mapped
to chain positions (RCSB `rcsb_polymer_entity_align` regions, unresolved residues shifting the numbering). That mapping is NOT built.
`check_site_correspondence_request` therefore refuses a search of any database outside `UNIPROT_NUMBERED` (`afdb-swissprot`) with the
code `site_sources_number_the_uniprot_sequence_and_this_search_has_chain_numbering`, and the head offers the tool only for such searches
(`credit.offered_site_pairs`). Null accessions of pdb100 hits are not handled: no pdb100 hit reaches the grader. The lead plans the mapping
with the bound-partner site source.
