# All-vs-all BLAST: design record (phase 1, 2026-11-20)

Status: DESIGN. Pure library modules are written and untested by a real run; nothing here has been executed
against BLAST. Owner decisions that bear on it are D1-D9 and D13-D14 of `docs/plan/A101_blast_regions_plan.html`;
the reasoning about all-vs-all itself is the plan's inference I7, restated and extended below. Marks: **[owner]**
said by the owner, **[inference]** proposed here, **[verify]** something to check in the first real run.

## 1. What all-vs-all is, and what it is not

- **[owner]** All-vs-all (a set of sequences searched against itself) identifies relationships or clusters among
  sequences. It does not exist in the tree yet. Database setup and cluster jobs make most sense for custom databases
  and large-scale clustering of reads or sequences.
- **[inference]** Its raw result is a graph of who resembles whom. It is a data product until read relative to a
  target or a subset. Uses, most relevant first:
  1. whether the top hits of a database search form one family or several (a coherence check on identification);
  2. the family context of a target inside a custom set (cluster, size, annotated members, agreement);
  3. clustering reads or sequences at scale (a data reduction step whose result later work consumes).
- E-value is meaningful here because the search space is the set. **[owner D8]** E-value is meaningful in context;
  the context is recorded with it (sequence count and total letters of the whole set).
- Different from pairwise (one against one: which residues align) and from database search (one against a
  reference: identification). The kind is derived from the job's operand structure, not from names.

## 2. The kind: declared and derived **[owner D9]**

- **Declared:** the commission states `analysis_kind: all_vs_all` (fixed vocabulary; the vocabulary today is
  `pairwise` only, so this adds one value).
- **Derived from the job:** a valid all-vs-all job has a subject operand that is the declared whole set, a query
  operand that is that set or a declared contiguous slice of it, a set of at least two records, and a chunk
  declaration consistent with both. One chunk means query digest equals subject digest; several chunks mean the
  query is a slice. Any other shape raises, so a commission that declares the kind over a different job fails.
- **Mismatch** fails with `native_blast_all_vs_all_declared_kind_conflicts_with_the_job:<declared>`. No fallback,
  no repair.
- Implemented in `forms/sequence_homology_evidence/blast_all_vs_all_job.py` (`derive_analysis_kind`,
  `check_declared_kind`).

## 3. Commission fields (controlled values and record references only)

| Field | Value | Notes |
|---|---|---|
| `analysis_kind` | `all_vs_all` | declared; checked against the job |
| `set_ref` | record reference | a FASTA artifact in custody: the set, with its digest |
| `program` | `blastp` or `blastn` | fixed set |
| `evalue` | number, 0 < x <= 1000 | search E-value threshold |
| `max_target_seqs` | integer 1..100000 | |
| `max_hsps` | integer 1..10, optional | |
| `chunk_count` | integer 1..record count | 1 for a small local run |
| `resource_id` | one of the bound resources | the kind decides which are allowed (section 6) |
| `thresholds` | `min_identity`, `min_coverage` (0..1), `max_evalue`, `coverage_rule` (`both` or `shorter`), `edge_rule` (`reciprocal` or `either`) | recorded with the result |
| `strict_thresholds` | identity and coverage (0..1) | near-duplicate groups |
| `target_id` | member identifier, optional | the target of the family-context sheet |
| `annotation_refs` | record references, optional | records holding `member -> annotation id`, controlled annotation identifiers from a looked-up list |

No paragraph, no command, no option token is written by a caller. The compiler writes every option token.

## 4. The job contract (`native_blast_all_vs_all_job_v1`)

- Two operands, both FASTA: `subject_set` (always the whole set) and `query_set` (the whole set or one chunk). Each
  carries path, digest, size, record count and optional artifact reference. The job also declares the whole set
  (digest, record count, total letters) and the chunk (index, count, first and last ordinal).
- Compiles to: `blastp|blastn -evalue E -max_target_seqs N [-max_hsps H] -query <chunk> -subject <whole set>
  -outfmt "6 qaccver saccver pident nident length mismatch gapopen qstart qend sstart send qlen slen evalue
  bitscore" -out graph.tsv`.
- **[owner D10]** It declares one tabular report and nothing else: no stdout or stderr is declared, honoured,
  written or checked. The report has both sequence lengths because coverage of both sequences needs them.
- The shared native BLAST contract is not changed; the new contract reads its digest, schema and option helpers.

## 5. The grader, the clustering step and the features (pure functions)

**Sets (`blast_all_vs_all_sets.py`).** Parse a set (unique identifiers, no empty record, at least two records),
its digest and total letters, deterministic chunk ranges, and chunk text as an exact slice of the set, with a check
that a declared chunk is what it claims to be.

**Graph (`blast_all_vs_all_graph.py`)** fills the sheet's slots:
- Directed edges, one per ordered pair of sequences: identity and bit score of the best HSP; coverage of each
  sequence as the union of its HSP intervals; lowest E-value; HSP count; both lengths. Alternative HSPs are never
  summed (same rule as the pairwise grader).
- **Completeness rule:** a searched query always finds itself, so a query with no self-hit was not searched. A run
  with any missing self-hit, or any missing chunk, is `incomplete`, never "no relatives". A self-hit below 0.99
  identity or coverage is listed as partial.
- Merge of chunk graphs: same chunk count, distinct indices, disjoint queries, no repeated pair.

**Clusters (`blast_all_vs_all_clusters.py`)**, deterministic with recorded thresholds:
- Directed edges become undirected under `reciprocal` (both directions present and passing) or `either`; coverage
  `both` requires both sequences covered, which keeps a multi-domain sequence from chaining unrelated families.
- Clusters are connected components over every record of the set, so unrelated sequences are singleton clusters.
  Each cluster reports `density` (present edges over possible edges): a chained cluster shows as sparse.
- **Independent members:** near-duplicates are one vote. Greedy groups from the longest sequence down under strict
  thresholds; counts are over groups, not sequences.

**Features (`blast_all_vs_all_features.py`)**, numbers, booleans and supplied annotation identifiers only; absent
when not computable, never defaulted:
- Target context: `target_in_set`, `graph_status`, `searched_fraction`, `cluster_count`, `largest_cluster_size`,
  `cluster_size`, `singleton`, `independent_member_count`, `neighbor_count`, `cluster_density`,
  `neighbor_identity_min/median/max`, `neighbor_coverage_min`, `annotated_member_count`,
  `independent_annotated_count`, `top_annotation`, `annotation_agreement`, `distinct_annotation_count`.
  Agreement is over redundancy groups, so ten near-identical annotated members count once.
- Hit-list coherence (use 1): `hit_count`, `cluster_count_among_hits`, `largest_cluster_hit_count`,
  `largest_cluster_fraction`, `independent_hit_count`, and for a reference member (for example the database search's
  query) whether it is in the set and in the largest cluster.
- None of this assigns support or credit. The sheet's own scorer decides what the features mean.

## 6. Run mechanics: resources, chunking, allocation (real-run constraints)

- **Window bounds:** 1 CPU, 5 GiB RAM, no swap, one workload at a time. The job's memory and scratch limits come
  from the resource policy and the assignment constraints; the job takes no thread option (the `-subject` form is
  single-threaded, **[verify]**).
- **Scale:** the search is quadratic in set size. A small set (tens to low hundreds of sequences) runs locally as
  one job. A large set is split into query chunks and goes to the cluster resource.
- **Chunking:** each chunk is its own FASTA artifact in custody (an exact slice of the set), staged to the job as
  an input; the whole set is staged too. Chunks are separate launches in one or more units, each with its own
  handoff row (`JobAccess.launch` already takes a distinct `name` per launch). Chunking queries does not change an
  E-value: the search space is the subject set, which is always whole. Splitting the SUBJECT would change E-values
  and would need the whole set's size passed explicitly; v1 does not split the subject.
- **Idempotency:** a launch is idempotent on its operation key, and an abandoned handoff row is taken over, not
  resubmitted. The monitor observes each chunk's handoff. Durations are expected via the estimates recorded at
  launch (a quadratic-size proxy, refined from observed runs) and observed by the monitor; nothing has a deadline.
- **Completeness is a recorded fact,** by chunk and by query. A missing chunk makes the graph `incomplete`; credit
  and features say so.
- **HPC:** the PBS route's job is `{mode, script, arguments, env}`; `arguments` carry the scheduler's own options,
  so a chunk can be one batch job, or an array whose script selects its chunk from the array index. A scheduler
  requires a walltime request; this is a scheduler allocation, not an application budget, but how it is chosen is
  an owner decision (section 10). The HPC leg is designed so the whole contract and the merge can be validated
  offline; a real Aurora run needs the owner to authenticate first. Nothing here authenticates, replaces a master
  connection, or runs a remote command.
- **Large outputs:** the graph is retained as an artifact beside the original report. Only controlled features and
  references travel upward.
- **v2 path for large sets [inference]:** a prepared database of the set (the database-preparation kind) searched
  with `-db`, with chunked queries. The shared contract forbids `-db`, so this needs its own contract and depends
  on the preparation kind.

## 7. Credit and return **[owner D14]**

- Credit is the gain in certainty. The graph earns credit once, in proportion to the newly covered fraction of the
  set's queries, as the plain-file results already credit newly covered bytes: a complete graph earns the unit, an
  incomplete one earns its covered fraction, a repeat earns nothing. The clustered family-context sheet earns its
  own unit once, when saved from a complete graph.
- Credit falls only when an established fact is lost. A target found to be a singleton earns the same as one found
  in a family: it is information.
- **Return (controlled fields):** credit and finding always; `execution_all_vs_all_graded_refs` (the saved graph
  record, its source and the clustering record) selectable; the target features of section 5 as the finding.

## 8. What fails, and how

| Case | Result |
|---|---|
| declared kind absent or different from the derived kind | commission fails with its error |
| set with a duplicate identifier, an empty record, or fewer than two records | commission fails |
| chunk slice is not an exact slice of the set | grading refuses (`...chunk_does_not_match_the_set`) |
| report row malformed, HSP outside its sequence, conflicting lengths for a pair | grading refuses with a stable code |
| query with no self-hit, missing chunk | graph `incomplete`; features report `graph_status`; never "no relatives" |
| target not in the set | `target_in_set: false`, nothing else |
| unknown threshold rule or out-of-range threshold | commission fails |

## 9. Existing files that need a change (exact patch list; none applied)

The pairwise work of the previous fork was removed from the working tree while this record was written (its
library files are absent), so patches that must sit beside it are given as the change to make, not as a diff.

1. **Kind vocabulary (the pairwise module's `blast_analysis_kind`):** add `all_vs_all` beside `pairwise`; deriving
   the kind from a requested job tries the pairwise contract, then `blast_all_vs_all_job.derive_analysis_kind`,
   and fails if neither accepts it.
2. **`execution_result_acquisition/messages/read_from_parent.py`:** in `family()`, before the generic native
   branch: `if 'native_blast_all_vs_all' in jobs: return 'blast_all_vs_all'`; the `analysis_kind` choice field gains
   `all_vs_all`; `validated_selector` gains a branch for the family's selector (thresholds, strict thresholds,
   `target_id`, annotation references); `read_from_parent` calls `check_declared_kind(declared, requested_job)`.
3. **`execution_result_acquisition/task.py`:** `_catalog` gains `_all_vs_all_catalog` with three tools: fetch of the
   one declared report (the same fetch the pairwise family uses, over `graph.tsv`), `all_vs_all_grade` (parse report,
   build edges, completeness, merge chunks, retain the graph artifact and source through custody), and
   `all_vs_all_cluster` (thresholds, components, redundancy groups, features, retain the family-context sheet).
4. **`credit.py`, `yield_estimator.py`, `messages/final_to_parent.py`, `messages/internal_summary.py`:** the unit
   credits of section 7, the stopping profile key for the family, the return fields of section 7, the held graph
   and sheet read from custody.
5. **The launch leaf's job validation** knows only a generic command or the shared native jobs. Either the parent
   keeps the full all-vs-all job for the results commission (the same split as pairwise, plan question Q1) or the
   validation learns this contract.
6. **Head commission builders:** none exist for this kind. They need the set record, the chunk artifacts and the
   thresholds as controlled fields (section 3).

## 10. Open owner decisions

1. **Clustering method:** connected components with recorded thresholds is v1. A graph method such as Markov
   clustering would be an external job at scale. Is it in scope, and when?
2. **HPC walltime and queue:** how are they chosen for chunk jobs, given there is no application deadline?
3. **Annotation source:** which episode supplies `member -> annotation id` for a custom set, and from which looked-up
   list?
4. **`-subject` for v1 versus prepared database:** is the `-subject` form acceptable for the first real runs, with
   the prepared-database path as v2?
5. **Large reads:** is BLAST-based all-vs-all acceptable for clustering large read sets, or will another tool be
   brought in later (outside this scope)?
6. **Defaults:** are `reciprocal` edges and `both` coverage the right defaults for family clustering?
7. **Where does the family-context subscore live,** and is it A101's, given that region and joint-credit work
   moved to the root? (Formulas stay deferred: data first.)

## 11. First thing to build, and the real-run recipe (phase 2)

**Build first: a small local set.** Reasons: no scheduler, no authentication, runs in seconds inside the window's
bounds, and it exercises every stage (set, job, launch, monitor, fetch, graph, clusters, features, credit,
resume) on real sequences. The chunked and HPC legs follow on the same code.

**Set (real sequences):** the 45 globins of the HMMER tutorial FASTA, the first 10 fn3 domains and the first
10 kinase domains from the tutorial Stockholm files (gaps removed). That is a family with sub-families, a second
and third family, and ready-made singletons at strict thresholds. Annotations supplied by the test world's own
mapping for the globins only (stated in the world file, not derived from names by code).

**Predictions (to be written into the run before it starts):**
- 65 records; 65 self-hits; `graph_status: complete`.
- The globins form one large cluster at lenient thresholds (identity 0.25, coverage 0.6, `reciprocal`, E-value
  1e-3); at strict thresholds (0.9) they split into near-duplicate groups, so independent members are far fewer than
  45. The fn3 and kinase sequences form their own, separate clusters; no sequence of either joins the globins.
- A target globin: not a singleton, `annotation_agreement` high; a target fn3 domain: in its own cluster.
- Units: status check, fetch, grade graph, cluster; credit from the graph earned once, the sheet once; repeating a
  unit earns 0; resume asks the model nothing.
- Second run, `chunk_count` 3 with one chunk's report withheld: `graph_status: incomplete`, `missing_chunks: [i]`,
  credit proportional to the covered fraction, no feature reads as "no relatives".

**Verify in the first real run:** that `-subject` accepts a multi-record set with these options and the
tabular fields; how the search space is computed against a multi-record subject (read once from a JSON report of
the same small set, and compare with the declared set size and total letters); that every query finds itself
(masking can remove a self-hit); and that the self-hit rule does not misreport a low-complexity sequence.

## 12. Incident note

While this record was being written, files created in this working tree by parallel work disappeared, including the
committed `docs/plan` directory (shown as deleted after the checkpoint commit). Copies of the five new modules are
in the session scratchpad under `f3_backup/`, and a copy of this record is there too; restore from there if a
module is missing.
