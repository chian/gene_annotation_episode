# all_vs_all: a child episode of the A101 head (all-vs-all BLAST of a chosen set, clustered with MCL)

Written 2026-11-21. HEAD = `gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence`; LIB =
`gene_annotation_episode/episodic_workflow/episode_support`. Pattern: `bvbrc_msa_episode.md` (a test over chosen product candidates,
graded into a measurement per candidate, kept as labelled data products, returned with closed record lists). Earlier design of the
never-run all-vs-all library: `all_vs_all.md`.

## The owner's words (verbatim; they govern)

- "with MSA it really does make sense to also add All-vs-all blast and some kind of clustering ... Clustering only makes sense with an All-vs-all scoring metric and so really I need two tools here"
- "locally then all vs all would need the database preparation, right?"
- "i would say it almost is a tool of the all vs all blast yes?"
- "clustering can also be a tool so that all vs all can just be one child episode"
- "you'll need to find a good clustering tool that can work on similarity scores like the bitwise scores"
- The graders add to the subscoring sheets and the sheets add to the score: "the graders should additively add to the subscoring sheets and then the subscoring sheets additively add to the score".
- Ceilings: "ceiling is a function that has to be how much max credit from this current state"; "UNBOUNDED filled in everywhere is bad; UNBOUNDED where truly unbounded is right".
- Tools are one-shot: "have the head node fill out a json and then that json is deterministically run through a function that checks it and either (returns things to fix) or runs the job".

## What the child is

One child episode, `HEAD/all_vs_all` (the standard files; no children of its own, so no `msg_to_child` or `read_from_child`). The head's model
commissions it with controlled fields only: `query_ref` (the target), `search_ref` (a held graded BV-BRC search), `candidates` (two or
more product candidates admitted from it) and `per_candidate` (2 to 20). The child's own model names the bound local resource each tool runs on
and tunes the clustering. Five one-shot tools, each one unit, each through `execute_on_local_resource` (the local inspection point) with its job
folder in the run's local resource workspace, each keeping a labelled data product (`records/data_products.py`) that the next requires
(`require_product`):

| tool (model's JSON) | its one check | what runs | product (EDAM data / format) |
|---|---|---|---|
| `prepare_database` (`resource_id`) | local resource bound; set of at least 2 sequences; no database of this commission held (reuse key); no earlier failure; `makeblastdb`, `blastdbcmd`, python exist | the set's hit sequences fetched once by md5 (`sequences_by_md5`), the set kept as `protein_sequences`; `makeblastdb` (existing `prepare_locally`); the database files packed into ONE tar | `blast_protein_database`: data_1233 Sequence set (protein) / format_3981 TAR |
| `all_vs_all_blast` (`resource_id`, `database_ref`) | the database is a held `blast_protein_database` product (`require_product`); no matrix of it held; no earlier failure; `blastp` exists | a new job folder: the driver unpacks the tar there and runs `blastp -db` of every sequence of the set; report parsed and checked for self-hits | `sequence_similarity_matrix`: data_2082 Matrix / format_3475 TSV |
| `cluster` (`resource_id`, `matrix_ref`, `inflation`, `contrast`) | the matrix is a held `sequence_similarity_matrix` product; inflation one of 1.4, 2.0, 4.0 and contrast one of none, rescale, percentile_25, _50, _75, _90 (`cluster_sheet.INFLATIONS`, `CONTRASTS`); the same tuning of the same matrix not tried before; no earlier failure; `mcl` exists | `mcl --abc -I <inflation>` on the score-ratio graph as the contrast leaves it. A TRY: the clusters are kept as a working result, the child's model is shown controlled facts of them, and nothing is graded | `sequence_clusters`: data_1245 Sequence cluster (protein) / format_2171 Sequence cluster format (protein) |
| `commit_clustering` (`clusters_ref`) | a held clustering; none committed yet | the committed clustering is graded into the cluster sheet: the one graded source the head reads | (the graded source) |
| `hold` (a reason) | always valid | nothing | none |

EDAM was read from https://edamontology.org/EDAM.tsv on 2026-11-21 (all six terms exist, none obsolete). EDAM has no term for a BLAST
database, so the closest, the protein sequence set it holds, is used with the TAR format of the archive; it has no sequence-similarity pair-score
matrix (data_0870 is an evolutionary distance matrix), so the generic data_2082 Matrix ("a placeholder for other, more specific types") is used.

## The set

The target (id `target`) and, for each chosen candidate, its hits by the head's own selection rule, the MSA child's `plan_rows` (highest value in the
graded search, ties by accession, one per distinct `aa_sequence_md5`, the first `per_candidate`), with PLAIN ids `r1`, `r2` ... (BV-BRC accessions
contain `|` and BLAST's `-parse_seqids` reads such ids as database identifiers; plain ids keep the report names what the code gave). The map
id -> candidate, accession, md5 is recomputed from the held search (`all_vs_all_run.set_members`), deterministic, and is also stored in the cluster sheet.
The sequences are fetched once, by md5, through `sequences_by_md5` (BV-BRC public data service, no login, batches of 100 ten seconds apart; each
sequence's md5 is verified), and kept with the target as the `protein_sequences` product.

## The matrix: which score and why

BIT SCORES of the best alignment of each ordered pair, from `blastp -db` of every sequence against the database of the set, E-value 10 (BLAST's
default, so weak relatives are kept), `max_target_seqs` the size of the set (no pair truncated). A bit score is the raw score put on a common scale
by the scoring system's statistics: it does not depend on the size of the set (an E-value does) or on the scoring system (a raw score does). The
matrix holds every ordered pair, the self pairs included (a sequence that did not find itself fails the run: never "no relatives").

## The clustering: MCL, and why

MCL (Markov Cluster, van Dongen; the established method for BLAST similarity graphs: TribeMCL, OrthoMCL), run as the program `mcl` (22-282,
built from the official source under `resources/software/mcl-22-282`, recorded in `resources/software/mcl.json`), on a graph whose edge weights
are the BLAST SCORE RATIO `bits(a, b) / min(bits(a, a), bits(b, b))` in [0, 1] (the larger of the two directions of the pair; capped at 1), so
sequence length does not dominate a bit score. The child's model tunes two parameters from fixed sets: the inflation (lower is coarser; 1.4, 2.0 or 4.0) and the graph contrast (none, rescale of the ratios to the set's own range, or only the edges at or above the 25th, 50th, 75th or 90th percentile of the set's ratios). MCL works on
the weights themselves, and a chain of weak links through a multi-domain sequence does not merge two families (it does
under single linkage or connected components). A sequence with no edge is a cluster of its own (mcl reads edges, so it is absent from its output).

## The cluster test the head reads

TEST = `cluster:mcl@<source>` (one test per graded clustering, as every test is named), subscoring sheet `cluster:mcl`, vocabulary `product`. One
measurement per candidate group (the set's sequences of one candidate; the target is in no group): value = the SHARE of the group's sequences that are
in the target's cluster, in [0, 1]. A candidate with no sequence in the set gives none. It is on the scale of the other tests: a database search's value
is the subscore of a hit's alignments (0 to 1; 0.8 to 0.96 for a typical strong result) and the cluster share is about 1 for a strong typical
result (all of a candidate's sequences cluster with the target) and 0 when none does (a candidate with value 0 is not admitted); the MSA count is
weighted by W = 1/E to be on the same scale. The measurement also keeps `size` and `in_target_cluster`, and its `dataset`: the graded BV-BRC
search the set's sequences are drawn from (the commission's `search_ref`).

ONE CREDIT FOR ONE DATASET. The owner (2026-11-21, verbatim): "You only can earn one credit for one dataset - you can improve a clustering to earn
more, but you cannot replicate". All the committed clusterings of one dataset together earn at most one test's credit
(`differential_credit`): each clustering is computed as a test at its own place in the order (its entries and differentials as for any test),
and the dataset earns the MAXIMUM of those test credits; a later clustering of the dataset earns only the amount by which it beats the best so far
(an improvement), a replicate earns 0, and the credit never falls. A candidate's value on the cluster sheet from one dataset reads the same
maximum: its largest share over that dataset's clusterings, not their sum.

One clustering is graded per commission: the tries of `cluster` are not graded, and `commit_clustering` grades one of them, once; the head refuses an identical commission.

## Credit and ceilings

Child credit (`all_vs_all/credit.py`): the head's three child units, each earned once and read from the products held: `handoff_unit` for the database,
`information_unit` for the matrix, `graded_unit` for the committed (graded) clustering; a refused or repeated step earns 0, and a try earns nothing. Child
ceiling: each tool's unit while its check can pass, else 0 (`cluster` and `hold` 0). Yield: the completion controller to the commission's target.

Head ceiling for `all_vs_all` (`HEAD/credit.ceiling`): the proved, tight maximum the cluster test can add from the current state
(`differential_credit.cluster_test_ceiling`, proof in its docstring). The test measures each named candidate once, its value w x its share in the
target's cluster, in [0, w] (w the cluster sheet's weight); appended last, its own credit (the entries it admits plus |v_a - v_b| over the listed pairs)
is convex on that box, so it is largest at a vertex: with l listed and u unlisted candidates named, w (u + floor(l^2 / 4)) (half the listed candidates
wholly in the target's cluster, the other half wholly outside; two candidates on the same side earn 0). Every named candidate has at least one sequence in
the set, so that partition is an outcome the clustering can give: the bound is reached. The dataset already earned its best test credit, so the ceiling is
that vertex bound minus the dataset's best so far, floored at 0 (`dataset_test_ceiling`; `candidate_measurements.dataset_bests`); a commission identical to
one already commissioned or graded (same search, candidates, per_candidate) 0. With no arguments the ceiling is that of the best commission the head's check
accepts now (`HEAD/credit.all_vs_all_best`: larger candidate sets first, the first found on a tie, the largest per_candidate not yet commissioned with that
set), and `best_arguments` names it, so the row the model sees and a refusal's `choose_from` name a commission that reaches the row's ceiling.

Direct check (labelled: NOT a real run) on a scratchpad copy of `runs/a101_goal5_ws_cspa` (state, journal `journal_cspa.sqlite3`, artifacts; run dir
`runs/a101_goal5_run_cspa_c60596441`), the head's summary and custody rebuilt as they stood before each unit (journal receipts of earlier units); the
recomputed old ceilings equal the journal's. Head units 2, 5, 7, 8 were `all_vs_all` of one search (all named candidates listed):

| unit | named | dataset best before | ceiling of the unit's commission, old (journal) -> new | rise | row ceiling (no arguments), old (journal) -> new |
|---|---|---|---|---|---|
| 2 | 4 | 0 | 6.0 -> 4.0 | 3.125 | 10.0 -> 6.0 |
| 5 | 4 | 3.125 | 2.875 -> 0.875 | 0 | 6.875 -> 2.875 |
| 7 | 5 | 3.125 | 6.875 -> 2.875 | 1.5417 | 6.875 -> 2.875 |
| 8 | 5 | 4.6667 | 5.3333 -> 1.3333 | 0 | 5.3333 -> 1.3333 |

Every rise is at or below the new ceiling. The best commission at each point was the search with all five admitted products at per_candidate 20; the
head's check accepts it (no problems), and its ceiling equals the row's.

## What was reused and what was not

Reused: `blast_all_vs_all_graph.parse_report`, `build_edges` and `completeness` (the best alignment of each ordered pair, the self-hit completeness rule),
`blast_preparation_job.compile_preparation` / `blast_preparation_run.prepare_locally` (the database build and its receipt; it now also returns the
files the job left), `bvbrc_msa_alignment.search_rows` / `plan_rows` (the selection rule), `bvbrc_hit_metadata.sequences_by_md5`,
`execute_on_local_resource`, `data_products` (`record_product`, `require_product`, `find_reusable`), `tool_grading_artifacts.retain_tool_grading`,
`job_records.returned_with_names`, the `candidate_measurements` / `differential_credit` arithmetic. Not reused, and why: `blast_all_vs_all_job` (compiles
`blastp -subject` of the set, no database; the owner's decision is a prepared database searched with `-db`), `blast_all_vs_all_chunk_job` (chunked
query slices for a cluster resource: the set here is tens of sequences, one local job), `blast_all_vs_all_sets` (FASTA parsing and chunking:
`describe_fasta` of the preparation already validates the set), `blast_all_vs_all_clusters` (connected components under identity and coverage thresholds:
the owner asked for a method that works on bit scores), `blast_all_vs_all_features` and `blast_all_vs_all_sheet` (family-context features that
need annotation identifiers of a custom set; the head reads the cluster sheet instead).

## Defects found

- The bundled BLAST+ 2.17.0 `blastdbcheck` reports "MetaData: caught exception" for every valid database (versions 4 and 5, with and without
  `-parse_seqids`, `-full` or not), so the preparation's integrity step could never succeed. The `check` step and the `integrity_*` facts were
  removed from the preparation (a database is established by `makeblastdb` returning 0, `blastdbcmd -info` counting the input's sequences and letters,
  and every file of the database present).
- A data product is content-addressed (its key is its artifact): two clusterings that give identical cluster files are one product row. With one
  clustering per commission this does not arise.

## Direct checks (labelled: NOT real runs)

On a copy of `runs/a101_conserved_ws_C2` (`runs/ava_direct_ws`), the md5 fetch against BV-BRC's public data service (no login) and BLAST+/MCL locally,
through the library functions with the head's stored custody (harness in the session scratchpad):

- The set: the target and the hits of the CspA, CspB/CspG/CspI and CspC products at `per_candidate` 10: 30 sequences (10, 10 and 9: the CspC product has
  nine distinct sequences among its hits), 2100 letters.
- The database: 10 files in one tar. The matrix: 900 rows (30 self, 870 ordered pairs, every pair has a hit); score-ratio graph of 435 edges, weights 0.739
  to 1.0.
- MCL at inflation 1.4, 2.0 and 4.0: ONE cluster of all 30 sequences each time. scipy average-linkage of 1 - score ratio, cut at 0.5 and at 0.7: also one
  cluster. Both agree: this set (one cold-shock-domain family of 70-residue proteins) is not separated by the clustering, so each candidate's share is 1.0
  (CspA 10/10, CspB/CspG/CspI 10/10, CspC 9/9). The test is uninformative on this set; it would be informative for candidate groups that are different families.

## 2026-11-21 (later): tuning by the child's model, the committed clustering, the sheet weights, the head wiring

The owner: "i'm not going to tune something that needs to be tuned for every single protein differently. that rescaling should be something the agent does" and "just let MCL be tuned by agent and figure out if we need to adjust scoring at all. if not, no worries"; then "wire in the all-vs-all into the subscoring and scoring and credit and then make the whole thing work"; and the scoring sheet weighs the subscoring sheets into the score with stated weights, derived from the stored runs.

This supersedes the earlier text above where they differ (the head's `inflations` field, one clustering per commission by refusing the second try):

- MCL stays the one algorithm. The tuning is a controlled choice of the child's MODEL per commission: the inflation (1.4, 2.0, 4.0) and the graph contrast (`none`; `rescale`: `(ratio - lowest) / (1 - lowest)`; `percentile_25/50/75/90`: keep only edges at or above that percentile of the set's ratios). The head's commission has no tuning field.
- `cluster` is a TRY (a working result): it returns controlled facts (cluster count, sizes, the target's cluster size, per candidate its size, its sequences in the target's cluster, the clusters it spans). Nothing is graded. A tuning of a matrix is tried once; a partition already held is reported as the same clustering. `commit_clustering` (once) grades one held try into the cluster sheet: the one graded source the head reads, so tries neither add to nor dilute the head's credit. Child credit: the database, the matrix and the committed clustering earn the three units; a try earns 0 (ceiling 0); `commit_clustering` has the graded unit as its ceiling while a try is held and none committed.
- On the C2 set (30 sequences; score ratios 0.739 to 1.0): no contrast gives one cluster at every inflation; `rescale` at 4.0 and every inflation at `percentile_50` give two clusters (21 with the target, 9 = the CspC product); `percentile_75` also splits CspB/CspG/CspI off (inflation 1.4: 6 of its 10 stay with the target; 2.0: none). The committed `rescale`, 4.0 clustering gives CspA 10/10, CspB/CspG/CspI 10/10, CspC 0/9, so the shares are 1.0, 1.0 and 0.0, the shape the MSA test gave (1.0, 0.29, 0.0). The cluster test's value rule did not need to change; neither did the child's credit or the ceilings, apart from the weights below.
- THE SHEET WEIGHTS (`differential_credit.SHEET_WEIGHT`, derivation beside the constants): the weight of each sheet's family is one over its typical strong value, the value in one test of the candidate that leads the stored real runs (C2, H1, the CspA run; all E. coli CspA): database_search 1/0.9593, profile_scan 1/0.8198, msa 7/12 (the leader's first alignment, 12 matched sites x 1/7), cluster 1, pairwise 1 (no stored value). The score is the sum over sheets of weight x sheet value; entries, differentials and the ceilings (`test_ceiling(..., family)`, the msa ceiling's maxima) are in the weighted units. Credit definition `a101_differential_credit_v3` (carries `sheet_weights`). Before and after on the stored records: C2 with the committed clustering 10.5289 to 9.4622 (CspA 3.6736 to 3.0000, CSD 0.8198 to 1.0000); the CspA run (`runs/a101_final_run_cspa`) 8.5289 to 7.4622 (CspA 2.6736 to 2.0000: database 1.0, msa 1.0). The data is one target: re-derive as other targets are run.
- Head wiring: slot `all_vs_all`; commission fields `query_ref`, `search_ref`, `candidates` (two or more admitted product candidates), `per_candidate`; its one check `all_vs_all_run.check_commission` (a set already commissioned or graded is refused); offered only while a held graded BV-BRC search admits at least two product candidates; the head's ceiling for it is the vertex bound of the cluster test (`cluster_test_ceiling`) minus the dataset's best test credit so far, floored at 0, with `best_arguments` naming the commission that reaches the no-arguments ceiling (see "Credit and ceilings"). The head's `database_blast` and `blast_database_preparation` children and the old `all_vs_all_blast` skeleton are removed; `database_blast_search.py` stays because the BV-BRC children import its shared functions (`bvbrc_blast_search`, `bvbrc_job_child`, `bvbrc_metacats_search`, `bvbrc_msa_alignment`, and the head's `task.py`: `seconds_between`).
