# A102 `partner_contacts` (rows P2 with ligand contacts, and P4): the rule, step zero, what was verified live, the direct-check numbers

Status: library built and checked directly, 2026-11-21 (no real run, no head wiring: the head's `task.py` calls it later; the job went
through a local stand-in for `execute_on_local_resource`, see "Not verified"). LIB = `gene_annotation_episode/episodic_workflow/episode_support`.
Check scripts and data: `runs/a102_partner_check/` (not versioned: `check.py`, `report.py`, `hand.py`, `cache/` the fetched assembly
files, `out_cspa2/`, `out_reca/`).

Why: the fold search cannot tell what a matching protein does with a partner. A solved structure shows it: "a methionine-bound homolog
localizes a different side-chain pocket"; "an arginine-bound comparator and modeled contact differences explain recognition"; the owner:
"Not everything is an enzyme ... functional pocket comparisons ... binding". CspA binds nucleic acid and has no annotated site in
UniProt, but its relatives are solved with DNA and RNA oligonucleotides: what a solved structure shows bound to a matched protein, and
whether the target has those contact residues in place, is evidence only this axis can give.

## The rule

Files: tool `tools/structure_search/structural_homology_evidence/partner_contacts.py` (check, unit, parsing), job program
`.../usalign_driver.py`, grader and sheets `grading/structural_homology_evidence/partner_contacts_sheet.py`, reader additions in
`candidate_measurements.py`, family and ceiling in `differential_credit.py`, kinds in `records/data_products.py`, the retained list
`forms/structural_homology_evidence/biolip_ligand_list/`.

* Request: `search_ref` (a held graded search of database `pdb100`) and `resource_id` (a bound local resource; the check needs it
  for the job). `check_partner_contacts_request(request, *, searches, analysed, resources, usalign_directory, python)` refuses, with
  field, code and `choose_from`: `search_is_not_a_held_graded_search`, `search_database_is_not_pdb100`,
  `search_result_sheet_metadata_or_model_not_held` (raw result, sheet, `search_hit_metadata` product or model), `search_already_analysed`
  (`candidate_measurements.held_partner_analyses` gives the search sources already analysed), `resource_not_bound`, `resource_not_local`,
  `program_missing`, `python_missing`. Called as the head calls `site_correspondence`, except that the unit is `async`
  (`await partner_contacts(ctx, search_ref=..., resource_id=...)`, as the `all_vs_all` tools are) because the job goes through
  `execute_on_local_resource`; `ctx.settings` holds `python_executable` and `usalign_executable_directory`.
* Hits asked: not a control, with a B, in rank order (a hit with no product still binds partners and enters test 2). One solved ENTRY
  FILE at a time (entry and assembly number as the hit target names it: `1mjc-assembly1.cif.gz_A`; an entry with several hit chains is
  fetched once), in batches of 10 files. Stopping rule (exact): after each batch the candidate picture of the hits done in BOTH tests
  is recomputed (`differential_credit` scores of the two tests' measurements); the unit stops when, after at least two batches, the batch
  admitted no new candidate in either test (no key outside the picture before it) and moved no candidate's value by more than
  `SETTLE` = 0.01 (`uniprot_hit_names.SETTLE`), or when all files are done; the first batch always has a second when files remain. Hits
  of files not reached are `not_asked`.
* Per file: fetch (`https://files.rcsb.org/download/<ID>-assembly<N>.cif.gz`, at most 2 a second, no name, email or key). A transfer
  over `MAX_BYTES` (8 MiB; known from `Content-Length` before the body is read) or an unpacked file over `MAX_UNPACKED_BYTES` (128 MiB) is
  recorded `too_large` and not asked. The unpacked mmCIF is kept through custody as data product `experimental_structure`.
* Molecules: `MMCIFParser(auth_chains=False)`: every polymer chain and every ligand instance is one label asym id. The hit chain is the
  polymer asym id whose AUTHOR chain id is the Foldseek label (`A-2` copies included). Partners: every other molecule with a heavy atom
  within `CONTACT_A` = 4.0 angstrom (<=) of a heavy atom of the hit chain: (a) hetero groups other than water (HOH, DOD) by chemical
  component id (kind `ligand`; a branched glycan counts each residue by its component id), (b) nucleic-acid chains (`dna`/`rna` from the entity's
  polymer type; a hybrid chain by the majority of its residue names), (c) other protein chains (and other polymers) as FACTS only (chain, whether the
  same entity, contact residue count). Partners of one key (`ligand:<id>`, `nucleic_acid:dna`, `nucleic_acid:rna`) are one partner of
  the hit chain: its contact residues are the union over its instances. `CONTACT_A` is the conventional heavy-atom contact distance;
  its source is UNVERIFIED (BioLiP's pages read state no distance).
* Additives: a ligand on BioLiP's published list is `additive: true` (recorded, no candidate, no site residues). No partner is flagged
  `unknown`: the list was retrieved (below).
* Correspondence: ONE local job per batch runs `usalign_driver` over a plan of pairs (target model with each hit chain of the batch:
  a PDB file of the chain's C-alpha atoms numbered 1..n in file order; the target's file numbers 1..L); per pair
  `USalign target.pdb hN.pdb -m -`, output parsed faithfully (both TM-scores with `normalized by length` and d0, RMSD, aligned length,
  Seq_ID, the aligned residue pairs from the two aligned strings against the C-alpha identifiers read from each file, rotation and
  translation as printed; the counts must equal the program's lengths and aligned length or the pair is `output_does_not_match_the_files`).
  The alignments of each batch are kept as `pairwise_structure_alignments`. No UniProt numbering is used anywhere.
* Residue score, exactly the sister test's: contact residue r (hit residue h) not aligned: absent (`outside_the_alignment` before the first or
  after the last aligned hit residue, else `within_the_alignment`), score 0, stays in the denominator; aligned to q: class match
  (`site_correspondence_sheet.class_match`) x `kernel(d)`, d = distance between the target C-alpha at q (after `X = t + u x`) and the hit
  C-alpha at r. A residue aligned to a target position with no coordinate is dropped (reason on the sheet, out of the denominator); a
  contact residue without a C-alpha is dropped (`hit_residue_has_no_c_alpha`).
  F(hit, partner) = mean over the partner's contact residues; F(hit) = mean over the union of the contact residues of the hit's
  NON-additive ligand and nucleic-acid partners; E = B x F with B the search sheet's B.
* TEST 1 `site_correspondence:partner_contacts@<source>`, sheet `a102_partner_contacts_sheet_v1`, source provider `partner_contacts`:
  product candidates; value = mean E(hit) over the product's hits with a functional partner; a product with none: no measurement.
  Family `site_correspondence` (existing weight).
* TEST 2 `bound_partner:pdb100@<source>`, sheet `a102_bound_partner_sheet_v1`, source provider `bound_partner`: candidates `ligand:<id>`,
  `nucleic_acid:dna|rna` (vocabularies `ligand` and `nucleic_acid`, added to `VOCABULARIES`); value = mean E(hit, partner) = B x F(hit, partner)
  over the hits bound to it. New family `bound_partner`, weight 1 ("no real run yet: 1 until real runs give the family's typical strong value").
* Sheets keep: per file (entry, assembly, url, status, download bytes and sha256, unpacked bytes, file ref), per hit chain (entry, chain,
  product, B, status, US-align TM-scores, RMSD, aligned length, partners with counts in place/absent outside/within, F, E, the contact residues
  one by one, protein partners as facts), per candidate of each test (hits, mean, mean F); totals (entries asked / too large / not obtained / not asked,
  hits with partners, candidates measured). The grader holds no threshold.

## Step zero: what exists and is called, what is new and why

| Need | Called (existing) | New, and why |
| --- | --- | --- |
| held searches | `site_correspondence.search_inputs`, `foldseek_search.graded_rows/model_positions/target_sequence`, kinds | `partner_search_inputs` adds the held hit-metadata product |
| residue score | `site_correspondence_sheet.class_match`, `kernel`, constants | nothing |
| hits' entry, assembly, chain | `foldseek_result.pdb_target` | nothing |
| stopping rule | `uniprot_hit_names.SETTLE`, `differential_credit` | the same idea applied to two tests (`picture`, `settled`) |
| job | `resource_local.execute_on_local_resource` (the inspection point), the staging pattern of `all_vs_all_run` | `usalign_driver.py`: stdlib program, plan in, one JSON out |
| custody and labels | `retain_tool_grading`, `record_grading_product`, `record_product` | kinds `experimental_structure`, `pairwise_structure_alignments` |
| files | Biopython 1.88 `MMCIFParser`, `MMCIF2Dict`, `NeighborSearch`; User-Agent and timeout of `target_model_sources` | `fetch_assembly` (the size cap needs a bounded read: `_request` reads the whole body) |
| failure vocabulary | `structure_search_child._failed` refuses codes outside `FAILURE_CODES` (not edited) | the unit's own `_failed` and `OWN_FAILURE_CODES` (as `all_vs_all_run`) |

## What was verified live (2026-11-21; no name, email or key; User-Agent as the library's)

* File URL: `https://files.rcsb.org/download/1MJC-assembly1.cif` HTTP 200 (`chemical/x-cif`, chunked, no length); `1mjc-assembly1.cif.gz` HTTP 200
  (`application/gzip`, with `Content-Length`: 17,126 B for 1MJC). The unit uses the `.cif.gz` form (the very file the Foldseek database was built
  from; the length is known before the body is read, so the size bound is a refusal before download).
* Chain labels: in the assembly files `_atom_site.auth_asym_id` carries the Foldseek label exactly, including symmetry copies: 2BH8-assembly1 has
  auth (and label) ids `A`, `B`, `A-2`, `B-2`; 4JBK-assembly3 has `C`, `C-3`, `H`, `H-3`; hit `2zts-assembly1.cif.gz_C-2` of the RecA search parsed and
  graded. A LIGAND carries the author id of its protein chain (1MJC: waters are label asym B with auth A; 3CMW: `E` to `S` hetero asyms with auth `A`), so
  the molecules cannot be told apart by author id: the label asym id is the molecule and the author id only selects the hit chain among the polymer
  asyms. The label asym id of 3CMW's protein is not its author id (label C = auth A).
* Biopython 1.88 reads these files (`auth_chains=False` gives the label asym ids including `A-2`; hetero residues of label asym ids are single molecules).
* BioLiP additive list: the BioLiP pages (`download.html`, `guide.html`, `whatsnew.html`, `readme_ligand.txt`) do not link or describe a list of
  non-biological ligands. PLIP's `config.py` (`biolip_list`, "BioLiP list of suspicious ligands from .../BioLiP/ligand_list (2014-07-10)") names it, and
  `https://zhanggroup.org/BioLiP/ligand_list` answers 200, 21,796 B, last modified 2024-11-05, two tab-separated columns (component id, name), 463 rows, sha256
  `e9b53b2b58657fa8fee3041560e841e85afcbba1f68879a0800799bfa0c7067b`. Retained with url, date and hash in `forms/structural_homology_evidence/biolip_ligand_list/`.
  Found: the list holds buffers, precipitants, sulfate, glycerol and also the monovalent ions NA, K, CL, heavy metals (AG, AU, HG, PB, ...), MSE and NAG; it does NOT
  hold MG, ZN, CA, MN, nucleotides (ADP, ATP, ANP, AGS, DTP) or HEM. The list is "suspicious ligands", not a statement of function: NA or CL near a binding site is flagged additive.

## Direct-check numbers (not a real run; limit of the check: 80 entry files per protein in rank order, the settling rule did not fire in 8 batches)

Stored pdb100 searches (`runs/a102_pdb100_check/out_*_pdb100.json`, models `cspa_model.pdb` 70 residues, AF-P0A7G6 353 residues). Entry files in the search: CspA 496 files for 548 hits;
RecA 858 hits. 80 files asked per protein (rank order).

| | CspA | RecA |
| --- | --- | --- |
| entry files asked / parsed / too large | 80 / 79 / 1 (4BTS-assembly1, 9,897,823 B) | 80 / 80 / 0 (largest 2,387,045 B) |
| hits in the asked files (asked hits) / hits with a functional partner | 87 / 22 | 86 / 44 |
| hits whose chain has protein partners (facts) | 28 | 26 |
| TEST 1: products measured / without measurement | 10 / 26 | 3 / 3 |
| TEST 2: partners measured | 6 | 13 |
| additive partners seen (hits) | GOL 3, SO4 3, NA 5, AG 4, CL 2, ACT 1, NO3 1, PB 1 ... | GOL 22, EDO 9, CL 5, MPD 4, FLC 4, IMD 3 ... |
| unit seconds (8 stand-in jobs of 0.1 s / 0.7-1.2 s) | 117 with 80 live downloads (49 on a rerun from the cached files) | 125 with 80 live downloads |

TEST 2 candidate tables (partner, hits, mean E, mean F; top 10 by mean E):

| CspA | hits | mean E | mean F |
| --- | --- | --- | --- |
| ligand:MG | 1 | 0.4911 | 0.6998 |
| nucleic_acid:rna | 17 | 0.2352 | 0.4437 |
| nucleic_acid:dna | 2 | 0.1711 | 0.4694 |
| ligand:WO4 | 1 | 0.0010 | 0.0038 |
| ligand:ZN | 4 | 0.0 | 0.0 |
| ligand:CU | 1 | 0.0 | 0.0 |

| RecA | hits | mean E | mean F |
| --- | --- | --- | --- |
| ligand:MN | 1 | 0.4781 | 0.8192 |
| nucleic_acid:dna | 3 | 0.4193 | 0.6575 |
| ligand:ALF | 1 | 0.3318 | 0.6310 |
| ligand:AGS | 11 | 0.2592 | 0.5110 |
| ligand:MG | 11 | 0.2532 | 0.6062 |
| ligand:ATP | 1 | 0.2295 | 0.5087 |
| ligand:ADP | 14 | 0.2023 | 0.4346 |
| ligand:ANP | 4 | 0.1736 | 0.4236 |
| ligand:DTP | 11 | 0.1667 | 0.3728 |
| ligand:CA | 2 | 0.1281 | 0.2243 |

(RecA's other three: NZW, NY5, O1E, one hit each.) As expected: nucleotides (ADP, ATP, ANP, AGS, DTP), magnesium, DNA. CspA: RNA from 17 hits (cold-shock proteins with
oligonucleotides) and DNA from 2; MG is one CspB chain (2I5M X); ZN comes from four hits of Y-box-binding protein 1 and lin-28 homolog A (zinc knuckles outside the cold-shock domain), CU from CusF, WO4 from a metal-binding protein: ions that are not the cold-shock domain's function, with E near 0 as the zinc and copper residues are absent or away from the target.

TEST 1 beside the search's B (product, hits with partners/asked, mean E, mean F | search hits, mean B):

| CspA | | |
| --- | --- | --- |
| Cold shock protein CspB | 2/16, 0.5395, 0.7377 | 17, 0.7500 |
| Y-box-binding protein 1 | 6/8, 0.3741, 0.7066 | 8, 0.5059 |
| Y-box-binding protein 2 | 2/2, 0.3365, 0.6261 | 2, 0.5362 |
| Lin-28 homolog B | 1/1, 0.2105, 0.4441 | 1, 0.4740 |
| RNA-binding protein Unr | 1/3, 0.1949, 0.3766 | 7, 0.3062 |
| Small ribosomal subunit protein uS12A | 2/2, 0.0707, 0.2683 | 5, 0.2201 |
| Protein lin-28 homolog A | 3/3, 0.0682, 0.1916 | 3, 0.3571 |
| Translation initiation factor 1A | 2/2, 0.0122, 0.0483 | 3, 0.2473 |
| Metal binding protein | 1/1, 0.0010, 0.0038 | 1, 0.2700 |
| Cation efflux system protein CusF | 1/4, 0.0, 0.0 | 4, 0.3230 |

| RecA | | |
| --- | --- | --- |
| Protein RecA | 35/57, 0.2241, 0.4540 | 69, 0.4317 |
| DNA repair and recombination protein RadA | 7/15, 0.0767, 0.2762 | 70, 0.2596 |
| KaiC domain-containing protein | 2/2, 0.0667, 0.2750 | 3, 0.2285 |

The 26 CspA products without a measurement include "Cold shock protein CspA" itself, "Cold shock-like protein CspC/CspA", the RNA chaperone: their solved structures show no
ligand or nucleic acid (free proteins). That is no zero: the test says nothing about them.

The best nucleic-acid hit of CspA (rank 12, 3PF5 chain B, "Cold shock protein CspB", B 0.7579, RNA, E 0.5879, F 0.7757; US-align TM 0.86515 normalised by the 70-residue target,
0.90039 by the 67-residue chain, RMSD 1.04, aligned 66): 9 contact residues, all aligned.

| hit residue (author number) | target position | target residue | class match | d (A) | kernel |
| --- | --- | --- | --- | --- | --- |
| K 7 | 10 | K | 1 | 0.158 | 0.976 |
| W 8 | 11 | W | 1 | 0.308 | 0.913 |
| N 10 | 13 | N | 1 | 0.815 | 0.601 |
| F 15 | 18 | F | 1 | 0.419 | 0.851 |
| F 17 | 20 | F | 1 | 0.176 | 0.970 |
| D 25 | 29 | D | 1 | 0.405 | 0.859 |
| F 27 | 31 | F | 1 | 0.358 | 0.887 |
| H 29 | 33 | H | 1 | 0.284 | 0.925 |
| Q 59 | 63 | A | 0 | 0.441 | 0.837 |

The aromatic and basic residues of CspA's nucleic-acid binding face that the literature names (K10, W11, F18, F20, F31, H33; F12, K16 and F34 are named too; this list is from memory,
UNVERIFIED) are among them except F12, K16 and F34, which this CspB-RNA contact set does not touch.

The best nucleotide hit of RecA (rank 1, 8GMS chain F, "Protein RecA", B 0.6682, AGS (ATP analogue), 2 instances, E 0.5937, F 0.8885; TM 0.91592 by the target, 0.9697 by the chain,
RMSD 1.35, aligned 333): 17 contact residues, all aligned, class match 1 each: hit residue (= target residue)/target position S 69/70, S 70/71, G 71/72, K 72/73, T 73/74, T 74/75 (the 67-74
P-loop of the sheet: `GPESSGKT`, numbered with the model's offset of 1), Y 103/104, F 217/218, S 240/241, K 248/249, N 249/250, K 250/251, I 251/252, A 252/253, A 253/254, P 254/255, Y 264/265;
distances 0.13 to 0.68 A, kernels 0.68 to 0.98.

One (hit, partner) recomputed by hand (`hand.py`: own mmCIF reading, brute-force numpy distances, US-align run directly on a chain file the script wrote, the printed rotation and translation applied):
RecA 8GMS F with AGS: F 0.8885067073 against the sheet's 0.8885065131 (difference 1.9e-7), E differs by 1.3e-7; CspA 3PF5 B with RNA: F differs by 2.2e-11, E by 1.6e-11 (the sheet reads coordinates as Biopython
float32). The first hand run of CspA differed (1.6e-4) because the script did not drop alternate locations; the library takes Biopython's selected atom of each disordered atom, the script the `A` altloc: they agree here.

## Credit and ceilings (A102 copies; order of tests: search, test 1, test 2)

| | CspA | RecA |
| --- | --- | --- |
| search test alone | 32.3159 (159 candidates) | 12.2487 (104 candidates) |
| + TEST 1 (rise) | 41.9558 (+9.6397) | 12.5635 (+0.3148) |
| + TEST 2 (rise) | 42.8543 (+0.8985) | 15.3895 (+2.8260) |
| ceiling before TEST 1 (`site_test_ceiling`, the search's products) | 6320 (159 listed: 159^2 // 4) | 2704 (104 listed) |
| ceiling before TEST 2 (`bound_partner_test_ceiling`) | 1.41e9 | 2.21e9 |

TEST 2's ceiling (`differential_credit.bound_partner_test_ceiling(held, partner_slots)`, proof in its docstring) is `w (max(slots - k, 0) + k^2 // 4)` with k the partner candidates already listed. The number of
partner candidates is NOT known before the unit runs: the held hit metadata (the RCSB reply of `pdb_chain_proteins.QUERY`) asks `polymer_entities` only, so it lists no non-polymer entity and no partner count;
the entries could not be skipped by it. The proved bound uses the machine bound of the unit: a file unpacks to at most `MAX_UNPACKED_BYTES` (128 MiB) and every atom row has at least 52 bytes (the smallest in the
fetched files is 91), so a file has at most `MAX_ATOMS_PER_FILE` = 2,581,110 molecules, and `partner_slots` = asked hits x that (CspA 548, RecA 858 hits). It is proved and extremely loose. If the head wants the
tight figure "one new partner per hit" (548, 858) that is a forecast, not a bound. Both rises are far below their ceilings. A tighter proof needs the entries' non-polymer entity counts (RCSB
`rcsb_entry_info.nonpolymer_entity_count` is a different request, not made) or a rule that caps partners per hit; none was invented.

## Not verified, and what did not fit

* The unit's job went through a stand-in for `execute_on_local_resource` (stages the inputs in a directory, runs the same command with the real driver); the real route (`job_access`, the slice, the staged artifact
  names) is exercised later in a real run. No head wiring; no model-made request.
* Not reached by the check: the settling rule's stop (80 files were all it asked), `JobFailed` paths, `file_unreadable`, `chain_*` statuses other than `parsed`, files near `MAX_BYTES` (the largest parsed was 2.4 MB;
  4BTS was refused by its stated length), the time and memory of a file near the cap.
* `CONTACT_A` 4.0: source UNVERIFIED. BioLiP's rule for binding residues was not found in the pages read.
* The meaning of the `-N` suffix as a symmetry copy: the chain exists as a separate `A-2` molecule with the entity of `A` (RecA 2ZTS C-2 graded, entity check passed); the Foldseek build scripts were not read.
* Entity ids from RCSB (hit metadata) are compared with the file's `label_entity_id` of the hit asym: no mismatch seen; if the entity numbering of an assembly file differed from the entry's the hit gets
  `chain_entity_differs_from_rcsb` (not asked of the partners), never a guess.
* The literature list of CspA's binding-face residues is from memory.
* The test's ligand `additive` flag rests on BioLiP's "suspicious" list, which marks NA, K, CL and MSE: a site cation of that list is recorded as additive.
